# Plan de implementación

> **Nota (2026-11-12):** plan anterior a v1.2. Las fases vigentes están en
> [`REQUIREMENTS.md`](REQUIREMENTS.md) §17; M2 se sustituye por la preparación del corpus
> completo y la vinculación de las 886 pistas FMA Medium ([`CORPUS_LETRAS.md`](CORPUS_LETRAS.md)),
> sin piloto de 500 casos ni dependencia de AcousticBrainz.

| Fase | Entregable | Criterio de salida |
|---|---|---|
| M0 | Estructura, Git y documentación | Carpetas, remoto correcto y API de salud funcionando |
| M1 | Infraestructura local | CouchDB y OpenSearch accesibles; bases e índices inicializados |
| M2 | Datos y cobertura | Corpus canónico, IDs/vínculos auditados e informe de unos 500 casos |
| M3 | Letras | TF-IDF y embeddings propios comparados; Top-K reproducible |
| M4 | Acústica | Esquema, calidad, escalador y vecinos evaluados; fuente aceptada con evidencia |
| M5 | Mixto | Elegibilidad, normalización, pesos y diversidad probados |
| M6 | Web | Diseño aprobado, búsqueda, controles, resultados y estados integrados |
| M7 | Evaluación y acceso | Juicios humanos, métricas y prototipo publicado por enlace |

La fase M4 depende del resultado de cobertura; si AcousticBrainz falla, se documenta y se
trabaja con un catálogo pequeño de audio verificado. No se declara terminado el modo musical
por tener un nombre de fuente o un script de descarga.

## Comprobaciones que deben acompañar la implementación

- Integridad de IDs, filas de vectores, dimensiones y versiones.
- Separación de versiones/letras duplicadas entre particiones.
- Uso de la misma transformación de texto/audio en entrenamiento e inferencia.
- Modos y filtros: exclusiones, datos faltantes, límites por artista y catálogos pequeños.
- Comparación de recuperación aproximada con búsqueda exacta sobre una muestra.
- Contrato API y comportamiento ante servicios no disponibles.
- Métricas de ranking con relevancia definida y cobertura real por modo.

## Entregas experimentales

Cada experimento conserva configuración, semilla, revisión de datos, dependencias,
artefactos y métricas. Los notebooks sirven para explorar y reportar; el código reutilizable
se mueve a `packages/sonora/src/sonora/` antes de integrarlo en la aplicación.
