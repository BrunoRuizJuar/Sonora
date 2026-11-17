# Estado del artículo — primera entrega incremental

Raíz comprobada: B:\SONORA, Windows/PowerShell. Fecha local: 16 de noviembre de 2026; algunos artefactos llevan 17 de noviembre UTC. Escrituras limitadas a reports/articulo_nlp/. No se ejecutaron notebooks, entrenamientos, anotaciones ni pipelines. La terminal requirió escalación porque fallaba el inicio del aislamiento; la otra sesión se consultó y se canceló la solicitud delegada de escritura al recuperarse el acceso propio.

## Alcance y pregunta

PLN sobre todas las letras canónicas aceptadas como inglesas de los diez Parquet Genius. La demo FMA Medium es un subconjunto independiente en su cobertura. Se conserva la pregunta ya adoptada en docs/REQUIREMENTS.md §2: «¿qué diferencias aparecen en la recuperación de canciones relevantes al representar letras en inglés con TF-IDF, embeddings propios y distribuciones temáticas, y cómo se relacionan esas diferencias con la estructura lingüística del corpus?». No se propone sustituirla. Relevancia sigue por evaluar.

## Avance verificado

- Preparación completa lyrics_full_v1: 3 179 588 registros → 3 155 772 letras; reporte reconciliado y manifiesto completo. E1/E2 con notebooks y salidas; E3 y E4 con agregados completos y revisión asistida; revisión personal pendiente.
- E5 e5-surface-v2 ya dispone de trained.json y representations/complete.json: ajuste propio SGNS/LDA, transformación de todo el corpus y recuperación contra train. runtime/e5_status.json registra complete=true, finalización 2026-11-17T02:07:02+00:00. Esto supera el handoff que aún describía entrenamiento en curso. No se declara cierre de E5 sólo por esa bandera.
- Durante la auditoría la otra sesión añadió E5_semantica.ipynb, docs/E5_RESULTADOS.md y e5_verification.json; se incorporaron a esta entrega y a sus hashes. El reporte registra 3 155 772 IDs únicos, cobertura y normas; su verificación de archivos/modelos no se repitió aquí. El notebook nuevo también se incluyó completo en la auditoría documental.
- e5_analysis.json declara una muestra de 2000 validation para PCA y contextos. [PENDIENTE: completar o localizar el análisis semántico de variación/contextos sobre todo el corpus pertinente; la muestra no satisface por sí sola el alcance completo de E5.] No se recorta el requisito para acomodarlo.
- Recuperación textual por coseno implementada en recommendation/lyrics.py. API principal sigue en scaffold; audio/fusión y evaluación final no acreditados por estos artefactos. Pesos de config/ranking.yaml son hipótesis, no configuración demostrada del recuperador actual.
- Introducción y Corpus redactados; referencias mínimas de datos y fuentes internas registradas; inventarios, trazabilidad y artículo integrado disponibles. Autoría, afiliación y datos institucionales no confirmados.

## Contradicciones y riesgos de interpretación

1. R06 frente a R07: diferencia de 180 tokens RESUELTA mediante metadatos de todos los shards y recálculo de sólo 56 letras discrepantes. La expansión U+0130 al aplicar lower introduce una marca combinante que separa tokens regex; el control por sustitución recupera todos los conteos previos. Ver revalidacion_independiente.json, word_count; no se modificaron textos ni se infiere idioma.
2. E1 celda 22 rotula bytes UTF-8, pero suma n_chars_original. No usar 4 620 787 538 como bytes medidos. [PENDIENTE: reportar tamaño real sólo con medición válida.]
3. E1 celda 31 afirma que las letras multilingües quedan en revisión «por diseño». Los detectores sobre extractos no garantizan eso; E4 conserva un pasaje de idioma incierto en letra aceptada. Se redacta aceptación automática de inglés predominante, sin pureza monolingüe garantizada.
4. E1 celda 31 interpreta duplicación como covers y no scraping. Los hashes no distinguen esas causas; el artículo no adopta la generalización.
5. Handoff original y requisitos conservan pendientes históricos ya ejecutados: E2–E4 y ajuste E5. Se toma el artefacto actual por etapa; no se confunde requisito con resultado.
6. 886 pistas / 850 localizadores / 849 letras son unidades diferentes y resultados históricos del reporte. El equipo actual no contiene demo_links, medium_prioritarios ni audio en las rutas documentadas; data/raw/genius sólo contiene .gitkeep. No se acredita disponibilidad actual de originales ni de demo. catalog_eligible=0 es estado del reporte histórico.
7. El snapshot remoto Genius carece de revisión registrada; hashes identifican la copia local, no reconstruyen por sí solos su descarga original. Etiqueta de licencia en una tarjeta no acredita derechos sobre todas las letras ni reproducción de audio.
8. docs/E5_RESULTADOS.md declara E5-04 completado como descripción, pero e5_analysis.json limita contextos a 2000 letras de validation. Se conserva ese avance sin equipararlo al análisis completo solicitado por el usuario. El cierre local declarado y el cierre de alcance del artículo son distintos; sigue pendiente ampliar o localizar evidencia contextual de cobertura completa.

## Pendientes de cierre

Auditoría humana de idioma (200 aceptados, 200 inciertos, 100 no ingleses), criterio docente de 150–300 páginas, lectura personal E3/E4/E5 y juicios de relevancia permanecen pendientes (TODO-human.md). No se aprueban en nombre del usuario. Faltan validación letra–grabación, decodificación/audio, licencias por pista y evaluación final de recomendación. No hay referencia humana para medir precisión POS/dependencias.

La auditoría inicial registra todos los notebooks localizados con celdas, código, salidas, errores y orden. La actualidad semántica de cada salida no queda certificada por tener contador creciente. Faltan el cotejo fino por sección y la revisión visual de las figuras candidatas distintas de la ECDF incluida. Fuentes de control pueden cambiar porque otra sesión avanza E5: fuentes_auditadas.json fija hashes y hora de lectura; revisar diferencias antes de la siguiente entrega.

## Siguiente acción

Redactar 05_ANALISIS_ESTADISTICO.md a partir de E2 y resultados KenLM existentes; comprobar tramos de Zipf, denominadores y afirmaciones contra sus tablas, sin repetir cálculo pesado. Después abordar E3, E4 y E5 con sus límites. Resumen y conclusiones definitivos se escribirán al estabilizar resultados y argumento. La versión integrada actual es un borrador parcial, no un artículo terminado.



## Segunda entrega: revisión crítica con SONORA

Se utilizó exclusivamente la sesión de apoyo **Document SONORA project** (`01a1e751-d65d-7ce1-bc85-282069bb1d6c`), con cuatro rondas documentadas. Se revisaron individualmente R01–R19 y once objeciones metodológicas. [Fact checks](00_FACT_CHECKS.md) y [registro del intercambio](revision_cruzada_sonora.json). Las respuestas se contrastaron con código y artefactos; repetir un reporte entre sesiones no se contó como revalidación independiente.

La revalidación propia confirmó IDs, grupos, conteos de particiones, ausencia de solapamiento de grupos registrados, exclusiones, tamaños por tag, medianas y años dudosos. La diferencia de 180 tokens quedó explicada en 56 letras. El tiempo y el procedimiento están en revalidacion_independiente.json. No se ejecutaron pipelines, notebooks ni entrenamiento. Se corrigieron la actualidad de demo/audio, la confusión entre 886 comprobaciones y 850 localizadores, la generalización train-only y el alcance de metadatos canónicos.

Las citas inline distinguen E1–E5 y celda base cero. 00_CITAS_NOTEBOOKS.md conserva ordinal, ID y ejecución. Todas las figuras candidatas tienen notebook/celda de generación o visualización; Figura 1 mantiene origen externo y hash. Resumen/conclusiones y secciones siguientes siguen pendientes. El constructor histórico construir_entrega.py se bloqueó para evitar que sobrescriba estas correcciones; esta revisión se aplica con actualizar_revalidacion.py.
