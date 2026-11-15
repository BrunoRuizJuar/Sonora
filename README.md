# SONORA

Prototipo de recomendación musical por letras, sonido y combinación de ambas señales.
Working directory de Windows: `B:\University\2027-1\SONORA`.
Repositorio: https://github.com/BrunoRuizJuar/Sonora.git

## Estado de esta entrega

Arquitectura y estructura inicial. Incluye documentación, configuración de ejemplo,
infraestructura de desarrollo y una API mínima de salud. El frontend, los adaptadores,
el pipeline, los modelos y los endpoints de recomendación están pendientes de implementación.
Los directorios vacíos indican su ubicación prevista. No incluye corpus, audio ni modelos entrenados.

## Documentos

- [Requisitos v1.2 (especificación vigente)](docs/REQUIREMENTS.md).
- [Corpus completo de letras y vínculos de la demo](docs/CORPUS_LETRAS.md).
- [Arquitectura completa](docs/ARQUITECTURA_SONORA.md).
- [Datos y fuentes](docs/DATOS_Y_FUENTES.md).
- [Contrato de API](docs/CONTRATO_API.md).
- [Ejecución en Windows](docs/WINDOWS.md).
- [Plan de implementación](docs/PLAN_IMPLEMENTACION.md).
- [Estructura exacta](docs/ESTRUCTURA.md).

## Inicio de la API mínima

Desde la raíz, con Python 3.11 instalado:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
$env:SONORA_HOME = (Get-Location).Path
.\.venv\Scripts\python.exe -m uvicorn sonora_api.main:app --host 127.0.0.1 --port 8000 --reload
```

Abrir `http://127.0.0.1:8000/docs` y `http://127.0.0.1:8000/api/v1/health/live`.
La ruta `/api/v1/health/ready` devuelve 503: todavía falta integrar datos y servicios.
Este resultado es intencional y evita presentar el scaffold como un recomendador listo.

El script `scripts/Initialize-SONORA.ps1` crea esta estructura en la carpeta de Windows,
configura `origin` y conserva archivos existentes. No descarga datos, instala dependencias,
genera credenciales, crea commits ni publica cambios.
