# Receipts Parser POC (PaddleOCR)

Script simple para extraer texto desde imagenes dentro de una carpeta usando `PaddleOCR`, y guardar el resultado en JSON.

## Requisitos

- Python `3.12+`
- [Poetry](https://python-poetry.org/)

## Estructura del proyecto

- `parse_folder_with_paddleocr.py`: script principal de OCR
- `input/`: carpeta de entrada (imagenes a procesar)
- `output/`: carpeta base de salida (ver subcarpetas abajo)

## Instalacion con Poetry

Desde la raiz del proyecto:

```bash
poetry env use python3.12
poetry install
```

> Nota: `paddlepaddle` y dependencias (p. ej. `opencv`) son paquetes pesados; la primera instalacion puede tardar. Si `pip` corta por tiempo de espera, puedes usar `poetry run python -m pip install --default-timeout 1200` para reinstalar.

## Ejecutar el script

Comando recomendado:

```bash
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True poetry run python parse_folder_with_paddleocr.py --input ./input --output ./output
```

## Parametros disponibles

```bash
poetry run python parse_folder_with_paddleocr.py --help
```

Opciones principales:

- `--input` (requerido): carpeta con imagenes
- `--output` (opcional): carpeta base de salida (default: `output`). Dentro se crean `json_output/` y `text_output/`
- `--lang` (opcional): idioma para PaddleOCR (default: `es`)
- `--use-angle-cls` (opcional): activa clasificador de rotacion
- `--log-level` (opcional): `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)

## Formatos soportados

El script procesa estos formatos:

- `.png`
- `.jpg`
- `.jpeg`
- `.bmp`
- `.tif`
- `.tiff`
- `.webp`

## Logs

El script incluye logs con timestamp y nivel:

- inicio de corrida
- carpeta de entrada/salida
- cantidad de archivos detectados
- progreso por archivo
- guardado final

Ejemplo con logs mas detallados:

```bash
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True poetry run python parse_folder_with_paddleocr.py --input ./input --output ./output --log-level DEBUG
```

## Salida (json_output y text_output)

Con `--output ./output` (o el directorio que elijas), se crea esta estructura:

- `output/json_output/ocr_results.json`: mismo JSON agregado que antes (todas las imagenes en un solo archivo)
- `output/text_output/<nombre_imagen>.txt`: un archivo de texto por imagen, con las lineas OCR concatenadas (una linea de texto por linea detectada, legible)

## Salida JSON

El archivo `json_output/ocr_results.json` tiene este esquema general:

- `input_folder`: path absoluto de entrada
- `files`: lista por archivo con:
  - `file`
  - `full_path`
  - `line_count`
  - `lines` (texto, confianza y bounding box)

## Troubleshooting rapido

- Si se queda en chequeo de conectividad:
  - usar `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True`
- Si la instalacion tarda o falla por timeout:
  - repetir comando con `--default-timeout 1200`
- Warning de import en editor (`paddleocr`):
  - suele ser del entorno del IDE, no del runtime de Poetry

