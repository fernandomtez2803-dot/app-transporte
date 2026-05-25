"""
Calculador de tarifas Antonio Marco.
CAMIÓN COMPLETO SIEMPRE. Precio fijo por destino desde Beneixama.
No se puede escoger fracción de carga.
"""
import json
import os
import unicodedata


def _load_data():
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'antonio_marco.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _normalizar(texto):
    texto = texto.upper().strip()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto)
                    if unicodedata.category(c) != 'Mn')
    return texto


def buscar_destino(destino, data):
    """Busca el destino en la tabla. Devuelve (precio, nombre_destino_encontrado) o (None, None)."""
    destino_norm = _normalizar(destino)
    for dest, precio in data['destinos'].items():
        if _normalizar(dest) == destino_norm:
            return precio, dest

    # Búsqueda parcial para casos como "A Coruña" → "CORUÑA"
    for dest, precio in data['destinos'].items():
        if destino_norm in _normalizar(dest) or _normalizar(dest) in destino_norm:
            return precio, dest

    # "Vizcaya" → "BILBAO"
    alias = {
        'VIZCAYA': 'BILBAO',
        'PAIS VASCO': 'BILBAO',
        'EUSKADI': 'BILBAO',
        'PONTEVEDRA': 'GALICIA',
        'LUGO': 'GALICIA',
        'ORENSE': 'GALICIA',
        'OURENSE': 'GALICIA',
        'A CORUNA': 'GALICIA',
    }
    if destino_norm in alias:
        return data['destinos'].get(alias[destino_norm]), alias[destino_norm]

    return None, None


def calcular(destino, **kwargs):
    """
    Calcula el precio Antonio Marco para un envío.

    Args:
        destino: Nombre de la provincia/ciudad destino

    Returns:
        dict con resultado y desglose
    """
    data = _load_data()

    precio, dest_encontrado = buscar_destino(destino, data)

    if precio is None:
        return {
            'transportista': 'Antonio Marco',
            'aplicable': False,
            'motivo': (
                f"Destino '{destino}' no está en la lista de destinos de Antonio Marco. "
                f"Destinos disponibles: {', '.join(data['destinos'].keys())}"
            ),
            'precio': None
        }

    return {
        'transportista': 'Antonio Marco',
        'aplicable': True,
        'precio': float(precio),
        'zona': 'Camión completo',
        'peso_tasable': None,
        'desglose': {
            'tipo': 'CAMIÓN COMPLETO — precio fijo independientemente de la carga',
            'destino_encontrado': dest_encontrado,
            'precio_base': f"{precio:.2f}€ (tarifa fija)",
            'suplementos': [],
            'total': f"{precio:.2f}€",
            'iva_no_incluido': True,
            'aviso': 'Este precio es para camión completo siempre. No aplica para envíos parciales.'
        }
    }


# --- TESTS ---
if __name__ == '__main__':
    casos = [
        ('Murcia', 330),
        ('Valencia', 380),
        ('Madrid', 690),
        ('Barcelona', 780),
        ('Galicia', 1430),
        ('Coruña', 1430),
        ('Bilbao', 1005),
        ('Vizcaya', 1005),
        ('Sevilla', 930),
        ('Almeria', None),     # No está en lista → no aplicable
        ('Toledo', 680),
        ('Girona', 810),
    ]

    print("=== TEST Antonio Marco ===")
    for destino, esperado in casos:
        r = calcular(destino)
        ok = ''
        if esperado and r['precio']:
            ok = '✓' if abs(r['precio'] - esperado) < 0.01 else f'⚠ esperado {esperado}'
        elif esperado is None and not r['aplicable']:
            ok = '✓ (no aplicable)'
        print(f"  {destino:15s} → {str(r.get('precio','N/A')):>8} € {ok}")
        if not r['aplicable']:
            print(f"    ⚠ {r['motivo'][:80]}")
