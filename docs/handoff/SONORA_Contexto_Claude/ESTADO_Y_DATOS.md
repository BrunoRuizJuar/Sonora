# Estado de SONORA al 12 de noviembre de 2026

## Ubicaciones

- Raíz del usuario: `B:\University\2027-1\SONORA`.
- Remoto indicado: https://github.com/BrunoRuizJuar/Sonora.git.
- Genius: `data/raw/genius/train-00000-of-00010.parquet` hasta `00009`.
- FMA metadata: bajo `data/raw/fma/`; localizar `tracks.csv` (posible subcarpeta `fma_metadata`).
- Matching original: normalmente `data/interim/matching/run_20261113T021601Z_160845/`.
  Localizar los CSV y summary; no renombrar/destruir una ejecución distinta existente.
- Revisión: extraer `matching/SONORA_Revision_Matching.zip` en `data/interim/matching/`.
  El resultado es `data/interim/matching/SONORA_Revision_Matching/`.
- Audio Medium: inventariar carpeta real bajo `data/raw/fma/`; el archivo MP3 suele usar
  ID FMA de seis dígitos y directorio de sus tres primeros dígitos. Validar la estructura local.

## Qué se comprobó

El usuario ejecutó `scripts/check_fma_genius.py --root .` sobre metadatos FMA y los diez Parquet.
Se auditaron los cuatro archivos de resultados, no los contenidos originales de letras/audio.

| Medición | Cantidad |
|---|---:|
| Filas FMA examinadas | 106 574 |
| Registros Genius leídos | 3 179 588 |
| exact_unique_candidate en todo FMA | 2 098 |
| exact_ambiguous en todo FMA | 238 |
| fuzzy_candidate en todo FMA | 245 |
| fuzzy_ambiguous en todo FMA | 25 |
| Pistas Medium con cualquier candidato | 987 |
| Exactas Medium retenidas | 886 |
| Exactas únicas Medium | 787 |
| Exactas Medium con clave FMA repetida | 99 |
| Filas Genius distintas para esas 886 | 850 |

Small ⊂ Medium ⊂ Large. Los valores `small`/`medium`/`large` de la metadata indican el mínimo
subconjunto: para Medium se selecciona `small` O `medium`, no sólo las filas llamadas medium.
En este cruce las exact_ambiguous proceden de varias grabaciones FMA con la misma clave, con
una fila Genius por clave; por decisión del usuario se conservan para experimentar.

## Archivos de revisión

- `medium_prioritarios.json`: selección completa de 886 exactas, no sólo las 787 únicas.
- `revision_candidatos.json`: todas las sugerencias y flags de auditoría.
- `auditoria.json`: conteos y 22 controles de consistencia satisfactorios sobre los resultados.
- `INFORME.md`: interpretación y límites.
- `audit_matching_results.py`: reproducción de la auditoría desde el ZIP original de resultados.

`genius_row_zero_based` es posición global dentro del shard Parquet, empezando en cero,
no posición dentro de un batch o row group. `genius_file` y ese índice juntos son el localizador.
La tabla seleccionada conserva `genius_locator`, `original_status`, `risk_flags`, estados
de validación nulos, `retained_for_experiment` y `lyrics_source_group` provisional.
Al leer las letras se deberán validar esos localizadores contra título/artista originales.

## Qué falta comprobar

Esquema real y procedencia/revisión exacta de Genius; cantidad limpia y en inglés; letras
vacías/duplicadas; idioma de cada coincidencia; existencia y decodificación de audio Medium;
contenido letra/audio; hardware, tiempo y disco; código y frontend efectivamente presentes
en el checkout. El usuario indica contar con audio para la demo; la disponibilidad concreta
se valida localmente antes de anunciar resultados acústicos.

Los 886 registros son candidatos retenidos; no son 886 vínculos ya escuchados/validados.
No eliminar registros por compartir letra: mantener identidad de grabación y agrupar para split.
