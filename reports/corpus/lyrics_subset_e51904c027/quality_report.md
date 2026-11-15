# Reporte de calidad del corpus de letras — `lyrics_subset_e51904c027`

Generado: 2026-11-13T05:43:10+00:00 (UTC). Universo: **SUBCONJUNTO de prueba: {'shards': ['train-00007-of-00010'], 'row_limit_per_shard': 40000} — NO es el corpus completo**.
Todos los conteos proceden de la ejecución indicada sobre los Parquet Genius locales; no son fixtures de prueba.

## Reconciliación

Registros de origen leídos: 40,000; esperados en el alcance: 40,000. Reconciliado: **True**.

| Estado | Registros |
|---|---:|
| accepted | 39,969 |
| review | 29 |
| excluded | 2 |

## Exclusiones y revisión por regla

| Regla | Registros |
|---|---:|
| language_uncertain | 29 |
| non_english | 1 |
| placeholder_text | 1 |

## Idioma (lingua, vista de análisis sin marcadores de sección)

| Estado de idioma | Registros |
|---|---:|
| en | 39,969 |
| uncertain | 29 |
| non_en | 1 |
| None | 1 |

| Motivo | Registros |
|---|---:|
| primary_en_high_conf | 39,671 |
| both_detectors_en | 298 |
| primary_not_en_secondary_en | 19 |
| primary_en_secondary_not_en | 6 |
| detectors_disagree_non_en | 4 |
| both_detectors_ja | 1 |
| None | 1 |

| Confianza inglés | Registros |
|---|---:|
| [0.00,0.05) | 15 |
| [0.05,0.20) | 10 |
| [0.20,0.50) | 40 |
| [0.50,0.80) | 90 |
| [0.80,0.90) | 62 |
| [0.90,0.95) | 48 |
| [0.95,0.99) | 59 |
| [0.99,1.00) | 39,675 |

| Idioma más probable | Registros |
|---|---:|
| en | 39,975 |
| tl | 5 |
| st | 3 |
| nb | 2 |
| ms | 2 |
| zu | 2 |
| tn | 1 |
| fr | 1 |
| fi | 1 |
| af | 1 |
| zh | 1 |
| da | 1 |
| sv | 1 |
| ja | 1 |
| nl | 1 |
| la | 1 |
| None | 1 |

## Duplicados y corpus canónico

| Clave | Cantidad |
|---|---:|
| Registros aceptados | 39,969 |
| Letras canónicas (lyrics_id) | 39,965 |
| Registros aceptados consolidados como duplicado | 4 |
| Letras canónicas con más de un registro | 4 |
| No aceptados cuyo texto coincide con una letra aceptada | 0 |
| Palabras totales (vista de análisis, canónicas) | 10,813,598 |
| Canónicas con marcadores de sección | 15,534 |

## Longitudes (letras canónicas)

| Medida | p0 | p1 | p5 | p25 | p50 | p75 | p95 | p99 | p100 | mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| n_words | 11 | 35 | 71 | 149 | 231 | 356 | 590 | 793 | 3,241 | 271 |
| n_chars_original | 101 | 185 | 371 | 764 | 1,177 | 1,809 | 3,014 | 4,068 | 15,572 | 1,381 |
| n_lines | 1 | 1 | 9 | 23 | 35 | 52 | 85 | 118 | 465 | 40 |
| n_stanzas | 1 | 1 | 1 | 3 | 5 | 7 | 13 | 27 | 184 | 6 |

## Grupos comparables (DAT-03)

| tag | Letras |
|---|---:|
| pop | 16,920 |
| rap | 14,054 |
| rock | 6,373 |
| rb | 1,870 |
| country | 748 |

| Década | Letras |
|---|---:|
| 1900 | 1 |
| 1920 | 24 |
| 1930 | 10 |
| 1940 | 7 |
| 1950 | 63 |
| 1960 | 339 |
| 1970 | 405 |
| 1980 | 610 |
| 1990 | 2,316 |
| 2000 | 5,117 |
| 2010 | 21,721 |
| 2020 | 9,319 |

Años < 1900 (dato de origen dudoso): 33.

## Banderas de calidad

| Bandera | Registros |
|---|---:|
| short_text_language | 32 |
| contains_url | 31 |
| missing_title | 3 |
| replacement_char | 3 |
| html_entity_unescaped | 1 |

## Marcadores de sección más frecuentes

| Etiqueta | Apariciones |
|---|---:|
| verse | 28,263 |
| chorus | 21,735 |
| hook | 6,417 |
| intro | 4,205 |
| bridge | 4,059 |
| outro | 4,038 |
| pre-chorus | 3,400 |
| ? | 806 |
| refrain | 732 |
| post-chorus | 708 |
| instrumental | 669 |
| interlude | 495 |
| pre | 319 |
| drop | 280 |
|  | 224 |
| guitar | 171 |
| part | 134 |
| spoken | 133 |
| pre-hook | 133 |
| break | 118 |
| chrous | 103 |
| solo | 100 |
| sample | 86 |
| breakdown | 76 |
| post | 70 |
| produced | 68 |
| repeat | 62 |
| lil | 53 |
| skit | 46 |
| pre-drop | 46 |

## Split por grupos

Semilla 42; objetivo {'train': 0.7, 'test': 0.2, 'validation': 0.1}; 39,965 letras en 39,964 grupos.

| Partición | Letras | Grupos | Registros de origen | Fracción real (letras) |
|---|---:|---:|---:|---:|
| train | 28,133 | 28,132 | 28,135 | 0.70394 |
| test | 7,903 | 7,903 | 7,903 | 0.19775 |
| validation | 3,929 | 3,929 | 3,931 | 0.09831 |

## Cobertura de la demo (FMA Medium, 886 exactas retenidas)

| Clave | Cantidad |
|---|---:|
| selection_rows | 886 |
| distinct_genius_locators | 850 |
| in_processed_scope | 9 |
| locator_verified | 9 |
| has_lyrics | 9 |
| distinct_lyrics_ids | 9 |
| recordings_per_lyrics_id_max | 1 |
| has_audio_file | 0 |
| catalog_eligible | 0 |

Estado de letras: {"None": 877, "accepted": 9}

Reglas de exclusión: {}

Grabaciones por split: {"None": 877, "train": 4, "test": 3, "validation": 2}

Carpetas de audio FMA encontradas: ninguna.
`catalog_eligible` permanece en falso hasta validar letra/audio y licencia de reproducción.

## Auditoría de idioma

Muestra reproducible (semilla 42): {'accepted': 200, 'uncertain': 29, 'non_english': 1} en `data/processed/lyrics/lyrics_subset_e51904c027/language_audit_sample.parquet`. Revisión humana pendiente: no se reporta exactitud del detector.
