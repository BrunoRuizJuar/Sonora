# Mapa de evidencias y secciones

Autoridad: instrucciones del usuario; CLAUDE.md; docs/REQUIREMENTS.md v1.2. AGENTS.md no existe en la raíz al corte. No se localizó plantilla académica independiente entre los documentos de entrega; se adopta la estructura solicitada, conservando ENT-05 y la matriz §15 de requisitos.

| Requisitos | Fuente concreta verificada | Universo / estado | Sección del artículo |
|---|---|---|---|
| OBJ-01…03; pregunta §2 | docs/REQUIREMENTS.md §§2–3 | Pregunta adoptada, hipótesis sin validar | 02, 10–12 |
| E1-01…05; DAT-01…10 | quality_report.json; manifests/runs y sources; config/lyrics_corpus.yaml; E1 celdas 2–30 | Corpus completo; ejemplos y auditoría de 400 aparte; idioma humano pendiente | 04 |
| SPL-01…05 | manifests/splits/lyrics_full_v1.json, by_split, group_rules; código ingestion/lyrics_corpus.py | 70/20/10 aproximado agrupado; reporte corroborado, no recorrido independiente nuevo | 04, 10 |
| E2-01…05 | E2 celdas 3, 5–17, 19–27; frequency/ngram_summary.json; lm/results.json; manifests/nlp | Descriptivos completos; KenLM train, selección validation; ejemplos manuales | 05, 10 |
| E3-01…04 | e3_summary.json docs/tokens/global_pos/lemma/examples; E3 completo; docs/E3_REVISION.md | Agregados completos; nueve ejemplos de tres letras; lectura del autor pendiente | 06 |
| E4-01…04 | e4_summary.json global_metrics/groups/by_length; e4_examples.json; E4 completo; docs/E4_REVISION.md | Completo agregado; auditoría 5000 letras y cuatro árboles dirigidos | 07 |
| E5-01…03 | docs/E5_METODO.md; docs/E5_RESULTADOS.md; E5_semantica.ipynb; e5_verification.json; trained.json; sgns_selection.json; representations/complete.json; e5_tfidf_retrieval.json; e5_embedding_retrieval.json | Ajuste todo train; transformación todas las letras; búsquedas contra train. Sin juicios de relevancia | 08–10 |
| E5-04…05; DAT-09 | e5_analysis.json scope/sample_ids/projection/concepts | PCA y contextos sólo muestra de hasta 2000 validation; NO sustituye análisis completo; matriz final pendiente | 08, 11 |
| REC; audio, fusión y VAL | recommendation/lyrics.py; config/ranking.yaml; apps/api/src/sonora_api/main.py; TODO-human H09–H10 | Recuperación textual implementada; mezcla 0,8/0,2 declarada initial_hypothesis; API scaffold; sin evaluación humana final | 09–11 |
| Fuentes y citas | config/sources.yaml; manifests/sources; páginas oficiales consultadas | URLs de Genius/FMA verificadas; revisión remota del snapshot Genius ausente | 04, 13 |

Los nombres train-0000x-of-00010 son shards de origen, no particiones experimentales. No mezclar lyrics_subset_e51904c027 ni semantics/e5-surface-v1 con lyrics_full_v1/e5-surface-v2.

Auditoría documental: [auditoria_notebooks.json](auditoria_notebooks.json) conserva cada celda completa y cada output textual; [LECTURA_NOTEBOOKS.md](LECTURA_NOTEBOOKS.md) facilita su consulta. Tener salidas y contadores crecientes no acredita actualidad. Las comparaciones automáticas de cifras son limitadas a las descritas en el registro; las afirmaciones restantes se revisarán por sección.
