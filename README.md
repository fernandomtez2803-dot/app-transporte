# 🚚 App Transporte — Comparador de Tarifas Agroserc

Aplicación web para comparar tarifas de transporte de diferentes transportistas, desarrollada para **Agroserc S.A.**

## 📋 Descripción

Esta herramienta permite calcular y comparar precios de envío entre varios transportistas de forma rápida y visual, facilitando la toma de decisiones logísticas.

### Transportistas disponibles

| Transportista | Tipo |
|---|---|
| **RDA Ramoneda** | Paquetería / Grupaje |
| **Antonio Marco** | Camión completo |
| **Transaher** | Paquetería / Grupaje |
| **Carreras Grupo Logístico** | Paquetería / Grupaje |

## 🚀 Instalación

### Requisitos previos

- Python 3.10+
- pip

### Pasos

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/fernandomtez2803-dot/app-transporte.git
   cd app-transporte
   ```

2. **Crear entorno virtual** (recomendado)
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar la aplicación**
   ```bash
   python app.py
   ```

5. **Abrir en el navegador**
   ```
   http://localhost:5000
   ```

## 🛠️ Tecnologías

- **Backend:** Python / Flask
- **Frontend:** HTML5, CSS3, JavaScript
- **Datos:** JSON (tarifas por transportista)

## 📁 Estructura del proyecto

```
app-transporte/
├── app.py                  # Aplicación Flask principal
├── requirements.txt        # Dependencias Python
├── calculators/            # Módulos de cálculo por transportista
│   ├── __init__.py
│   ├── ramoneda.py
│   ├── antonio_marco.py
│   ├── transaher.py
│   └── carreras.py
├── data/                   # Datos de tarifas (JSON)
│   ├── ramoneda.json
│   ├── antonio_marco.json
│   ├── transaher.json
│   └── carreras.json
├── templates/              # Plantillas HTML
│   └── index.html
└── static/                 # Archivos estáticos (CSS, JS, imágenes)
```

## 📝 Uso

1. Introduce el **destino** (provincia española o ciudad portuguesa).
2. Indica el **peso** en kg.
3. Opcionalmente, añade **volumen** (m³) y **número de pallets**.
4. Selecciona la **temperatura** (ambiente o refrigerado).
5. Marca opciones adicionales si aplica (llegada RDA, importación Portugal).
6. Pulsa **Calcular** para ver la comparativa de precios.

## 📄 Licencia

Proyecto privado de uso interno — **Agroserc S.A.** © 2026
