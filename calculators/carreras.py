"""
Calculador de tarifas Carreras Grupo Logístico.
Dos modalidades: CAPILAR (€/kg) y DIRECTOS (€/envío por pallets).
- Capilar: hasta 6 pallets, precio por kg con mínimo por envío.
- Directos: 7+ pallets, precio fijo por banda de pallets.
- Temperatura ambiente y controlada disponibles.
- Factor conversión: 270 kg/m³ (peninsular), 333 kg/m³ (islas/Ceuta/Melilla).
"""
import json
import os
import unicodedata


def _load_data():
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'carreras.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _norm(texto):
    texto = texto.upper().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto)
                   if unicodedata.category(c) != 'Mn')


# Mapa de alias/variantes para buscar código de provincia ES
ALIAS_PROVINCIAS = {
    'ALAVA': 'ES01', 'ARABA': 'ES01',
    'ALBACETE': 'ES02',
    'ALICANTE': 'ES03', 'ALACANT': 'ES03',
    'ALMERIA': 'ES04', 'ALMERÍA': 'ES04',
    'AVILA': 'ES05', 'ÁVILA': 'ES05',
    'BADAJOZ': 'ES06',
    'BALEARES': 'ES07', 'ILLES BALEARS': 'ES07', 'MALLORCA': 'ES07',
    'MENORCA': 'ES07', 'IBIZA': 'ES07', 'EIVISSA': 'ES07',
    'BARCELONA': 'ES08',
    'BURGOS': 'ES09',
    'CACERES': 'ES10', 'CÁCERES': 'ES10',
    'CADIZ': 'ES11', 'CÁDIZ': 'ES11',
    'CASTELLON': 'ES12', 'CASTELLÓN': 'ES12',
    'CIUDAD REAL': 'ES13',
    'CORDOBA': 'ES14', 'CÓRDOBA': 'ES14',
    'CORUNA': 'ES15', 'CORUÑA': 'ES15', 'A CORUNA': 'ES15', 'A CORUÑA': 'ES15',
    'CUENCA': 'ES16',
    'GERONA': 'ES17', 'GIRONA': 'ES17',
    'GRANADA': 'ES18',
    'GUADALAJARA': 'ES19',
    'GUIPUZCOA': 'ES20', 'GUIPÚZCOA': 'ES20', 'GIPUZKOA': 'ES20',
    'HUELVA': 'ES21',
    'HUESCA': 'ES22',
    'JAEN': 'ES23', 'JAÉN': 'ES23',
    'LEON': 'ES24', 'LEÓN': 'ES24',
    'LERIDA': 'ES25', 'LÉRIDA': 'ES25', 'LLEIDA': 'ES25',
    'LA RIOJA': 'ES26', 'RIOJA': 'ES26',
    'LUGO': 'ES27',
    'MADRID': 'ES28',
    'MALAGA': 'ES29', 'MÁLAGA': 'ES29',
    'MURCIA': 'ES30',
    'NAVARRA': 'ES31',
    'ORENSE': 'ES32', 'OURENSE': 'ES32',
    'ASTURIAS': 'ES33',
    'PALENCIA': 'ES34',
    'GRAN CANARIA': 'ES35', 'LAS PALMAS': 'ES35',
    'PONTEVEDRA': 'ES36',
    'SALAMANCA': 'ES37',
    'TENERIFE': 'ES38', 'SANTA CRUZ DE TENERIFE': 'ES38',
    'CANTABRIA': 'ES39',
    'SEGOVIA': 'ES40',
    'SEVILLA': 'ES41',
    'SORIA': 'ES42',
    'TARRAGONA': 'ES43',
    'TERUEL': 'ES44',
    'TOLEDO': 'ES45',
    'VALENCIA': 'ES46', 'VALENCIA / ALICANTE': 'ES46',
    'VALLADOLID': 'ES47',
    'VIZCAYA': 'ES48', 'BIZKAIA': 'ES48', 'BILBAO': 'ES48',
    'ZAMORA': 'ES49',
    'ZARAGOZA': 'ES50',
    # Portugal
    'LISBOA': 'PT_LISBOA',
    'SANTAREM': 'PT_SANTAREM', 'SANTARÉM': 'PT_SANTAREM',
    'SETUBAL': 'PT_SETUBAL', 'SETÚBAL': 'PT_SETUBAL',
    'AVEIRO': 'PT_AVEIRO',
    'COIMBRA': 'PT_COIMBRA',
    'LEIRIA': 'PT_LEIRIA',
    'BRAGA': 'PT_BRAGA',
    'PORTO': 'PT_PORTO',
    'BEJA': 'PT_BEJA',
    'CASTELO BRANCO': 'PT_CASTELO BRANCO',
    'EVORA': 'PT_EVORA', 'ÉVORA': 'PT_EVORA',
    'GUARDA': 'PT_GUARDA',
    'PORTALEBRE': 'PT_PORTALEBRE',
    'VISEU': 'PT_VISEU',
    'BRAGANCA': 'PT_BRAGANÇA', 'BRAGANÇA': 'PT_BRAGANÇA',
    'FARO': 'PT_FARO',
    'VIANA DO CASTELO': 'PT_VIANA DO CASTELO',
    'VILA REAL': 'PT_VILA REAL',
}


def buscar_codigo(destino):
    """Devuelve el código ES/PT para el destino o None."""
    dn = _norm(destino)
    # Primero exacto
    for alias, cod in ALIAS_PROVINCIAS.items():
        if _norm(alias) == dn:
            return cod
    # Luego parcial
    for alias, cod in ALIAS_PROVINCIAS.items():
        if dn in _norm(alias) or _norm(alias) in dn:
            return cod
    return None


def calcular_peso_tasable(peso_real_kg, volumen_m3, codigo, data):
    """Calcula peso tasable con factor Carreras."""
    if volumen_m3 is None or volumen_m3 <= 0:
        return peso_real_kg, "Peso real"

    islas_ceuta = ['ES07', 'ES35', 'ES38']  # Baleares, Gran Canaria, Tenerife
    factor = data['factor_volumen']['islas_ceuta_melilla'] if codigo in islas_ceuta \
        else data['factor_volumen']['peninsular']

    peso_vol = volumen_m3 * factor
    if peso_vol > peso_real_kg:
        return peso_vol, f"Peso volumétrico ({volumen_m3:.3f} m³ × {factor} kg/m³ = {peso_vol:.1f} kg)"
    return peso_real_kg, f"Peso real ({peso_real_kg:.1f} kg > {peso_vol:.1f} kg volumétrico)"


def _calcular_capilar(peso_tasable, info, data):
    """
    Calcula precio capilar para un destino.
    info = {'minimo': float, 'bandas': [6 tasas]} según bandas_peso_kg.
    Regla: precio = max(minimo, peso × tasa_banda).
    Cumplir 'no inferior al máximo de la fracción anterior'.
    """
    bandas_kg = data['bandas_peso_kg']  # [200, 500, 1000, 1500, 2500, 999999]
    minimo = info['minimo']
    tasas = info['bandas']

    # Encontrar la banda correcta
    banda_idx = len(bandas_kg) - 1
    for i, limite in enumerate(bandas_kg):
        if peso_tasable <= limite:
            banda_idx = i
            break

    tasa = tasas[banda_idx]
    precio_calculado = round(peso_tasable * tasa, 2)

    # Precio del máximo de la banda anterior (para la regla de mínimo)
    if banda_idx > 0:
        limite_ant = bandas_kg[banda_idx - 1]
        tasa_ant = tasas[banda_idx - 1]
        precio_banda_ant = round(limite_ant * tasa_ant, 2)
        precio_minimo_ant = max(precio_banda_ant, minimo)
    else:
        precio_minimo_ant = minimo

    precio_final = max(precio_calculado, precio_minimo_ant)

    limite_banda = bandas_kg[banda_idx]
    desc_banda = f"0-{bandas_kg[0]} kg" if banda_idx == 0 else f"{bandas_kg[banda_idx-1]+1}-{limite_banda} kg"
    if limite_banda == 999999:
        desc_banda = f">{ bandas_kg[-2]} kg"

    desc = f"{peso_tasable:.1f} kg × {tasa:.4f} €/kg (banda {desc_banda})"
    if precio_final > precio_calculado:
        desc += f" → ajustado a {precio_final:.2f}€ (mínimo {precio_minimo_ant:.2f}€)"
    elif precio_final == minimo and precio_final > precio_calculado:
        desc += f" → mínimo envío {minimo:.2f}€"

    return precio_final, desc, minimo


def _calcular_directos(n_pallets, info_directos):
    """
    Calcula precio directos por banda de pallets.
    info_directos = {'bandas': [8 precios para 8 bandas de pallets]}
    Bandas: [7-8, 9-11, 12-13, 14-16, 17-18, 19-21, 22-23, >23]
    """
    bandas = [[7, 8], [9, 11], [12, 13], [14, 16], [17, 18], [19, 21], [22, 23], [24, 9999]]

    for i, (min_p, max_p) in enumerate(bandas):
        if min_p <= n_pallets <= max_p:
            precio = info_directos['bandas'][i]
            desc = f"{n_pallets} pallets → banda {min_p}-{max_p if max_p < 9999 else '>'}: {precio:.2f}€/envío"
            return precio, desc

    return None, f"Número de pallets fuera de rango: {n_pallets}"


def calcular(destino, peso_real_kg, volumen_m3=None, n_pallets=None, temperatura='ambiente'):
    """
    Calcula el precio Carreras para un envío.

    Args:
        destino: Nombre de la provincia/ciudad destino
        peso_real_kg: Peso real en kg
        volumen_m3: Volumen en m³ (opcional)
        n_pallets: Número de pallets (determina si usa capilar o directos)
        temperatura: 'ambiente' o 'controlada' (12-18°C)

    Returns:
        dict con resultado y desglose
    """
    data = _load_data()

    codigo = buscar_codigo(destino)
    if codigo is None:
        return {
            'transportista': 'Carreras Grupo Logístico',
            'aplicable': False,
            'motivo': f"Destino '{destino}' no encontrado en las zonas de Carreras.",
            'precio': None
        }

    peso_tasable, desc_peso = calcular_peso_tasable(peso_real_kg, volumen_m3, codigo, data)

    es_portugal = codigo.startswith('PT_')
    n_pallets = n_pallets or 0

    # Decidir capilar o directos
    usar_directos = (n_pallets >= 7) and not es_portugal and codigo != 'ES07'  # Baleares solo capilar

    resultados = []

    if temperatura == 'controlada':
        tabla_cap = data['capilar_temp_controlada']['portugal' if es_portugal else 'espana']
        tabla_dir = None  # Los directos T.C. no tienen tabla completa
    else:
        tabla_cap = data['capilar_espana_ambiente'] if not es_portugal else data['capilar_portugal_ambiente']
        tabla_dir = data['directos_espana_ambiente']

    # --- Capilar ---
    if es_portugal:
        clave = codigo.replace('PT_', '')
        info_cap = tabla_cap.get(clave)
    else:
        info_cap = tabla_cap.get(codigo)

    if info_cap:
        precio_cap, desc_cap, minimo_cap = _calcular_capilar(peso_tasable, info_cap, data)
        prov_nombre = info_cap.get('provincia', destino)

        resultados.append({
            'modalidad': 'Capilar',
            'precio': round(precio_cap, 2),
            'desc_precio': desc_cap,
            'minimo': minimo_cap,
            'prov': prov_nombre
        })

    # --- Directos (solo si aplica) ---
    if usar_directos and tabla_dir and codigo in tabla_dir:
        info_dir = tabla_dir[codigo]
        precio_dir, desc_dir = _calcular_directos(n_pallets, info_dir)
        if precio_dir is not None:
            resultados.append({
                'modalidad': 'Directos',
                'precio': round(precio_dir, 2),
                'desc_precio': desc_dir,
                'prov': info_dir.get('provincia', destino)
            })

    if not resultados:
        return {
            'transportista': 'Carreras Grupo Logístico',
            'aplicable': False,
            'motivo': f"No se encontró tarifa para '{destino}' (código: {codigo}) en las tablas de Carreras.",
            'precio': None
        }

    # Directos es obligatorio para 7+ pallets (cuando está disponible)
    # Si usar_directos y hay tarifa directos → usar directos; si no, capilar
    if usar_directos and any(r['modalidad'] == 'Directos' for r in resultados):
        mejor = next(r for r in resultados if r['modalidad'] == 'Directos')
    else:
        mejor = resultados[0]

    precio_final = mejor['precio']
    modalidad = mejor['modalidad']

    suplementos = []
    if temperatura == 'controlada':
        suplementos.append("Temperatura controlada 12-18°C (+/- 2°)")

    return {
        'transportista': 'Carreras Grupo Logístico',
        'aplicable': True,
        'precio': precio_final,
        'zona': f"{mejor['prov']} ({codigo})",
        'peso_tasable': round(peso_tasable, 2),
        'modalidad': modalidad,
        'desglose': {
            'peso': desc_peso,
            'modalidad': modalidad,
            'precio_base': f"{mejor['precio']:.2f}€ ({mejor['desc_precio']})",
            'suplementos': suplementos,
            'total': f"{precio_final:.2f}€",
            'iva_no_incluido': True,
            'combustible': "Revisión gasoil mensual (base 1.50€/L). Si variación >±5% se aplica cargo sobre 30% de facturación mensual.",
            'alternativas': [r for r in resultados if r['modalidad'] != modalidad]
        }
    }


# --- TESTS ---
if __name__ == '__main__':
    casos = [
        # (destino, kg, m3, pallets, esperado_aprox, nota)
        ('Alicante', 100, None, 1, None, "local, pocos kg"),
        ('Madrid', 300, None, 2, None, "capilar 2 pallets"),
        ('Valencia', 500, None, 4, None, "capilar 4 pallets"),
        ('Murcia', 1000, None, 7, None, "directos 7 pallets"),
        ('Sevilla', 200, None, 1, None, "capilar 1 pallet"),
        ('Barcelona', 10, None, 8, None, "directos 8 pallets"),
        ('Baleares', 200, None, 2, None, "baleares, solo capilar"),
        ('Lisboa', 300, None, 3, None, "portugal capilar"),
    ]

    print("=== TEST Carreras ===")
    for destino, kg, m3, pallets, esperado, nota in casos:
        r = calcular(destino, kg, m3, pallets)
        print(f"  {destino:15s} {kg:5.0f}kg {pallets}p → {str(r.get('precio','N/A')):>8} € | {r.get('modalidad','N/A')} | {nota}")
        if r.get('desglose') and r['desglose'].get('alternativas'):
            for alt in r['desglose']['alternativas']:
                print(f"    Alt. {alt['modalidad']}: {alt['precio']:.2f}€ ({alt['desc_precio'][:60]})")
        if not r['aplicable']:
            print(f"    ⚠ {r['motivo'][:80]}")
