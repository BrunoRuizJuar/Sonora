# Corpus completo de letras en inglés y vínculos de la demo

Implementa la etapa de `docs/handoff/SONORA_Contexto_Claude/SIGUIENTE_ETAPA.md` según
`docs/REQUIREMENTS.md` v1.2 (DAT-01…DAT-13, SPL-01…SPL-05, BD-05). No entrena modelos.

- Código: `packages/sonora/src/sonora/` (`ingestion/genius.py`, `ingestion/lyrics_corpus.py`,
  `preprocessing/lyrics_text.py`, `nlp/language.py`, `matching/normalize.py`, `storage/runs.py`).
- CLI: `pipelines/ingestion/prepare_lyrics_corpus.py`.
- Configuración versionada: `config/lyrics_corpus.yaml`.
- Pruebas: `tests/unit/`, `tests/integration/` (datos **sintéticos**; nunca el corpus real).

## 1. Esquema real de entrada (inspeccionado el 2026-11-12)

| Elemento | Valor |
|---|---|
| Archivos | `data/raw/genius/train-0000{0..9}-of-00010.parquet`, 2,4 GB |
| Filas | 317 959 × 8 + 317 958 × 2 = **3 179 588** (coincide con el cruce FMA–Genius) |
| Row groups | 318 por archivo (~1 000 filas) |
| Columnas | `title: string`, `artist: string`, `tag: string`, `year: int64`, `lyrics: string` |
| Metadatos | Sólo `huggingface` (features); sin revisión del dataset |
| Idioma | **No hay columna**: se detecta (sección 4) |
| ID único | **No hay**: identidad de fuente = `archivo#row=<fila global base 0>` |
| `tag` | `pop`, `rap`, `rock`, `rb`, `country` (no aparece `misc` en las muestras) |
| `year` | Entero; hay valores < 1900 (p. ej. 1): se informan como dudosos, no se corrigen |
| `lyrics` | Longitud mínima observada 101 caracteres (el dataset ya filtró por longitud); marcadores `[Verse 1]`, `[Chorus]`, `[?]`, créditos `[Produced by …]`, nombres de personajes; espacios Unicode (U+2005, U+00A0), comillas tipográficas y `\'` escapadas |

El localizador `genius_locator` del cruce (`train-0000X-of-00010.parquet#row=N`) usa el mismo
formato y la misma numeración global, independiente del tamaño de batch o row group.

## 2. Identidades y salidas

| Identidad | Definición |
|---|---|
| `source_key` | `<archivo>#row=<fila global>`; un registro de origen |
| `text_hash` | sha256 de la clave de deduplicación (vista de análisis, casefold, espacios colapsados) |
| `lyrics_id` | `lyr_` + 20 hex de `text_hash`; estable entre ejecuciones; se verifica que no colisione |
| `group_id` | `grp_` + menor `lyrics_id` del componente de letras relacionadas |
| `fma_track_id` | Grabación FMA; varias pueden apuntar a una misma `lyrics_id` |

Salidas de una ejecución `<run_id>` (todo bajo `data/` queda fuera de Git):

| Ruta | Contenido |
|---|---|
| `data/interim/lyrics/<run_id>/records/<shard>/part-NNNNN.parquet` | Un registro por fila de origen: metadatos, conteos, hashes, idioma (2 detectores), banderas, `status`, `exclusion_rule`, `exclusion_reason`. Sin texto. |
| `data/interim/lyrics/<run_id>/run_config.json` | Configuración + hash + tamaño/mtime/filas de entradas para validar la reanudación |
| `data/processed/lyrics/<run_id>/corpus/<shard>.parquet` | Corpus canónico: una fila por `lyrics_id` con `lyrics_original`, `lyrics_structural`, `lyrics_analysis`, idioma y conteos |
| `data/processed/lyrics/<run_id>/source_to_lyrics.parquet` | TODOS los registros de origen → `lyrics_id` canónico, `is_canonical`, `consolidation_reason`, `matches_accepted_lyrics_id` |
| `data/processed/lyrics/<run_id>/exclusions.parquet` | Registros excluidos o en revisión con regla, motivo y puntuaciones de idioma |
| `data/processed/lyrics/<run_id>/language_audit_sample.parquet` | Muestra reproducible para auditoría humana de idioma (con extractos) |
| `data/processed/splits/<run_id>/lyrics_splits.parquet` | `lyrics_id`, `group_id`, `split`, tamaño del grupo, registros de origen |
| `data/processed/demo/<run_id>/demo_links.parquet` / `.csv` | Las 886 grabaciones con verificación de localizador, `lyrics_id`, grupo, split, capacidades y motivos |
| `manifests/runs/<run_id>.json` | Entradas (tamaño, mtime, filas, sha256), configuración y hash, huella del código, versiones, tiempos, RSS, etapas y salidas |
| `manifests/splits/<run_id>.json` | Reglas, semilla, porcentajes objetivo/reales por letras y grupos, tamaños de grupo, sha256 del Parquet |
| `manifests/sources/genius_snapshot.json` | sha256 de cada Parquet Genius |
| `reports/corpus/<run_id>/quality_report.{md,json}` | Reporte de calidad (sólo conteos, sin letras) |
| `runtime/logs/<run_id>.log` | Log de la ejecución |

Los manifiestos y reportes no contienen letras y pueden versionarse.

## 3. Vistas de texto (DAT-04) — `lyrics-views-v1`

1. **Original**: cadena exacta del Parquet; nunca se modifica (las pruebas lo verifican byte a byte).
2. **Estructural**: NFC; `\r\n`→`\n`; entidades HTML y etiquetas `<br>`/`<i>`… sólo si aparecen;
   `\'`/`\"` escapadas → comillas; sufijo `NNEmbed` y línea `You might also like` (artefactos de
   scraping de Genius); espacios Unicode → espacio; caracteres de ancho cero eliminados;
   comillas/apóstrofos tipográficos → ASCII (`don’t` → `don't`); espacios repetidos colapsados;
   varias líneas vacías → un único salto de estrofa. Conserva marcadores de sección, mayúsculas,
   puntuación, contracciones y negaciones.
3. **Análisis**: estructural sin anotaciones editoriales entre corchetes (encabezados `[Chorus]`,
   `[?]`, `[Produced by …]`); un encabezado se convierte en límite de estrofa. Conserva líneas,
   estrofas, mayúsculas, puntuación, contracciones y negaciones para POS/lemas/dependencias.
   La conversión a minúsculas y la tokenización se hacen en las prácticas, no aquí.

**Estribillos**: no se expanden (`[Chorus x2]` no se duplica) ni se eliminan repeticiones escritas.
Las etiquetas de sección se guardan en `section_labels` para comparar secciones (DAT-03).
`U+FFFD` no se puede reparar: se marca `replacement_char`.

## 4. Idioma (DAT-02)

Entrada: extracto de la vista de análisis (inicio/medio/final, 3 × 800 caracteres) para no
juzgar sólo la introducción y sin encabezados en inglés.

- Primario: `lingua-language-detector` 2.2.0, todos los idiomas, modo de alta precisión.
- Secundario: `py3langid` 0.4.0 (modelo langid.py, probabilidades normalizadas), sólo cuando el
  primario no es concluyente.

Calibración sobre filas reales (shard 7, 106 000 filas, 2026-11-12): lingua dio confianza 1,0
a `de`/`tl`/`la` sobre inglés evidente y confianzas 0,25–0,8 en letras cortas en inglés. Reglas:

| Caso | Decisión |
|---|---|
| lingua = en con confianza ≥ 0,99 y ≥ 20 palabras | `en` (`primary_en_high_conf`) |
| ambos = en (secundario ≥ 0,5) | `en` (`both_detectors_en`) |
| ambos = mismo idioma ≠ en y ≥ 20 palabras | `non_en`, excluido (`both_detectors_<lang>`) |
| desacuerdo, texto corto no inglés o indetectable | `uncertain` → estado `review` |

Los `review` no entran en el corpus aceptado, quedan identificados en `exclusions.parquet` con
ambas puntuaciones y se muestrean en `language_audit_sample.parquet`. La exactitud del detector
no se reporta hasta completar la auditoría humana.

## 5. Calidad y exclusiones

| Regla | Estado | Condición |
|---|---|---|
| `empty_lyrics` | excluded | nulo o sólo espacios |
| `too_few_words` | excluded | < 5 palabras en la vista de análisis (p. ej. sólo `[Instrumental]`) |
| `placeholder_text` | excluded | ≤ 30 palabras y patrón de marcador (“lyrics … not available”, “instrumental”) |
| `non_english` | excluded | ver sección 4 |
| `language_uncertain` | review | ver sección 4 |

Banderas sin exclusión: `very_long` (≥ 20 000 caracteres), `short_text_language`,
`replacement_char`, `contains_url`, `missing_title`, `missing_artist` y las de limpieza aplicada.
No hay máximo de letras ni filtro por coincidencia con FMA.

## 6. Deduplicación, grupos y split (SPL-01, SPL-02)

- Duplicado exacto = mismo `text_hash`. Canónica = primer registro en orden (shard, fila).
  Todos los registros conservan su correspondencia; no se guarda el mismo texto varias veces.
- Grupos (unión-búsqueda): (a) mismo `text_hash`; (b) mismo artista normalizado y mismo
  título base (sin sufijos de versión como `(Live)`, `- Remix`, `[Acoustic Version]`), tomando
  título/artista de **todos** los registros aceptados de cada letra.
- Split por grupo: `sha256("42:<group_id>")` → uniforme [0,1) → train < 0,70 ≤ test < 0,90 ≤ validation.
  Ningún grupo aparece en dos particiones; los porcentajes reales se publican en el manifiesto.
- Limitación: no se detectan casi-duplicados ni covers con letra modificada de otro artista.

## 7. Demo FMA Medium (DAT-07, DAT-08, DAT-12)

`medium_prioritarios.json` (886 filas, 850 localizadores). Cada fila se considera una vez:
se comprueba que el localizador apunta a una fila cuyo título y artista normalizados
(`nfkc-casefold-punctuation-spaces-v1`, idéntica al script del cruce) coinciden con FMA;
se toma `lyrics_id`, grupo y split de la letra; las repetidas comparten letra y split.
Capacidades: `has_lyrics` (localizador verificado y letra aceptada), `has_text_vector=false`,
`has_audio_features=false`, `has_audio_file` (existe `<dir>/<id[:3]>/<id>.mp3`),
`playback_allowed=null` (licencia no verificada). `catalog_eligible` es falso hasta validar letra,
audio y licencia; `lyrics_validated`/`audio_validated` siguen nulos (revisión humana).

## 8. Reanudación y garantías (BD-05)

- Partes de 20 000 filas alineadas a filas globales; el batch de lectura (`--batch-size`) no
  forma parte del hash ni cambia resultados (probado con 7 y 500).
- Cada parte se escribe en `.tmp` y se renombra; lleva en sus metadatos el hash de configuración
  y su rango. Una parte se da por completa sólo si hash, rango y número de filas coinciden.
- Reanudar = repetir el comando con el mismo `--run-id`. Si la configuración, las versiones de
  los detectores o los archivos de entrada cambiaron, la ejecución se niega a mezclar resultados.
- `runtime/locks/<run_id>.lock` impide dos escritores sobre la misma ejecución.
- Las etapas posteriores se niegan a correr si falta alguna parte de la ingesta.
- Una ejecución sólo se marca `complete_full_corpus_run: true` si su alcance son los diez
  shards completos, todas las etapas terminaron y los totales se reconcilian.

## 9. Comandos

Windows (PowerShell, desde `B:\University\2027-1\SONORA`):

```powershell
.\.venv\Scripts\python.exe -m pip install pyarrow pyyaml lingua-language-detector py3langid psutil numpy pytest
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe pipelines\ingestion\prepare_lyrics_corpus.py inspect
# corrida completa (reanudable: repetir el mismo comando)
.\.venv\Scripts\python.exe pipelines\ingestion\prepare_lyrics_corpus.py all --run-id lyrics_full_v1
# estado de las etapas
.\.venv\Scripts\python.exe pipelines\ingestion\prepare_lyrics_corpus.py status --run-id lyrics_full_v1
# smoke test (subconjunto, nunca se marca como corpus completo)
.\.venv\Scripts\python.exe pipelines\ingestion\prepare_lyrics_corpus.py all --shards train-00007-of-00010 --row-limit 40000
```

Etapas sueltas: `ingest`, `consolidate`, `split`, `demo`, `report`. `--max-chunks N` detiene la
ingesta tras N partes (útil para repartir la carga en varias sesiones).

WSL: el venv de Windows no sirve dentro de Linux. Comprobar la ruta montada real
(`wslpath 'B:\University\2027-1\SONORA'`; si B: no está montada,
`sudo mkdir -p /mnt/b && sudo mount -t drvfs B: /mnt/b`), crear un venv propio fuera del
repo o en `.venv-wsl/` y ejecutar los mismos subcomandos con `python3`. No ejecutar a la vez
la misma `--run-id` desde Windows y WSL: el lock lo impide, pero conviene un único escritor.

## 10. Recursos medidos

Equipo: i7-13650HX (20 hilos), 15,7 GB RAM, Python 3.14.7 (venv existente), pyarrow 26.0.1.
Throughput de ingesta en datos reales: ~1 500 filas/s (shard 7) y ~450 filas/s en las primeras
filas del shard 0 (letras más largas); la detección de idioma domina el tiempo.
Los tiempos y RSS de la corrida completa están en `manifests/runs/<run_id>.json`.

## 11. Resultado de la corrida completa `lyrics_full_v1` (datos reales, 2026-11-12/13)

`complete_full_corpus_run: true`; totales reconciliados. Detalle en
`reports/corpus/lyrics_full_v1/quality_report.md`.

| Medida | Valor |
|---|---:|
| Registros de origen leídos | 3 179 588 |
| Aceptados | 3 177 443 |
| En revisión (idioma incierto) | 1 914 |
| Excluidos: no inglés / marcador / < 5 palabras | 155 / 75 / 1 |
| Letras canónicas (`lyrics_id`) | 3 155 772 |
| Registros aceptados consolidados como duplicado exacto | 21 671 |
| Palabras (vista de análisis, canónicas) | 902 376 173 |
| Detector secundario ejecutado | 21 041 registros |
| Grupos | 3 145 790 (máx. 24 letras por grupo) |
| Split train / test / validation (letras) | 2 208 832 / 631 651 / 315 289 (69,99 % / 20,02 % / 9,99 %) |
| Grupos presentes en más de una partición | 0 |
| Demo: grabaciones / localizadores verificados / con letra aceptada | 886 / 886 / 886 |
| Demo: `lyrics_id` distintos | 849 (dos filas Genius con texto idéntico) |
| Demo por split (grabaciones) | train 575, test 210, validation 101 |
| Demo con archivo de audio local | 886 (actualizado 2026-11-13 tras extraer FMA Medium; ver abajo) |

Tiempo: ingesta 52 min (pico RSS 0,5 GB); consolidación 30 min (pico RSS 3,3 GB tras la
optimización de memoria); split 30 s. Disco: 0,3 GB interim, 5,2 GB corpus procesado.
Una primera consolidación fue detenida por falta de memoria del sistema; se reanudó sin
repetir la ingesta y se comprobó que el código optimizado produce salidas idénticas.

**Audio FMA Medium (2026-11-13).** `data/raw/fma/fma_medium.zip` (23,8 GB, bzip2; el
extractor de Windows no lo admite) se extrajo con 7-Zip:
`& 'C:\Program Files\7-Zip\7z.exe' x data\raw\fma\fma_medium.zip -odata\raw\fma -aos`.
25 000 MP3 (24,8 GB) verificados contra `checksums` con
`scripts/verify_fma_checksums.py data/raw/fma/fma_medium`: 25 000 correctos, 0 faltantes,
0 discrepancias. Tras repetir la etapa `demo`, las 886 grabaciones tienen `has_audio_file=true`.
Siguen con `catalog_eligible=false` por tres motivos explícitos: audio no decodificado/validado,
letra no validada por una persona y licencia de reproducción no verificada.

## 12. Avance de PLN sobre el corpus completo (añadido 2026-11-14)

Todo sobre `lyrics_full_v1` (3 155 772 letras canónicas). Salidas bajo `data/processed/nlp/lyrics_full_v1/` (fuera de Git).

| Artefacto | Estado | Comando | Resultado verificado |
|---|---|---|---|
| Léxico regex (`regex-words-v1`) | (hecho) | `pipelines/nlp/annotate_corpus.py lexicon` | 902 376 353 tokens, 1 277 145 tipos; 5,27 M formas `X-in'` (15 166 raíces) |
| Estadísticas por letra (`doc-stats-v1`) | (hecho) | `pipelines/nlp/corpus_stats.py` | 3 155 772 filas en `doc_stats/` (cambios de limpieza, repetición de versos, TTR) |
| Anotación spaCy (`spacy-lines-gdrop-v1`) | (hecho) | `pipelines/nlp/annotate_corpus.py annotate` | 1 033 733 693 tokens, 144 457 653 oraciones, 5 243 419 g-dropping normalizados; 11 GB en `spacy_sm_v1/{tokens,sentences,docs}` |
| n-gramas 1–3 por split (`ngrams-lines-v1`) | (hecho) | `pipelines/nlp/count_ngrams.py` | 179 404 316 filas; train 631 669 490 / validation 90 048 892 / test 180 657 971 tokens; reconcilia con el léxico |
| E1 notebook | (hecho) | `notebooks/evidencias/build_e1.py` | `notebooks/evidencias/E1_construccion_exploracion.ipynb`, figuras en `reports/figures/E1/` |
| Léxico POS por split (`frequency-v1`) | (hecho) | `pipelines/nlp/e2_frequency.py pos-lexicon` | 1 033 733 693 tokens spaCy; 3 236 971 filas `(split, lower, lemma, upos)` y agregados por tag/década |
| Vocablos (`vocables-v1`, sólo train) | (hecho) | `e2_frequency.py vocable-candidates` / `vocables` | 731 candidatos → 424 vocablos; 1,71 % de los tokens del corpus |
| Unigramas por tag y década | (hecho) | `e2_frequency.py group-unigrams` | 4 128 532 filas; suma por tag = 902 376 353 tokens |
| Resumen de n-gramas (totales, espectro, top-K) | (hecho) | `e2_frequency.py ngram-summary` | tipos 1 277 145 / 25 877 889 / 105 251 805 (órdenes 1–3) |
| Texto y vocabulario del LM (train ≥ 2) | (hecho) | `e2_frequency.py lm-vocab` / `lm-export` | 497 831 tipos; `<oov>` 0,084 % train, 0,187 % validation |
| E2 notebook completo, secciones 1–8 | (hecho 2026-11-15) | `notebooks/evidencias/build_e2.py` | `notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb`, figuras en `reports/figures/E2/`, comparación y hallazgos KenLM ejecutados |
| E2-05 KenLM (órdenes por validation) | (hecho 2026-11-15) | `pipelines/nlp/ngram_lm.py train/eval --order N` | órdenes 2/3/4: PPL 153,53 / 97,45 / 82,34; elegido orden 4; binario local WSL 2,708 GB, fuera de Git; test reservado |

Decisiones de la anotación: spaCy 3.8.18 + `en_core_web_sm` 3.8.0 sin NER; todo salto de verso es
frontera de oración (en una muestra de 400 letras la segmentación por defecto unía versos en el
64 % de sus oraciones); `runnin'` se analiza mediante texto sombra `running` de igual longitud sólo
si la forma `-ing` aparece ≥ 20 veces (el token conserva su forma original); `batch_size=16`
(verificado: 0 diferencias frente a 64 en 221 879 tokens). Métricas por oración: profundidad
(raíz = 0) y distancia media de dependencia sin raíz ni arcos de puntuación.

Lección operativa: con 15,7 GB de RAM no ejecutar dos trabajos pesados a la vez; las corridas
largas conviene lanzarlas en una terminal propia del usuario (Claude Code puede detener procesos
en segundo plano cuando el sistema se queda sin memoria).

## 13. E4 sobre las anotaciones existentes (2026-11-16)

Ejecutada en `B:\SONORA` sobre todo el corpus: 3 155 772 letras, 144 457 653 segmentos,
1 033 733 693 tokens y 809 010 838 arcos incluidos. Reutiliza `spacy_sm_v1/sentences/`
y `doc_stats/`, sin repetir spaCy. Métricas por tag/década y bandas de longitud;
árboles y auditoría dirigida con alcance declarado por separado.

CLI `pipelines/nlp/e4_syntax.py`; generador `notebooks/evidencias/build_e4.py`;
notebook `E4_sintaxis_dependencias.ipynb`. Resultados en
`reports/nlp/lyrics_full_v1/e4_{summary,examples}.json`; siete figuras en `reports/figures/E4/`.
Las convenciones de puntuación e índices se distinguen explícitamente de E3.
Revisión asistida realizada, pendiente lectura personal del autor:
[`E4_REVISION.md`](E4_REVISION.md). Detalle operativo:
[`handoff/E4_2026-11-16.md`](handoff/E4_2026-11-16.md). Suite: 43 aprobadas.
