# Datos y fuentes

> **Nota (2026-11-12):** documento anterior a la especificación v1.2. Donde la contradiga
> prevalece [`REQUIREMENTS.md`](REQUIREMENTS.md): FMA Medium es la fuente de audio de la demo,
> el corpus de PLN son todas las letras válidas en inglés de los diez Parquet Genius y
> AcousticBrainz no es dependencia. La preparación implementada está en
> [`CORPUS_LETRAS.md`](CORPUS_LETRAS.md).

## Fuentes acordadas y pendientes

| Fuente | Papel | Estado del proyecto |
|---|---|---|
| Genius `theelderemo/genius-lyrics-cleaned` | Letras en inglés | Ya trabajada; importar copias existentes antes de volver a descargar |
| MusicBrainz | Identidad y metadatos | Enriquecimiento documentado; auditar vínculos disponibles |
| AcousticBrainz | Descriptores acústicos | Nueva prueba; cobertura y calidad por verificar |
| FMA | Audio para extracción propia | Alternativa explorada; matching con letras pendiente |

Los archivos `corpus_tokenized.parquet` y `corpus_p1_genius_musicbrainz.parquet` se mencionan
en el resumen aportado. No están incluidos en este repositorio. Se ubicarán como entradas
históricas bajo `data/raw/legacy/`, conservando intactos los originales y registrando checksum.
Después se genera una versión canónica. Los conteos de `lyrics` y `lyrics_clean` deben registrarse
por separado; no deben mezclarse estadísticas de versiones distintas.

## Tablas canónicas propuestas

| Tabla | Clave | Campos importantes |
|---|---|---|
| `tracks.parquet` | `track_id` | title, artist_ids, artist_display, language, year, recording_mbid, work_mbid, capacidades |
| `lyrics.parquet` | `lyrics_id` | source_ref, lyrics, lyrics_clean, tokens, n_tokens, text_hash |
| `track_lyrics.parquet` | track_id + lyrics_id | evidencia, estado de vínculo |
| `source_links.parquet` | source + source_record_id + revision | track_id, candidato externo, método, score, estado, auditoría |
| `audio_features.parquet` | track_id + schema_version | feature_values, extraction_origin, calidad y faltantes |
| `splits.parquet` | track_id + split_version | train/validation/test, group_id, seed |
| `vectors.ids.parquet` | row_index | track_id y model_version |

`recording_mbid`, `work_mbid`, año, género y portadas pueden faltar. Se conserva el dato
original y el normalizado. Los arrays de vectores se guardan junto con un índice explícito
de filas: el orden de un DataFrame no constituye un identificador estable.

## Documento operativo de canción: ejemplo de estructura

Ejemplo ficticio; no representa un registro real ni un matching confirmado.

```json
{
  "_id": "track:example-internal-id",
  "track_id": "example-internal-id",
  "title": "Example Song",
  "artist_ids": ["example-artist-id"],
  "artist_display": "Example Artist",
  "language": "en",
  "recording_mbid": null,
  "work_mbid": null,
  "catalog_version": "example-v1",
  "capabilities": {
    "has_lyrics": true,
    "has_text_vector": false,
    "has_audio_features": false,
    "has_audio_file": false,
    "playback_allowed": false,
    "has_cover_art": false
  },
  "cover_status": "unknown"
}
```

## Prueba de cobertura

Seleccionar aproximadamente 500 canciones estratificadas por época y etiquetas disponibles.
Registrar muestra y semilla antes de buscar coincidencias. Medir cuántas tienen un vínculo
de grabación aceptado, cuántas tienen datos acústicos y cuántas pasan calidad. Auditar una
submuestra manual incluyendo resultados positivos, ambiguos y negativos. No definir la
viabilidad sólo con un score del buscador o con el número bruto de respuestas.

## Manifiesto de publicación

Cada release define versión del corpus, fuentes/revisiones, conteos por modo, particiones,
modelos, orden de features, dimensiones, rutas, checksums, índice/alias asociado y configuración.
Se publica de manera coordinada. Conservar el release anterior permite restaurar la versión
activa sin volver a entrenar. Audio, letras, metadatos y assets conservan su procedencia y
condiciones de uso; los permisos de una capa no se transfieren automáticamente a las demás.
