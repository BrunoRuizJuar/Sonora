# Reporte de calidad del corpus de letras — `lyrics_full_v1`

Generado: 2026-11-14T03:54:12+00:00 (UTC). Universo: **corpus completo (10 shards, todas las filas)**.
Todos los conteos proceden de la ejecución indicada sobre los Parquet Genius locales; no son fixtures de prueba.

## Reconciliación

Registros de origen leídos: 3,179,588; esperados en el alcance: 3,179,588. Reconciliado: **True**.

| Estado | Registros |
|---|---:|
| accepted | 3,177,443 |
| review | 1,914 |
| excluded | 231 |

## Exclusiones y revisión por regla

| Regla | Registros |
|---|---:|
| language_uncertain | 1,914 |
| non_english | 155 |
| placeholder_text | 75 |
| too_few_words | 1 |

## Idioma (lingua, vista de análisis sin marcadores de sección)

| Estado de idioma | Registros |
|---|---:|
| en | 3,177,443 |
| uncertain | 1,914 |
| non_en | 155 |
| None | 76 |

| Motivo | Registros |
|---|---:|
| primary_en_high_conf | 3,158,471 |
| both_detectors_en | 18,972 |
| primary_not_en_secondary_en | 1,447 |
| primary_en_secondary_not_en | 289 |
| detectors_disagree_non_en | 178 |
| both_detectors_ja | 80 |
| None | 76 |
| both_detectors_zh | 56 |
| both_detectors_tl | 5 |
| both_detectors_xh | 4 |
| both_detectors_zu | 3 |
| both_detectors_sn | 3 |
| both_detectors_la | 2 |
| both_detectors_ga | 1 |
| both_detectors_sv | 1 |

| Confianza inglés | Registros |
|---|---:|
| [0.00,0.05) | 1,231 |
| [0.05,0.20) | 574 |
| [0.20,0.50) | 2,169 |
| [0.50,0.80) | 5,532 |
| [0.80,0.90) | 4,201 |
| [0.90,0.95) | 3,358 |
| [0.95,0.99) | 3,901 |
| [0.99,1.00) | 3,158,546 |

| Idioma más probable | Registros |
|---|---:|
| en | 3,177,732 |
| tl | 337 |
| la | 187 |
| de | 141 |
| zh | 111 |
| da | 104 |
| yo | 95 |
| ja | 90 |
| None | 76 |
| nb | 74 |
| zu | 55 |
| es | 53 |
| sv | 51 |
| st | 47 |
| fr | 43 |
| mi | 31 |
| nl | 28 |
| xh | 27 |
| fi | 27 |
| cy | 26 |

## Duplicados y corpus canónico

| Clave | Cantidad |
|---|---:|
| Registros aceptados | 3,177,443 |
| Letras canónicas (lyrics_id) | 3,155,772 |
| Registros aceptados consolidados como duplicado | 21,671 |
| Letras canónicas con más de un registro | 19,703 |
| No aceptados cuyo texto coincide con una letra aceptada | 0 |
| Palabras totales (vista de análisis, canónicas) | 902,376,173 |
| Canónicas con marcadores de sección | 1,466,578 |

## Longitudes (letras canónicas)

| Medida | p0 | p1 | p5 | p25 | p50 | p75 | p95 | p99 | p100 | mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| n_words | 9 | 38 | 77 | 159 | 242 | 368 | 629 | 850 | 18,186 | 286 |
| n_chars_original | 101 | 198 | 401 | 816 | 1,238 | 1,877 | 3,222 | 4,395 | 92,032 | 1,464 |
| n_lines | 1 | 4 | 11 | 25 | 37 | 53 | 86 | 119 | 3,110 | 42 |
| n_stanzas | 1 | 1 | 1 | 4 | 6 | 8 | 12 | 23 | 1,295 | 6 |

## Grupos comparables (DAT-03)

| tag | Letras |
|---|---:|
| pop | 1,336,051 |
| rap | 959,763 |
| rock | 621,148 |
| rb | 153,552 |
| country | 85,258 |

| Década | Letras |
|---|---:|
| 1900 | 100 |
| 1910 | 182 |
| 1920 | 1,361 |
| 1930 | 1,096 |
| 1940 | 1,200 |
| 1950 | 9,014 |
| 1960 | 39,341 |
| 1970 | 62,259 |
| 1980 | 93,673 |
| 1990 | 213,283 |
| 2000 | 435,534 |
| 2010 | 1,582,505 |
| 2020 | 714,549 |
| 2050 | 1 |
| 2100 | 1 |

Años < 1900 (dato de origen dudoso): 1,673.

## Banderas de calidad

| Bandera | Registros |
|---|---:|
| contains_url | 1,768 |
| short_text_language | 1,528 |
| very_long | 492 |
| replacement_char | 128 |
| escaped_quote_fixed | 125 |
| missing_title | 117 |
| html_entity_unescaped | 31 |
| embed_suffix_removed | 2 |

## Marcadores de sección más frecuentes

| Etiqueta | Apariciones |
|---|---:|
| verse | 2,851,517 |
| chorus | 2,357,951 |
| hook | 562,598 |
| bridge | 441,847 |
| pre-chorus | 439,009 |
| outro | 436,011 |
| intro | 406,946 |
| post-chorus | 110,414 |
| refrain | 84,127 |
| instrumental | 64,157 |
| ? | 63,215 |
| interlude | 53,026 |
| drop | 27,081 |
| guitar | 18,914 |
|  | 18,409 |
| pre | 17,693 |
| pre-hook | 17,509 |
| spoken | 14,255 |
| break | 13,725 |
| part | 10,477 |
| breakdown | 9,890 |
| solo | 8,824 |
| repeat | 8,348 |
| produced | 7,419 |
| all | 6,960 |
| sample | 6,917 |
| chrous | 6,660 |
| round | 6,118 |
| post | 4,965 |
| the | 4,665 |

## Split por grupos

Semilla 42; objetivo {'train': 0.7, 'test': 0.2, 'validation': 0.1}; 3,155,772 letras en 3,145,790 grupos.

| Partición | Letras | Grupos | Registros de origen | Fracción real (letras) |
|---|---:|---:|---:|---:|
| train | 2,208,832 | 2,201,895 | 2,223,978 | 0.69993 |
| test | 631,651 | 629,609 | 635,945 | 0.20016 |
| validation | 315,289 | 314,286 | 317,520 | 0.09991 |

## Cobertura de la demo (FMA Medium, 886 exactas retenidas)

| Clave | Cantidad |
|---|---:|
| selection_rows | 886 |
| distinct_genius_locators | 850 |
| in_processed_scope | 886 |
| locator_verified | 886 |
| has_lyrics | 886 |
| distinct_lyrics_ids | 849 |
| recordings_per_lyrics_id_max | 3 |
| has_audio_file | 886 |
| catalog_eligible | 0 |

Estado de letras: {"accepted": 886}

Reglas de exclusión: {}

Grabaciones por split: {"train": 575, "validation": 101, "test": 210}

Carpetas de audio FMA encontradas: ['data/raw/fma/fma_medium'].
`catalog_eligible` permanece en falso hasta validar letra/audio y licencia de reproducción.

## Auditoría de idioma

Muestra reproducible (semilla 42): {'accepted': 200, 'uncertain': 200, 'non_english': 100} en `data/processed/lyrics/lyrics_full_v1/language_audit_sample.parquet`. Revisión humana pendiente: no se reporta exactitud del detector.
