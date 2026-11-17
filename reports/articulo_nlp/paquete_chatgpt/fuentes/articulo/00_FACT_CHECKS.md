# Fact checks de los hallazgos publicados

Revisión de todos los 19 registros iniciales y de sus interpretaciones. La revalidación propia no toma como confirmación independiente que la otra sesión repita el mismo reporte. Resultado computable: [revalidacion_independiente.json](revalidacion_independiente.json). Procedimiento de lectura: [revalidar_hallazgos.py](revalidar_hallazgos.py). Crítica cruzada: [revision_cruzada_sonora.json](revision_cruzada_sonora.json).

| Hallazgo | Veredicto | Evidencia y límite | Cita notebook o fuente correcta |
|---|---|---|---|
| R01 | Corroborado desde salidas procesadas; entrada original no disponible | 3 177 443 registros representados + 2145 exclusiones/revisión = 3 179 588; data/raw/genius sin Parquet | [13, E1, celdas 3, 6](../../notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R02 | Revalidado desde metadatos | Suma n_source_records de canónicas = 3 177 443 | [13, E1, celdas 6, 14](../../notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R03 | Revalidado desde metadatos e IDs | Diez shards: 3 155 772 filas; cobertura exacta una vez en split | [13, E1, celdas 14, 22](../../notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R04 | Revalidado; denominador aclarado | 3 177 443 aceptados menos 3 155 772 canónicas = 21 671; denominador de duplicación: aceptados | [13, E1, celda 14](../../notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R05 | Revalidado desde exclusions.parquet | 1914 review; 155 no inglés, 75 placeholders y 1 texto corto | [13, E1, celdas 6, 11](../../notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R06 | Reconciliado con casos; pendiente anterior resuelto | 56 letras; diferencia +180. Control U+0130 antes de lower recupera conteo previo en cada caso | No figura la explicación de U+0130 en el notebook; fuente primaria del hallazgo nuevo: [18] |
| R07 | Revalidado desde count y doc_stats | 902 376 353 tokens; 1 277 145 filas/tipos del léxico | [13, E1, celda 22](../../notebooks/evidencias/E1_construccion_exploracion.ipynb); [14, E2, celda 3](../../notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb) |
| R08 | Revalidado directamente en el Parquet | 3 145 790 grupos, máximo 24 letras; 0 multisbplit; 2 208 832/631 651/315 289 letras y 2 201 895/629 609/314 286 grupos; SHA coincide. No descarta duplicados no detectados | [13, E1, celda 25](../../notebooks/evidencias/E1_construccion_exploracion.ipynb); asignación por grupos en manifiesto/código, no demostrada por esa celda sola |
| R09 | Acotado a resultado histórico; actualidad no verificable | 886 grabaciones, 850 localizadores y 849 letras en quality_report.demo; tablas/audio ausentes en rutas previstas | Sin celda E1–E5 que revalide demo; citar [4], claves demo, y [18] |
| R10 | Revalidado desde metadatos canónicos | Cinco conteos coinciden; tag del primer canónico no representa todas las etiquetas originales | [13, E1, celda 25](../../notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R11 | Revalidado desde columnas numéricas | Medianas 242 palabras, 37 versos, 6 estrofas; marginales, no una canción típica íntegra | [13, E1, celdas 20, 23](../../notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R12 | Corroborado en output; no reanotado | Tabla 4746/3018 vs 16955/0 en muestra 400. No se repite spaCy; no mide precisión | [13, E1, celda 19](../../notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R13 | Revalidado desde year | 1673 anteriores a 1900, 392 posteriores a 2022; no reconstruye fechas reales | [13, E1, celda 24](../../notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R14 | Corroborado entre reportes y notebook | Suma POS = 1 033 733 693; docs coincide con corpus. Anotaciones individuales no releídas; ejemplos de 3 letras | [15, E3, celdas 1, 3, 9](../../notebooks/evidencias/E3_morfosintaxis.ipynb) |
| R15 | Corroborado entre artefactos; no reparseado | Tokens E4 coinciden con E3; global_metrics guardadas, sin recalcular todos los arcos | [16, E4, celdas 1, 5, 7, 9](../../notebooks/evidencias/E4_sintaxis_dependencias.ipynb) |
| R16 | Corroborado entre manifiestos y notebook | counts y space_id iguales a auditoría E5; no se releen todos los vectores/modelos | [17, E5, celdas 1, 3](../../notebooks/evidencias/E5_semantica.ipynb) |
| R17 | Muestra y pertenencia revalidadas; alcance completo pendiente | 2000 IDs distintos, todos validation; PCA/contextos no son corpus completo | [17, E5, celdas 5, 7](../../notebooks/evidencias/E5_semantica.ipynb) |
| R18 | Auditoría previa corroborada documentalmente | Valores de norma/cobertura guardados coinciden con notebook. No se repite validación de vectores | [17, E5, celda 1](../../notebooks/evidencias/E5_semantica.ipynb) |
| R19 | Revalidado desde doc_stats por tag | 204/408/187/284/215 palabras; sin significancia inferida | [13, E1, celdas 25, 28](../../notebooks/evidencias/E1_construccion_exploracion.ipynb) |

## Objeciones metodológicas y resolución

| Formulación cuestionada | Resolución y fuente |
|---|---|
| Todo preprocesamiento se fijó en train | Se rechaza. KenLM/E5 ajustan con train; spaCy es preentrenado y el guard de g-dropping usa léxico completo (annotate_corpus.py y E1 c15/c17). E5 words excluye esa transformación. |
| Un grupo equivale a un artista/título único | Se rechaza. _group_roots usa todas las filas aceptadas; conexiones transitivas. |
| Duplicado exacto demuestra cover | Se rechaza. Hash sólo demuestra igualdad bajo su normalización, sin identificar la causa. |
| El corpus aceptado es enteramente monolingüe | Se rechaza. lang_status=en en todas las canónicas es una decisión automática; el pasaje incierto E4 c7 limita esa lectura. |
| 886 localizadores fueron comprobados | Se corrige: 886 vínculos sobre 850 localizadores distintos; aceptación de letras procede de demo.lyrics_status. |
| Existen 886 audios en este equipo | Se retira como afirmación actual. Lo registra un reporte histórico; faltan rutas previstas y originales. |
| E5 técnico cerrado satisface todo alcance contextual | Se mantiene brecha: modelos/exportación completos, contextos sólo muestra 2000. |
| La diferencia de 180 implica 180 caracteres o error de idioma | Se rechaza. Es diferencia de tokens por interacción lower/regex en 56 letras; no identifica idioma ni recomienda limpieza. |
| Cero grupos solapados demuestra cero contaminación | Se rechaza. Sólo acredita separación de IDs/grupos registrados; no detecta covers modificados ni casi duplicados omitidos. |
| Una imagen copiada procede necesariamente del output binario | Se distingue: Figura 1 copiada del PNG externo, generado por E1 c28; igualdad comprobada con PNG externo, no con el render incrustado. |
| Que todos los tests pasen demuestra calidad lingüística | Se rechaza. Fixtures comprueban software; falta referencia humana para precisión y juicios para relevancia. |

La relectura de reportes/modelos no valida todos los hallazgos lingüísticos de E1–E5. Las secciones aún no redactadas tendrán su propia auditoría antes de incluir cifras o interpretaciones. No se declara una validación humana ni un cierre global del artículo.
