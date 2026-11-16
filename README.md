# Limpiador de Escaneos (hojas en blanco y recicladas)

Aplicación de escritorio (Windows, GUI con Tkinter) para analizar archivos escaneados (PDF o imágenes), **detectar hojas en blanco** y **detectar hojas que parecen recicladas** (tono/textura), con acciones editables por página.

## Funciones
- Carga de **PDF** e imágenes (`.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.bmp`, `.webp`).
- Detección automática con puntajes y umbrales ajustables:
  - **Hoja en blanco**: baja densidad de tinta/contenido.
  - **Hoja reciclada**: heurística por color de fondo y textura/moteado (aproximado).
- **Acciones por defecto** configurables (conservar / eliminar / separar) y **edición manual por página** en la tabla/vista previa.
- Exportación a PDF(s): limpio, eliminadas y/o separadas según la acción asignada.

> Nota: la detección de papel reciclado es heurística (basada en apariencia). Revisa la vista previa y ajusta umbrales/acciones según tus escaneos.

## Requisitos
- Python 3.10+ (probado con Python 3.x en Windows)
- Dependencias:
  - `pymupdf`
  - `pillow`
  - `numpy`
  - `opencv-python-headless` (o `opencv-python`)

Instalación de dependencias:
```bash
python -m pip install pymupdf pillow numpy opencv-python-headless
```

## Uso
Desde la carpeta del proyecto:
```bash
python run_scan_cleaner.py
```
o bien:
```bash
python -m scan_cleaner
```

1. **Abrir archivo...** y selecciona un PDF o imagen escaneada.
2. Ajusta **umbrales** y **acciones por defecto** si es necesario y pulsa **Reanalizar**.
3. Selecciona páginas en la lista para ver la vista previa y **cambia la acción** de esa página (conservar/eliminar/separar).
4. **Exportar resultado...** elige una carpeta; se generarán los PDF según las acciones asignadas (`*_limpio.pdf`, `*_eliminadas.pdf`, `*_recicladas_o_separadas.pdf`).

## Estructura
- `scan_cleaner/detectors/blank.py` – heurística de hoja en blanco
- `scan_cleaner/detectors/recycled.py` – heurística de hoja reciclada
- `scan_cleaner/document.py` – carga y exportación de documentos
- `scan_cleaner/analysis.py` – análisis por página
- `scan_cleaner/app.py` – interfaz gráfica (Tkinter)
