# Arquitectura vigente para la implementación

Esta nota sustituye las propuestas antiguas en lo que contradigan REQUISITOS_SONORA.md v1.2.
El código real se debe inspeccionar antes de crear carpetas duplicadas.

## Dos escalas, una identidad

1. Corpus de letras: toda letra válida en inglés de los diez Parquet, sin condición de audio.
2. Catálogo demo: subconjunto FMA Medium vinculado al corpus textual, empezando con 886 exactas.

Separar `lyrics_id` (documento/letra), `recording_id` o `track_id` (grabación) y claves de fuente.
Conservar todos los localizadores originales aunque varias letras se consoliden por hash.
Una relación letra–grabación es potencialmente muchos-a-muchos. No unir tablas usando sólo título.
El split textual y los grupos relacionados se propagan a grabaciones de la demo.

## Capas

- Offline: ingesta, limpieza, idioma, deduplicación, splits, prácticas, modelos y audio.
- Dominio Python compartido: representaciones, similitudes, mezcla, filtros y evaluación.
- FastAPI: búsqueda, metadatos, recomendaciones, comparaciones y evaluaciones.
- Web existente HTML/CSS/JS: conectar sin rediseño ni migración obligatoria a Next.js.
- Datos: Parquet/JSON para tablas, manifiestos y controles; archivos para modelos y audio.
- CouchDB/OpenSearch forman parte de la referencia posterior; no son requisitos para limpiar
  Genius ni para el primer ranking exacto. Redis opcional y sólo con una necesidad medida.
- Extracción acústica propia desde FMA. MusicBrainz opcional; AcousticBrainz no es dependencia.

## Carpetas por responsabilidad

| Ruta | Contenido |
|---|---|
| `data/raw/genius/` | Diez Parquet originales |
| `data/raw/fma/` | Metadatos y audio originales |
| `data/interim/matching/` | Ejecuciones de cruce y selección revisada |
| `data/interim/lyrics/` | Ingesta y anotaciones incrementales |
| `data/processed/lyrics/<run_id>/` | Corpus limpio completo y correspondencias |
| `data/processed/demo/<run_id>/` | Vínculos y capacidades de la demo |
| `manifests/` | Fuentes, hashes, splits, modelos y ejecuciones |
| `packages/sonora/` | Lógica reutilizable; adaptar a la estructura real |
| `scripts/` y `pipelines/` | Entradas CLI; sin lógica duplicada |
| `config/` | Parámetros y reglas versionadas |
| `notebooks/` | Cinco evidencias ejecutadas |
| `artifacts/` | Vectores, modelos, escaladores y esquemas |
| `apps/api/` y `apps/web/` | Backend y frontend |
| `reports/` | Calidad del corpus, resultados y reporte académico |
| `runtime/` | Logs, locks y temporales |

## Representaciones y recomendación

Baseline TF-IDF/coseno; embeddings propios (familia por decidir, Word2Vec/SGNS como propuesta),
LDA con conteos para tópicos. Entrenar en train; transformar el corpus completo sin reajuste.
Audio: FFT/STFT y descriptores de ritmo, energía, timbre y armonía sobre clips reales.
Registrar parámetros, unidades, segmentos y escaladores ajustados sólo con train.

Recomendador basado en contenido, de ítem a ítem. La fusión Letras/Audio es multimodal;
no llamarla filtrado colaborativo si no usa interacciones de usuarios.

`score = alpha * lyrics_similarity + (1 - alpha) * audio_similarity`

El slider es alpha, peso de letras. Comparar/calibrar escalas con validation; compartir
intervalo [0,1] no asegura calibración. LDA y embeddings deben mostrarse por separado en la
comparación y decidir mediante validación si los tópicos participan en ranking o explicación.
Sin una modalidad requerida, devolver no disponible; no inventar cero ni sustituir con mock.
Para demo pequeña, ranking exacto por consulta. Para corpus grande, búsqueda dispersa o índice
vectorial y evaluación del compromiso calidad/recursos. No crear similitudes densas N×N.

## Web y evaluación

Preservar sepia rojizo, naranja/terracota, viejo oeste; Smokum en títulos, Rubik Distressed
muy poco y Ovo en texto. Banners según hora local: día [06:00,18:00), noche el resto.
Dashboard de dos canciones con audio/letras, scores, tópicos, descriptores y peso.

Evaluación exploratoria con personas, ablaciones y comparación contra baseline; métricas de
ranking, cobertura, diversidad, recursos y latencia. La similitud no demuestra gusto o “vibra”.
Las cinco evidencias académicas completas y la justificación en Datos Masivos están detalladas
en REQUISITOS_SONORA.md. Los ejemplos/figuras pueden seleccionar casos; las estadísticas y
anotaciones deben representar el corpus limpio completo, sin limitarlo a la demo.
