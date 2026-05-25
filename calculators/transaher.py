"""
Calculador de tarifas Transaher (Grupo Transaher).
Paquetería por kg desde Alicante. 8 zonas peninsulares + Portugal (A-E) + Baleares/Canarias.
Precios escalonados: hasta 1000 kg = precio fijo por tramo, >1000 kg = €/kg.
Factor conversión volumen: 200 kg/m³ peninsular (negociado con AGROSERC).
"""
import json
import os
import unicodedata


def _load_data():
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'transaher.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _norm(texto):
    texto = texto.upper().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto)
                   if unicodedata.category(c) != 'Mn')


def buscar_zona_peninsular(destino, data):
    """Devuelve (zona_num 1-8, zona_str) o (None, None)."""
    dn = _norm(destino)
    for zona_str, provincias in data['peninsular']['zonas'].items():
        for p in provincias:
            if _norm(p) == dn:
                return int(zona_str), zona_str
    return None, None


def buscar_zona_portugal(destino, data):
    """Devuelve (zona_letra A-E, nombre_zona) o (None, None)."""
    dn = _norm(destino)
    for zona_letra, info in data['portugal']['zonas'].items():
        for prov in info['provincias']:
            if _norm(prov) == dn:
                return zona_letra, info['descripcion']
    return None, None


def buscar_zona_baleares_canarias(destino, data):
    """Devuelve (zona_num 9-16, nombre_zona) o (None, None)."""
    dn = _norm(destino)
    zonas = data['baleares_canarias']['zonas']
    for zona_num_str, info in zonas.items():
        for isla in info['islas']:
            if _norm(isla) == dn:
                return int(zona_num_str), info['nombre']
    return None, None


def calcular_peso_tasable(peso_real_kg, volumen_m3, destino, data, tipo_destino='peninsular'):
    """Calcula peso tasable comparando real vs volumétrico según factor negociado."""
    if volumen_m3 is None or volumen_m3 <= 0:
        return peso_real_kg, "Peso real (no se indicó volumen)"

    factores = data['factor_volumen']
    if tipo_destino == 'peninsular':
        factor = factores['peninsular']  # 200 kg/m³ para AGROSERC
    elif tipo_destino == 'portugal':
        factor = factores['portugal_terrestre']
    elif tipo_destino in ['baleares', 'mallorca', 'menorca']:
        factor = factores['baleares_mallorca_menorca']
    elif tipo_destino in ['ibiza', 'formentera']:
        factor = factores['baleares_islas_menores']
    else:
        factor = factores.get(tipo_destino, factores['canarias'])

    peso_vol = volumen_m3 * factor
    if peso_vol > peso_real_kg:
        return peso_vol, f"Peso volumétrico ({volumen_m3:.3f} m³ × {factor} kg/m³ = {peso_vol:.1f} kg)"
    return peso_real_kg, f"Peso real ({peso_real_kg:.1f} kg > {peso_vol:.1f} kg volumétrico)"


def _precio_peninsular(peso_kg, zona_idx, data):
    """
    Calcula precio peninsular.
    zona_idx: 0-based (zona 1 → 0, zona 8 → 7).
    Tramos: mínimo, 100, 200, ..., 1000 (precio fijo); luego kg_rate.
    Regla: para peso en tramo X → precio del tramo X. Si < tramo anterior, usa tramo anterior.
    """
    p = data['peninsular']['precios']
    bp_fijo = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

    if peso_kg <= 0:
        return p['minimo'][zona_idx], "Mínimo facturable"

    # Buscar tramo
    for bp in bp_fijo:
        if peso_kg <= bp:
            precio = p[str(bp)][zona_idx]
            minimo = p['minimo'][zona_idx]
            precio_final = max(precio, minimo)
            desc = f"Tramo {bp} kg: {precio:.2f}€"
            if precio_final != precio:
                desc += f" (ajustado a mínimo {minimo:.2f}€)"
            return precio_final, desc

    # Peso > 1000 kg: €/kg
    tasa = p['kg_rate'][zona_idx]
    precio_calculado = round(peso_kg * tasa, 2)
    precio_1000 = p['1000'][zona_idx]  # mínimo
    precio_final = max(precio_calculado, precio_1000)
    desc = f"{peso_kg:.1f} kg × {tasa:.3f} €/kg = {precio_calculado:.2f}€"
    if precio_final > precio_calculado:
        desc += f" → ajustado a mínimo tramo 1000 kg ({precio_1000:.2f}€)"
    return precio_final, desc


def _precio_portugal(peso_kg, zona_idx, data):
    """
    Calcula precio Portugal (zonas A-E → índice 0-4).
    Tramos: 10-100 kg (precio fijo), luego kg_rates escalados.
    """
    p = data['portugal']['precios']
    bp_fijo = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

    for bp in bp_fijo:
        if peso_kg <= bp:
            precio = p[str(bp)][zona_idx]
            return precio, f"Tramo {bp} kg Portugal"

    # Peso > 100 kg: usar tabla kg_rates
    bp_kg = [150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000]
    kr = p['kg_rates']

    precio_100 = p['100'][zona_idx]

    for i, bp in enumerate(bp_kg):
        if peso_kg <= bp:
            tasa = kr[str(bp)][zona_idx]
            precio = round(peso_kg * tasa, 2)
            if i > 0:
                bp_ant = bp_kg[i-1]
                tasa_ant = kr[str(bp_ant)][zona_idx]
                minimo = max(round(bp_ant * tasa_ant, 2), precio_100)
            else:
                minimo = precio_100
            precio_final = max(precio, minimo)
            desc = f"{peso_kg:.1f} kg × {tasa:.3f} €/kg (tramo hasta {bp} kg)"
            if precio_final > precio:
                desc += f" → mínimo {minimo:.2f}€"
            return precio_final, desc

    # Peso > 1000 kg
    tasa = kr['en_adelante'][zona_idx]
    precio = round(peso_kg * tasa, 2)
    minimo_1000 = round(1000 * kr['1000'][zona_idx], 2)
    precio_final = max(precio, minimo_1000)
    return precio_final, f"{peso_kg:.1f} kg × {tasa:.3f} €/kg (>1000 kg)"


def _precio_baleares_canarias(peso_kg, zona_idx, data):
    """
    Calcula precio Baleares/Canarias/Ceuta/Melilla (zonas 9-16 → índice 0-7).
    Tramos: hasta 1000 kg precio fijo, luego €/kg.
    """
    p = data['baleares_canarias']['precios']
    bp_fijo = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 125, 150, 175, 200,
               300, 400, 500, 600, 700, 800, 900, 1000]

    for bp in bp_fijo:
        if peso_kg <= bp:
            precio = p[str(bp)][zona_idx]
            return precio, f"Tramo {bp} kg"

    # Peso > 1000 kg: €/kg
    tasa = p['kg_rate'][zona_idx]
    precio = round(peso_kg * tasa, 2)
    precio_1000 = p['1000'][zona_idx]
    precio_final = max(precio, precio_1000)
    desc = f"{peso_kg:.1f} kg × {tasa:.3f} €/kg"
    if precio_final > precio:
        desc += f" → mínimo {precio_1000:.2f}€"
    return precio_final, desc


def calcular(destino, peso_real_kg, volumen_m3=None, importacion=False):
    """
    Calcula el precio Transaher para un envío.

    Args:
        destino: Nombre de la provincia/ciudad/zona destino
        peso_real_kg: Peso real en kg
        volumen_m3: Volumen en m³ (opcional)
        importacion: Si es True (retorno desde Portugal), aplica +15%

    Returns:
        dict con resultado y desglose
    """
    data = _load_data()

    # Buscar en qué área está el destino
    zona_pen, _ = buscar_zona_peninsular(destino, data)
    zona_pt, desc_pt = buscar_zona_portugal(destino, data)
    zona_bc, desc_bc = buscar_zona_baleares_canarias(destino, data)

    suplementos = []

    if zona_pen is not None:
        # Destino peninsular
        zona_idx = zona_pen - 1
        peso_tasable, desc_peso = calcular_peso_tasable(peso_real_kg, volumen_m3, destino, data, 'peninsular')
        precio_base, desc_precio = _precio_peninsular(peso_tasable, zona_idx, data)
        zona_str = f"Zona Peninsular {zona_pen} de 8"

    elif zona_pt is not None:
        # Destino Portugal
        letras = ['A', 'B', 'C', 'D', 'E']
        zona_idx = letras.index(zona_pt)
        tipo_vol = 'portugal'
        peso_tasable, desc_peso = calcular_peso_tasable(peso_real_kg, volumen_m3, destino, data, tipo_vol)
        precio_base, desc_precio = _precio_portugal(peso_tasable, zona_idx, data)
        zona_str = f"Portugal Zona {zona_pt} ({desc_pt})"

        if importacion:
            inc = round(precio_base * data['portugal']['importaciones_recargo_pct'] / 100, 2)
            suplementos.append(f"Recargo importación +{data['portugal']['importaciones_recargo_pct']}%: +{inc:.2f}€")

    elif zona_bc is not None:
        # Baleares, Canarias, Ceuta, Melilla, Gibraltar, Andorra
        zonas_bc = list(data['baleares_canarias']['zonas'].keys())
        zona_idx = zonas_bc.index(str(zona_bc))

        dn = _norm(destino)
        if any(_norm(x) == dn for x in ['IBIZA', 'EIVISSA', 'FORMENTERA', 'MALLORCA', 'MENORCA']):
            tipo_vol = 'baleares_mallorca_menorca'
        elif any(_norm(x) == dn for x in ['IBIZA', 'EIVISSA', 'FORMENTERA']):
            tipo_vol = 'baleares_islas_menores'
        else:
            tipo_vol = 'canarias'

        peso_tasable, desc_peso = calcular_peso_tasable(peso_real_kg, volumen_m3, destino, data, tipo_vol)
        precio_base, desc_precio = _precio_baleares_canarias(peso_tasable, zona_idx, data)
        zona_str = f"Zona {zona_bc}: {desc_bc}"

        # DUA si aplica
        dua_list = data['baleares_canarias']['dua_euros']
        if zona_idx < len(dua_list) and dua_list[zona_idx] is not None:
            suplementos.append(f"DUA (despacho aduanas): {dua_list[zona_idx]:.2f}€")

        # Seguro especial si aplica
        seg_list = data['baleares_canarias']['seguro_especial_pct']
        if zona_idx < len(seg_list) and seg_list[zona_idx] is not None:
            suplementos.append(f"Seguro especial: {seg_list[zona_idx]:.1f}% s/valor mercancía")

    else:
        return {
            'transportista': 'Transaher',
            'aplicable': False,
            'motivo': f"Destino '{destino}' no encontrado en zonas de Transaher.",
            'precio': None
        }

    precio_final = precio_base
    for sup in suplementos:
        # Los suplementos que sean % ya están calculados arriba; los fijos los sumamos
        if '€' in sup and '+' in sup:
            try:
                val = float(sup.split('+')[1].replace('€', '').strip())
                precio_final += val
            except Exception:
                pass
        elif 'DUA' in sup or 'despacho' in sup.lower():
            try:
                val = float(sup.split(':')[1].replace('€', '').strip())
                precio_final += val
            except Exception:
                pass

    return {
        'transportista': 'Transaher',
        'aplicable': True,
        'precio': round(precio_final, 2),
        'zona': zona_str,
        'peso_tasable': round(peso_tasable, 2),
        'desglose': {
            'peso': desc_peso,
            'zona': zona_str,
            'precio_base': f"{precio_base:.2f}€ ({desc_precio})",
            'suplementos': suplementos,
            'total': f"{precio_final:.2f}€",
            'iva_no_incluido': True,
            'combustible': "Suplemento combustible variable (2 meses decalaje, Ministerio Transición Ecológica)"
        }
    }


# --- TESTS ---
if __name__ == '__main__':
    casos = [
        # (destino, kg, m3, esperado_aprox)
        ('Alicante', 100, None, 11.68),     # Z1, 100kg
        ('Murcia', 100, None, 13.98),       # Z2, 100kg... wait Murcia es zona 2, idx=1
        ('Valencia', 200, None, 20.71),     # Z2, 200kg
        ('Madrid', 300, None, 34.49),       # Z3, 300kg
        ('Toledo', 500, None, 56.20),       # Z4, 500kg
        ('Sevilla', 700, None, 95.40),      # Z5, 700kg... Sevilla es zona 5
        ('Alicante', 50, None, 10.76),      # Z1, mínimo
        ('Coruña', 1000, None, 192.62),     # Z8, 1000kg
        ('Lisboa', 100, None, 32.25),       # Portugal Zona A... Lisboa→A, 100kg
        ('Mallorca', 50, None, None),       # Baleares zona 9
    ]

    print("=== TEST Transaher ===")
    for args in casos:
        destino, kg, m3, esperado = args
        r = calcular(destino, kg, m3)
        ok = ''
        if esperado and r['precio']:
            ok = '✓' if abs(r['precio'] - esperado) < 0.10 else f'⚠ esperado {esperado}'
        print(f"  {destino:15s} {kg:5.0f}kg → {str(r.get('precio','N/A')):>8} € | {r.get('zona','N/A')[:30]} {ok}")
