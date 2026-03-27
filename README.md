# Receipts Parser POC (PaddleOCR + Ollama)

Script para extraer texto desde imágenes dentro de una carpeta usando `PaddleOCR`, guardar el resultado en JSON/texto, y opcionalmente estructurar el ticket con `Ollama` para exportar un CSV.

## Requisitos

- Python `3.12+`
- [Poetry](https://python-poetry.org/)

## Estructura del proyecto

- `parse_folder_with_paddleocr.py`: CLI principal (orquesta OCR, escritura de outputs y el paso opcional con Ollama)
- `ocr_parsing.py`: lógica de OCR (PaddleOCR, parseo por imagen, concatenación de texto)
- `llm_receipt.py`: integración con Ollama (request/response JSON) + export CSV
- `input/`: carpeta de entrada (imágenes a procesar) — **ignorada por git**
- `output/`: carpeta base de salida — **ignorada por git**

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
- `--output` (opcional): carpeta base de salida (default: `output`). Dentro se crean `json_output/`, `text_output/` y (si usas `--ollama`) `csv_output/`
- `--lang` (opcional): idioma para PaddleOCR (default: `es`)
- `--use-angle-cls` (opcional): activa clasificador de rotacion
- `--log-level` (opcional): `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)
- `--ollama` (opcional): habilita el paso de LLM (Ollama) y escribe un CSV por imagen en `csv_output/`
- `--ollama-host` (opcional): URL base de Ollama (default: `http://127.0.0.1:11434`)
- `--ollama-model` (opcional): nombre del modelo en Ollama (default: `llama3.2` — ajusta según tus modelos instalados)

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

Si habilitas `--ollama`, además:

- `output/csv_output/<nombre_imagen>.csv`: un CSV por imagen (una fila por ítem detectado)

Columnas del CSV:

- `source_file`
- `date`
- `currency`
- `item_description`
- `quantity`
- `unit_price`
- `line_total`
- `receipt_total`
- `payment_method`

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
- Si Ollama devuelve `model not found`:
  - instala o usa un modelo existente (ej: `ollama list`, luego `--ollama-model llama3:latest`)

