"""
Calculador de tarifas RDA Ramoneda.
Paquetería por kg desde Alicante. 10 zonas.
Precios fijos por expedición hasta 200 kg, luego €/kg por tramos.
"""
import json
import os


def _load_data():
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'ramoneda.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _normalizar(texto):
    """Normaliza texto para comparación: mayúsculas, sin tildes."""
    import unicodedata
    texto = texto.upper().strip()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto)
                    if unicodedata.category(c) != 'Mn')
    return texto


def buscar_zona(destino, data):
    """Devuelve el número de zona (1-10) para el destino dado, o None."""
    destino_norm = _normalizar(destino)
    for zona, provincias in data['zonas'].items():
        for prov in provincias:
            if _normalizar(prov) == destino_norm:
                return int(zona)
    return None


def calcular_peso_tasable(peso_real_kg, volumen_m3, destino, data):
    """Calcula el peso tasable comparando real vs volumétrico."""
    if volumen_m3 is None or volumen_m3 <= 0:
        return peso_real_kg, "Peso real (no se indicó volumen)"

    destino_norm = _normalizar(destino)
    if any(_normalizar(p) == destino_norm for p in data['zonas'].get('8', []) + data['zonas'].get('9', [])):
        factor = data['factor_volumen']['baleares']
    elif any(_normalizar(p) == destino_norm for p in data['zonas'].get('10', [])):
        factor = data['factor_volumen']['portugal']
    else:
        factor = data['factor_volumen']['peninsular']

    peso_vol = volumen_m3 * factor
    if peso_vol > peso_real_kg:
        return peso_vol, f"Peso volumétrico ({volumen_m3:.3f} m³ × {factor} kg/m³ = {peso_vol:.1f} kg)"
    return peso_real_kg, f"Peso real ({peso_real_kg:.1f} kg > {peso_vol:.1f} kg volumétrico)"


def _precio_expedicion(peso_kg, zona_idx, data):
    """
    Devuelve (precio, descripcion) para el tramo de precio fijo por expedición (≤200 kg).
    zona_idx es 0-based (zona 1 → índice 0).
    Regla: redondear AL TRAMO SUPERIOR inmediato.
    """
    breakpoints = sorted([int(k) for k in data['precios_expedicion'].keys()])

    for bp in breakpoints:
        if peso_kg <= bp:
            precio = data['precios_expedicion'][str(bp)][zona_idx]
            return precio, f"Tarifa fija tramo {bp} kg"

    # Si supera el último breakpoint (200 kg), caerá en precios_kg
    return None, None


def _precio_kg(peso_kg, zona_idx, data):
    """
    Devuelve (precio, descripcion) para el tramo €/kg (>200 kg).
    zona_idx es 0-based.
    Regla: usar tarifa del tramo correspondiente, mínimo = precio tramo inferior.
    """
    bp_kg = sorted([int(k) for k in data['precios_kg'].keys()])  # [350, 500, 1000, 2000, 3000, 5000]

    # Precio del tramo 200 kg como mínimo inicial
    precio_min_anterior = data['precios_expedicion']['200'][zona_idx]

    # Calcular precio al inicio de cada tramo para la regla de mínimo
    precio_200 = precio_min_anterior

    for i, bp in enumerate(bp_kg):
        if peso_kg <= bp:
            tasa = data['precios_kg'][str(bp)][zona_idx]
            precio_calculado = round(peso_kg * tasa, 2)

            # Calcular el mínimo del tramo anterior
            if i == 0:
                minimo = precio_200
                desc_min = f"mínimo {precio_200:.2f}€ (tarifa 200 kg)"
            else:
                bp_ant = bp_kg[i - 1]
                tasa_ant = data['precios_kg'][str(bp_ant)][zona_idx]
                minimo = round(bp_ant * tasa_ant, 2)
                desc_min = f"mínimo {minimo:.2f}€ (tarifa inicio tramo {bp_ant} kg)"

            # Asegurar que el anterior también sea >= precio_200
            minimo = max(minimo, precio_200)

            precio_final = max(precio_calculado, minimo)
            if precio_final > precio_calculado:
                return precio_final, f"{peso_kg:.1f} kg × {tasa:.4f} €/kg = {precio_calculado:.2f}€ → ajustado a {desc_min}"
            return precio_final, f"{peso_kg:.1f} kg × {tasa:.4f} €/kg (tramo hasta {bp} kg)"

    # Peso > 5000 kg: usar tasa del último tramo
    tasa = data['precios_kg']['5000'][zona_idx]
    precio = round(peso_kg * tasa, 2)
    return precio, f"{peso_kg:.1f} kg × {tasa:.4f} €/kg (tramo >3000 kg, CONFIRMAR CON RDA para pesos >5000 kg)"


def calcular(destino, peso_real_kg, volumen_m3=None, llegada=False):
    """
    Calcula el precio Ramoneda para un envío.

    Args:
        destino: Nombre de la provincia/zona destino
        peso_real_kg: Peso real en kg
        volumen_m3: Volumen en m³ (opcional, para calcular peso volumétrico)
        llegada: Si es True, aplica +20% por ser envío de llegada/retorno

    Returns:
        dict con resultado y desglose
    """
    data = _load_data()

    zona = buscar_zona(destino, data)
    if zona is None:
        return {
            'transportista': 'RDA Ramoneda',
            'aplicable': False,
            'motivo': f"Destino '{destino}' no encontrado en las zonas de RDA Ramoneda.",
            'precio': None
        }

    zona_idx = zona - 1

    peso_tasable, desc_peso = calcular_peso_tasable(peso_real_kg, volumen_m3, destino, data)

    # Calcular precio según tramo
    if peso_tasable <= 200:
        precio_base, desc_precio = _precio_expedicion(peso_tasable, zona_idx, data)
        if precio_base is None:
            precio_base, desc_precio = _precio_kg(peso_tasable, zona_idx, data)
    else:
        precio_base, desc_precio = _precio_kg(peso_tasable, zona_idx, data)

    suplementos = []
    precio_final = precio_base

    if llegada:
        incremento = round(precio_base * data['suplemento_llegadas_pct'] / 100, 2)
        precio_final += incremento
        suplementos.append(f"Suplemento llegada +{data['suplemento_llegadas_pct']}%: +{incremento:.2f}€")

    return {
        'transportista': 'RDA Ramoneda',
        'aplicable': True,
        'precio': round(precio_final, 2),
        'zona': f"Zona {zona}",
        'peso_tasable': round(peso_tasable, 2),
        'desglose': {
            'peso': desc_peso,
            'zona': f"Zona {zona} de 10",
            'precio_base': f"{precio_base:.2f}€ ({desc_precio})",
            'suplementos': suplementos,
            'total': f"{precio_final:.2f}€",
            'iva_no_incluido': True,
            'combustible': "Suplemento combustible variable según Ministerio (no incluido en cálculo base)"
        }
    }


# --- TESTS ---
if __name__ == '__main__':
    casos = [
        # (destino, kg, m3, llegada, precio_esperado_aprox)
        ('Alicante', 50, None, False, 9.33),      # Z1, 50kg
        ('Murcia', 100, None, False, 14.11),       # Z2, 100kg
        ('Madrid', 200, None, False, 27.18),       # Z3, 200kg
        ('Sevilla', 500, None, False, None),       # Z4, 500kg
        ('Mallorca', 50, None, False, None),       # Z8, Baleares
        ('Portugal', 100, None, False, 36.36),     # Z10
        ('Valencia', 30, None, False, 7.50),       # Z2, 30kg
        ('Zaragoza', 350, None, False, None),      # Z4, 350kg (primer tramo €/kg)
        ('Barcelona', 1000, None, False, None),    # Z3, 1000kg
        ('Bilbao', 200, None, False, None),        # No existe → ver zona
    ]

    print("=== TEST RDA Ramoneda ===")
    for destino, kg, m3, llegada, esperado in casos:
        r = calcular(destino, kg, m3, llegada)
        ok = ''
        if esperado and r['precio']:
            ok = '✓' if abs(r['precio'] - esperado) < 0.05 else f'⚠ esperado {esperado}'
        print(f"  {destino:12s} {kg:5.0f}kg → {r.get('precio','N/A'):>8} € | Zona: {r.get('zona','N/A')} {ok}")
        if r.get('desglose'):
            print(f"    {r['desglose']['peso']}")
            print(f"    {r['desglose']['precio_base']}")
