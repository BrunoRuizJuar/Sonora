# 13. Referencias verificadas de esta entrega

Sistema único de citas numéricas [n], conservado en las secciones y en el integrado. Las entradas internas son evidencia de implementación, no publicaciones revisadas por pares. Fecha de consulta externa: 16 de noviembre de 2026, hora local. No se atribuye autoría institucional al artículo.

[1] SONORA. *Especificación de requisitos académicos, funcionales y técnicos*, v1.2, 12 de noviembre de 2026. Documento interno: [docs/REQUIREMENTS.md](../../docs/REQUIREMENTS.md), §§2–5, 13 y 15.

[2] SONORA. *Corpus completo de letras en inglés y vínculos de la demo*. Documento técnico interno: [docs/CORPUS_LETRAS.md](../../docs/CORPUS_LETRAS.md), §§1–7, 11–13.

[3] SONORA. *E5 — protocolo de representaciones semánticas*, 16 de noviembre de 2026. Protocolo interno: [docs/E5_METODO.md](../../docs/E5_METODO.md). Describe TF-IDF, SGNS y LDA de la implementación; las publicaciones metodológicas originales se incorporarán verificadas en la sección 03.

[4] SONORA. *Quality report: lyrics_full_v1*, generado el 14 de noviembre de 2026 UTC. Artefacto de resultados: [quality_report.json](../corpus/lyrics_full_v1/quality_report.json). Localizadores por clave en 00_REGISTRO_RESULTADOS.md.

[5] SONORA. *Manifiesto de particiones lyrics_full_v1*. Artefacto reproducible: [manifests/splits/lyrics_full_v1.json](../../manifests/splits/lyrics_full_v1.json), seed, group_rules, by_split y actual_fraction_lyrics.

[6] SONORA. *Recuperación textual ítem a ítem*. Código interno: [lyrics.py](../../packages/sonora/src/sonora/recommendation/lyrics.py), función recommend_lyrics; [main.py](../../apps/api/src/sonora_api/main.py), estado de API; [ranking.yaml](../../config/ranking.yaml), hipótesis de combinación. El código se cita como implementación, no como prueba empírica de calidad.

[7] theelderemo. *genius-lyrics-cleaned*. Dataset en Hugging Face, sin fecha de publicación comprobada. [Tarjeta oficial](https://huggingface.co/datasets/theelderemo/genius-lyrics-cleaned). Verificados identificador y esquema público. Revisión de la copia local no registrada. No se asume que una licencia declarada por el depositante resuelva derechos sobre cada letra. DOI visible en tarjeta no se incorpora como identificador verificado del snapshot local.

[8] Responsables del repositorio mdeff/fma. *FMA: A Dataset For Music Analysis*. [Repositorio oficial de datos y documentación](https://github.com/mdeff/fma). Documentación de variantes y clips; no se atribuye un año bibliográfico al repositorio consultado. La publicación metodológica FMA y sus autores se verificarán antes de añadirla a antecedentes.

[9] SONORA. *Manifiestos de la entrada Genius y de la corrida completa*. [genius_snapshot.json](../../manifests/sources/genius_snapshot.json) y [lyrics_full_v1.json](../../manifests/runs/lyrics_full_v1.json). Hashes y procedencia de la copia local.

[10] SONORA. *Configuración y preparación lingüística*. [lyrics_corpus.yaml](../../config/lyrics_corpus.yaml); [lyrics_text.py](../../packages/sonora/src/sonora/preprocessing/lyrics_text.py), build_views/dedup_key/language_excerpt; [language.py](../../packages/sonora/src/sonora/nlp/language.py), needs_secondary/decide. Fuentes de software local.

[11] SONORA. *Revisión lingüística y cierre de E4*, 16 de noviembre de 2026. [E4_REVISION.md](../../docs/E4_REVISION.md), ejemplo lyr_9b869033ae33f65fdae4, sent_i=56, line_i=61; revisión del autor pendiente.

[12] SONORA. *Exportación del espacio E5 e5-surface-v2*. [complete.json](../../data/processed/nlp/lyrics_full_v1/semantics/e5-surface-v2/representations/complete.json), counts y space_id; [trained.json](../../artifacts/models/lyrics_full_v1/e5-surface-v2/trained.json), modelos seleccionados y test_consumed. Artefactos locales, fuera de Git; disponibilidad no garantizada en otra copia.

[13] SONORA. *Evidencia 1 — Construcción y exploración del corpus de letras*. [Notebook ejecutado](../../notebooks/evidencias/E1_construccion_exploracion.ipynb), celdas base cero 15, 19–25 y 28. [Manifiesto NLP](../../manifests/nlp/lyrics_full_v1.json), lexicon y annotations; [lexicon.py](../../packages/sonora/src/sonora/nlp/lexicon.py), count_file. Las salidas son evidencia guardada con las reservas registradas en los controles.

Pendientes bibliográficos: publicaciones primarias de TF-IDF/recuperación, SGNS, LDA, spaCy, KenLM, Zipf y antecedentes específicos de recuperación musical. No se incluyen referencias no comprobadas ni citas secundarias como si se hubieran leído los originales.
