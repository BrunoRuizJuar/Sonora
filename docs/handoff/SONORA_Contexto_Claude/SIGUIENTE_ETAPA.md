# Siguiente etapa: corpus completo y vinculación demo

## Objetivo de esta sesión de implementación

Dejar ingesta/limpieza/splits reproducibles y la correspondencia de la demo, sin entrenar aún
Word2Vec/LDA ni implementar toda la web. No eliminar ni modificar los diez Parquet originales.

## Orden de ejecución

1. Inventariar repo, cambios locales, Python/venv, RAM/disco y archivos. Leer requisitos v1.2. (hecho)
2. Inspeccionar schema y metadatos Parquet sin cargar el corpus completo. Registrar tamaños,
   row counts, campos, tipos y algunos ejemplos breves sin volcar miles de letras en logs. (hecho)
3. Definir mapeo explícito de columnas reales, identidad por fuente y esquema de salidas.
   Si hay un campo fiable de idioma, documentar su significado; si falta, detectar idioma con
   una herramienta identificada/versionada, confianza y tratamiento de textos ambiguos/cortos. (hecho)
4. Ingerir por batches y shards con memoria acotada, contador de fila GLOBAL por shard,
   escrituras atómicas, manifiesto de progreso y reanudación sin duplicar registros. (hecho)
5. Preservar original; limpiar HTML/artefactos verificables, normalizar Unicode y saltos,
   conservar estructura de versos/estrofas y una vista de análisis independiente. No eliminar
   puntuación/negación de la vista sintáctica. Documentar estribillos y marcadores de sección. (hecho)
6. Emitir razón por cada exclusión y estado por cada registro. Los casos de idioma incierto
   quedan identificados para revisión. No imponer un máximo de letras ni filtrar por match FMA. (hecho)
7. Deduplicar con hash del texto normalizado sin colapsar versiones distintas sin evidencia.
   Mantener la correspondencia de TODOS los registros de origen con la letra canónica. (hecho)
8. Leer `medium_prioritarios.json`, verificar localizadores contra filas reales y enlazar
   las 886 grabaciones a letras canónicas. Una fila Genius puede mapear varias pistas FMA.
   Conservar registros rechazados por calidad/idioma con motivo; no desaparecerlos del informe. (hecho)
9. Fusionar grupos relacionados antes de crear split reproducible (70/20/10, semilla inicial42),
   sin letras iguales entre particiones. Propagar la partición del grupo a la demo. Los porcentajes
   son objetivos aproximados por grupos; informar reparto real por letras y grabaciones. (hecho)
10. Escribir reporte de calidad y comandos exactos, con logs y límites de ejecución claros. (hecho)

## Salidas esperadas (nombres orientativos; el contrato importa)

| Salida | Campos / significado mínimo |
|---|---|
| Corpus Parquet particionado por shard/run | lyrics_id, source_file, source_row_zero_based, título/artista de origen, texto original/estructural/limpio, idioma y procedencia del idioma, hash, estado |
| Correspondencias origen→letra | Clave de fuente, lyrics_id canónico y motivo de consolidación |
| Registro de exclusiones | Clave de fuente, estado, regla y motivo |
| Vínculos demo | fma_track_id, localizador Genius, lyrics_id, retenido para prueba, validaciones letra/audio, grupo, capacidades y motivos |
| Manifiesto de splits | lyrics_id, group_id, train/test/validation, semilla, reglas y porcentajes reales |
| Manifiesto de ejecución | Inputs/hashes, configuración/hash, código, versiones, tiempos, recursos, checkpoints y salidas completas/incompletas |
| Reporte | Total de origen, aceptadas, excluidas por motivo, incertidumbre, idioma, duplicados, longitudes y cobertura demo |

Procesar y conservar trazabilidad de todos los registros no significa guardar el mismo texto
muchas veces: tablas canónicas más correspondencias son válidas. Guardar texto original y
anotaciones pesadas en archivos locales fuera de Git. El localizador no debe depender del tamaño
del batch. “Reanudar” debe comprobar configuración/input compatibles y evitar duplicación.

## Verificaciones relevantes

- Totales reconciliados: registros aceptados/excluidos/pendientes explican el universo leído. (hecho)
- Mismo resultado por fuente al cambiar batch size; localizadores globales correctos. (hecho)
- Interrupción/reanudación no duplica ni declara completos shards a medio escribir. (hecho)
- Texto original preservado; ejemplos con contracciones, Unicode y saltos mantienen trazabilidad. (hecho)
- Las 886 candidatas exactas son consideradas una vez cada una, sin excluir por repetición. (hecho)
- Un duplicado de letra puede enlazar varias grabaciones; cada grupo aparece en un solo split. (hecho)
- Sólo aceptar una ejecución real como completa tras procesar todas las entradas esperadas. (hecho)

## Después de esta etapa

E1 exploración completa (hecho; re-ejecutar con anotación al 100 %) → E2 frecuencias/n-gramas/Zipf → E3 POS/lemas → E4 dependencias
y complejidad → E5 TF-IDF/embeddings/LDA/espacio semántico. Reutilizar anotaciones y evitar
recalcular cada notebook. Fourier y descriptores de Medium pueden avanzar en otra etapa
offline, usando los mismos IDs/grupos. Por último ranking, API, dashboard y evaluación.

Las corridas pequeñas son smoke tests, no el cumplimiento de PLN sobre todo el corpus.
Si no hay recursos suficientes, medir throughput y guardar progreso; informar la limitación
y proponer configuración de ejecución, sin sustituir silenciosamente el corpus por una muestra.

---

## Registro de avance (añadido 2026-11-14; no sustituye lo anterior)

- Etapa corpus + demo: (hecho) `lyrics_full_v1`, reconciliada y marcada completa.
  Evidencia: `docs/CORPUS_LETRAS.md` §11, `reports/corpus/lyrics_full_v1/quality_report.md`.
- Audio FMA Medium extraído y verificado por sha1 (hecho); 886/886 demo con archivo.
  Decodificación y descriptores: pendientes (prioridad del usuario: PLN primero).
- Léxico del corpus completo (hecho), estadísticas por letra (hecho), anotación spaCy completa
  de 3 155 772 letras (hecho), conteo de uni/bi/trigramas por split (hecho).
- E1 (hecho, ejecutado). E2–E5: pendientes. Estado detallado y prompt de continuación:
  `docs/handoff/ESTADO_2026-11-14.md`.

## Actualizaci?n de cierre ? 2026-11-15

- E1 y E2: (hecho), notebooks ejecutados. E2 incluye KenLM de ?rdenes 2/3/4;
  elegido orden 4 por validation (PPL 82,34), test reservado.
- E3?E5 siguen pendientes. No se inici? E3; siguiente etapa autorizable tras el cierre E2.
- Detalle vigente: `docs/handoff/ESTADO_2026-11-14.md`, secci?n ?Cierre E2?.
