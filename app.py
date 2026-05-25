"""
App de comparación de tarifas de transporte — Agroserc
Transportistas: RDA Ramoneda, Antonio Marco, Transaher, Carreras
"""
from flask import Flask, render_template, request, jsonify
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from calculators import ramoneda, antonio_marco, transaher, carreras

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/calcular', methods=['POST'])
def calcular():
    datos = request.get_json()

    destino = datos.get('destino', '').strip()
    peso_kg = float(datos.get('peso_kg', 0) or 0)
    volumen_m3 = float(datos.get('volumen_m3', 0) or 0) or None
    n_pallets = int(datos.get('n_pallets', 0) or 0) or None
    temperatura = datos.get('temperatura', 'ambiente')
    llegada_rda = datos.get('llegada_rda', False)
    importacion_pt = datos.get('importacion_pt', False)

    if not destino:
        return jsonify({'error': 'Indica el destino'}), 400
    if peso_kg <= 0:
        return jsonify({'error': 'El peso debe ser mayor que 0'}), 400

    resultados = []

    # 1. RDA Ramoneda
    try:
        r = ramoneda.calcular(destino, peso_kg, volumen_m3, llegada=llegada_rda)
        resultados.append(r)
    except Exception as e:
        resultados.append({
            'transportista': 'RDA Ramoneda',
            'aplicable': False,
            'motivo': f"Error de cálculo: {e}",
            'precio': None
        })

    # 2. Antonio Marco (camión completo)
    try:
        r = antonio_marco.calcular(destino)
        resultados.append(r)
    except Exception as e:
        resultados.append({
            'transportista': 'Antonio Marco',
            'aplicable': False,
            'motivo': f"Error de cálculo: {e}",
            'precio': None
        })

    # 3. Transaher
    try:
        r = transaher.calcular(destino, peso_kg, volumen_m3, importacion=importacion_pt)
        resultados.append(r)
    except Exception as e:
        resultados.append({
            'transportista': 'Transaher',
            'aplicable': False,
            'motivo': f"Error de cálculo: {e}",
            'precio': None
        })

    # 4. Carreras
    try:
        r = carreras.calcular(destino, peso_kg, volumen_m3, n_pallets, temperatura)
        resultados.append(r)
    except Exception as e:
        resultados.append({
            'transportista': 'Carreras Grupo Logístico',
            'aplicable': False,
            'motivo': f"Error de cálculo: {e}",
            'precio': None
        })

    # Ordenar aplicables por precio
    aplicables = [r for r in resultados if r.get('aplicable') and r.get('precio') is not None]
    no_aplicables = [r for r in resultados if not r.get('aplicable') or r.get('precio') is None]

    aplicables_sorted = sorted(aplicables, key=lambda x: x['precio'])

    # Marcar el más barato
    if aplicables_sorted:
        aplicables_sorted[0]['es_mas_barato'] = True
        # Diferencia porcentual con el más caro
        if len(aplicables_sorted) > 1:
            mas_barato = aplicables_sorted[0]['precio']
            for r in aplicables_sorted[1:]:
                if r['precio'] > 0:
                    r['diferencia_pct'] = round((r['precio'] - mas_barato) / mas_barato * 100, 1)

    return jsonify({
        'aplicables': aplicables_sorted,
        'no_aplicables': no_aplicables,
        'total_comparados': len(resultados)
    })


@app.route('/provincias')
def provincias():
    """Lista de provincias/destinos disponibles para autocompletar."""
    lista = [
        "Alicante", "Albacete", "Almería", "Ávila", "Badajoz", "Baleares",
        "Barcelona", "Burgos", "Cáceres", "Cádiz", "Cantabria", "Castellón",
        "Ciudad Real", "Córdoba", "Coruña", "Cuenca", "Gerona", "Granada",
        "Guadalajara", "Guipúzcoa", "Huelva", "Huesca", "Jaén", "León",
        "Lérida", "La Rioja", "Lugo", "Madrid", "Málaga", "Murcia",
        "Navarra", "Orense", "Asturias", "Palencia", "Gran Canaria",
        "Pontevedra", "Salamanca", "Tenerife", "Segovia", "Sevilla",
        "Soria", "Tarragona", "Teruel", "Toledo", "Valencia", "Valladolid",
        "Vizcaya", "Zamora", "Zaragoza",
        # Portugal
        "Lisboa", "Porto", "Braga", "Coimbra", "Aveiro", "Leiria",
        "Santarém", "Setúbal", "Faro", "Évora", "Beja", "Viseu",
        "Castelo Branco", "Guarda", "Bragança", "Viana do Castelo", "Vila Real",
        # Otros
        "Mallorca", "Menorca", "Ibiza", "Andorra", "Ceuta", "Melilla"
    ]
    return jsonify(sorted(lista))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
