# SONORA · Condensed procedure

SONORA investiga qué similitudes entre canciones recuperan las representaciones de letras en inglés y cómo cambia el ranking al incorporar características del sonido. La aplicación parte de una canción semilla y la especificación contempla tres modos, Letras, Música y Mixto. El producto actual integra búsqueda, recomendación textual, reproductor FMA y captura de valoraciones. La extracción acústica y la afinidad emocional tienen pilotos propios.

Para redactar el informe, usar el [manuscrito](reports/articulo_nlp/ARTICULO_COMPLETO.md), el [mapa de evidencias](reports/articulo_nlp/00_MAPA_EVIDENCIAS.md), el [registro de resultados](reports/articulo_nlp/00_REGISTRO_RESULTADOS.md) y las [referencias verificadas](reports/articulo_nlp/13_REFERENCIAS.md). Para decidir el alcance de entrega, consultar los [requisitos](docs/REQUIREMENTS.md).

## 1. Corpus, identidad y particiones

1. Ingerir los diez Parquet de Genius. Conservar los localizadores de origen y una vista fiel de la letra para visualización. Crear vistas de análisis que preserven versos y estrofas y permitan limpiar marcadores y normalizar variantes para cada tarea. Registrar exclusiones e idiomas inciertos.
2. Consolidar duplicados exactos en `lyrics_id` canónicos y agrupar versiones relacionadas para asignarlas juntas. Mantener distinta la identidad de la grabación FMA. El vínculo entre letra y grabación se registra aparte con su procedencia.
3. Usar 70 % train, 20 % test y 10 % validation como objetivo por grupos. Ajustar vocabularios, modelos y transformaciones con train, elegir configuraciones con validation y reservar test para la evaluación final. Los conteos descriptivos pueden abarcar el corpus completo si se indica el universo.

| Resultado | Valor |
| --- | --- |
| Registros de origen / aceptados automáticamente | 3 179 588 / 3 177 443 |
| Idioma incierto / no inglés / marcador / menos de cinco palabras | 1 914 / 155 / 75 / 1 |
| Duplicados exactos consolidados / letras canónicas | 21 671 / 3 155 772 |
| Grupos / grupos en más de un split | 3 145 790 / 0 registrados |
| Train / test / validation | 2 208 832 / 631 651 / 315 289 letras |
| Medianas por letra | 242 palabras, 37 versos y 6 estrofas |
| Palabras en la vista de análisis / tokens del léxico regex / tokens spaCy | 902 376 173 / 902 376 353 / 1 033 733 693 |

Los tres conteos de texto corresponden a representaciones distintas. La diferencia de 180 entre los dos primeros se reconcilió en 56 letras tras el paso a minúsculas. Los tags y años de Genius sirven para contrastes descriptivos. El desbalance por tag, los años dudosos y los cambios de composición por década limitan las conclusiones. La auditoría humana del idioma sigue pendiente. [Método, esquema, comandos y costes](docs/CORPUS_LETRAS.md) · [Informe de calidad](reports/corpus/lyrics_full_v1/quality_report.md) · [Manifiesto de split](manifests/splits/lyrics_full_v1.json)

## 2. Evidencias de PLN

| Evidencia | Procedimiento | Resultado e interpretación |
| --- | --- | --- |
| [E1 · Corpus](notebooks/evidencias/E1_construccion_exploracion.ipynb) | Medir longitud, repetición, estructura y cobertura por tag/década. Comparar segmentación spaCy por defecto y con frontera de verso en una muestra dirigida de 400 letras. | Medianas de palabras por tag: rap 408, rb 284, country 215, pop 204 y rock 187. La segmentación por defecto cruzó versos en 3 018 de 4 746 segmentos. La regla de verso dio 16 955 segmentos y cero cruces, con el coste de partir construcciones que continúan en el siguiente verso. |
| [E2 · Estadística léxica](notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb) | Contar uni-, bi- y trigramas con frontera de verso. Comparar políticas de filtrado, difusión, repetición, Zipf/Mandelbrot y log-odds por tag. Entrenar modelos KenLM por orden sobre train. | 1 277 145 tipos de unigramas, 25 877 889 bigramas y 105 251 805 trigramas. Se seleccionaron 424 vocablos de 731 candidatos. Perplejidad en validation por orden 2/3/4: 153,53 / 97,45 / 82,34. Se eligió el orden 4. |
| [E3 · Morfosintaxis](notebooks/evidencias/E3_morfosintaxis.ipynb) | Anotar POS y lemas con spaCy 3.8.18 y `en_core_web_sm` 3.8.0 sin NER. Usar fronteras de verso y texto sombra de igual longitud para formas como `runnin'` cuando su variante `-ing` tiene soporte, conservando el token original. | 3 155 772 letras y 1 033 733 693 tokens spaCy. Los agregados de POS y lemas cubren el corpus. Los ejemplos de errores y fragmentación requieren revisión contextual. [Revisión E3](docs/E3_REVISION.md) |
| [E4 · Dependencias](notebooks/evidencias/E4_sintaxis_dependencias.ipynb) | Reutilizar spaCy. Medir longitud sin puntuación, profundidad desde raíz 0 y distancia sin arcos de raíz ni puntuación. Contrastar tags, décadas y bandas de longitud. Inspeccionar cuatro árboles dirigidos. | 144 457 653 segmentos y 809 010 838 arcos incluidos. Medias globales de longitud 6,5976, profundidad 2,4413 y distancia por arco 1,9360. El orden de profundidad entre country y rap cambia al acotar a segmentos de 5–9 tokens. La auditoría estructural de 5 000 letras y 244 951 segmentos revisa integridad de grafos. [Revisión E4](docs/E4_REVISION.md) |
| [E5 · Semántica](notebooks/evidencias/E5_semantica.ipynb) | Ajustar TF-IDF, Word2Vec/SGNS propio y LDA sobre train. Comparar vecinos textuales, proyectar embeddings con PCA e inspeccionar contextos y tópicos. | Se publicaron embeddings de 128 dimensiones y distribuciones de 20 tópicos para los 3 155 772 IDs. La cobertura del vocabulario sobre tokens es de aproximadamente 81,9 % en cada split. [Método](docs/E5_METODO.md) · [Resultados](docs/E5_RESULTADOS.md) |

E1 y E2 están cerradas. E3–E5 tienen resultados ejecutados y revisión personal pendiente. Las métricas del parser describen sus salidas y la perplejidad mide predicción de texto. Para medir relevancia de recomendaciones se necesitan juicios humanos. [Pendientes de revisión](TODO-human.md)

### Lectura y decisiones de E5

- **SGNS.** Entrenar sobre tokens superficiales con 128 dimensiones, cinco negativos, semilla 42 y tres épocas. La ventana 5 obtuvo un objetivo medio de −2,392892 frente a −2,401978 de la ventana 10 sobre 100 000 pares positivos de validation. Representar cada letra con pooling ponderado por TF-IDF sublineal sobre términos distintos y normalización L2.
- **Recuperación.** Comparar top-10 por coseno SGNS y TF-IDF en cinco consultas de validation contra 2 208 832 letras de train. El solapamiento observado fue 1/10 en una consulta y 0/10 en cuatro. Los casos ilustran afinidades parciales y pérdidas de tema específico, por ejemplo, el embarazo en *Eat For Two MTV Unplugged*. Para adjudicar calidad entre estrategias hacen falta valoraciones independientes.
- **PCA y contextos.** En 2 000 letras de validation elegidas por hash, PC1 explica 23,323 % y PC2 9,852 %. Hay solapamiento amplio entre tags. Los análisis de `love`, `home`, `money`, `war` y `freedom` comparan contextos de ±5 palabras dentro de un espacio estático. Los contrastes requieren al menos diez letras y veinte ocurrencias por grupo. Algunas décadas y tags quedan con soporte insuficiente.
- **LDA.** Se eligieron 20 tópicos por cota variacional en validation, −9,310046 frente a −10,691584 con 40 tópicos para la misma semilla. Tres tópicos dominados por palabras funcionales concentran 94,925 % de la masa media de train. El Jaccard medio de términos top-10 entre semillas fue 0,364228. El ranking activo prescinde de LDA y cualquier incorporación requiere una ablación.

[Resultados, parámetros, casos y limitaciones de E5](docs/E5_RESULTADOS.md) · [CLI de recuperación](docs/E5_RECOMMENDATIONS.md) · [Auditoría reproducible](scripts/verify_e5_results.py)

## 3. Audio, enlaces y evaluación

| Bloque | Método, resultado y estado |
| --- | --- |
| FMA Medium | 25 000 clips, verificados por checksum en la corrida documentada. El cruce por título y artista normalizados retuvo 886 grabaciones, 850 localizadores Genius y 849 IDs de letra canónica. El manifiesto local revisado marca las 886 como candidatas y cero como elegibles para el catálogo combinado. La elegibilidad requiere revisar correspondencia, decodificación y condiciones de reproducción. [Corpus y vínculos](docs/CORPUS_LETRAS.md#7-demo-fma-medium-dat-07-dat-08-dat-12) · [Verificación FMA](manifests/sources/fma_medium_checksums_verification.json) |
| Piloto acústico | Decodificar a mono a 22 050 Hz y aplicar STFT con ventana de 2 048 y salto de 512 muestras. Extraer descriptores de ritmo, energía, timbre y armonía, incluidos BPM cuando hay estimación, MFCC y croma. La corrida local `runtime/audio-pilot/resultados.json` contiene 15 pistas de train, 15 de validation, 435 pares y cero errores de extracción. Las muestras de escucha sirven para revisar vecinos y contrastes. [Piloto acústico](scripts/pilot_audio.py) · [Piloto de armonía](scripts/pilot_harmony.py) |
| Portal y API | Búsqueda por título/artista, letras originales cuando está disponible el índice, rankings SGNS y TF-IDF, reproductor FMA y valoraciones. SQLite FTS5 sirve búsqueda, y las matrices por shard permiten calcular top-k sin matriz de pares completa. El ranking relacionado de FMA emplea género y artista. Las rutas de Música acústica y Mixto real siguen pendientes. [API textual](docs/API_TEXTO_WEB.md) · [Implementación del portal](apps/api/src/sonora_api/main.py) · [Ranking FMA](apps/api/src/sonora_api/fma_audio.py) |
| Piloto emocional | 200 letras, 12 consultas y 224 pares en la unión de rankings. Probar SGNS frente a pesos emocionales 0,1/0,2/0,3 con el léxico NRC. Anotar tema y afinidad emocional por separado en escala 0–5 con pasos de media estrella. Elegir peso con cuatro consultas de ajuste del piloto y comparar en ocho reservadas. El piloto se prepara a partir del split test del corpus y mantiene su división interna. Conservar los resultados como piloto al diseñar la evaluación final. [Protocolo y comandos](docs/PILOTO_EMOCIONAL.md) · [Archivo de anotación](data/evaluation/emotion-pilot/anotacion.json) |
| Evaluación final | Congelar catálogo, modelo, pesos y protocolo antes de juzgar test. Recoger relevancia humana separada por modo, registrar desacuerdo y pares sin juzgar, y comparar baselines y ablaciones. Reportar calidad de ranking, cobertura y latencia/recursos con denominadores y condiciones de ejecución. Las métricas finales de Letras/Música/Mixto quedan por medir. [Protocolo de evaluación](docs/REQUIREMENTS.md#11-evaluación-empírica) |

Las valoraciones del portal se guardan por par, catálogo y navegador en SQLite, en `runtime/feedback/ratings.sqlite3` por defecto. La web registra tema, emoción y vibra musical. La interfaz de anotación también permite exportar juicios a JSON. [Persistencia](apps/api/src/sonora_api/ratings.py) · [Guía del piloto](docs/PILOTO_EMOCIONAL.md)

## 4. Figuras y capturas para reutilizar

| Uso | Archivos en Git |
| --- | --- |
| Construcción del corpus y estructura de letras | [Longitud por tag, ECDF](reports/figures/E1/e1_longitud_por_tag.png) · [Histograma de longitud](reports/figures/E1/e1_longitud_letras.png) · [Letras por década](reports/figures/E1/e1_letras_por_decada.png) · [Repetición de versos](reports/figures/E1/e1_repeticion_por_tag.png) |
| Frecuencias y modelos de lenguaje | [Zipf/Mandelbrot](reports/figures/E2/e2_zipf.png) · [Espectro](reports/figures/E2/e2_espectro.png) · [Difusión y repetición](reports/figures/E2/e2_difusion_repeticion.png) · [Políticas de filtrado](reports/figures/E2/e2_top_palabras_politicas.png) · [Log-odds por tag](reports/figures/E2/e2_logodds_tags.png) · [Perplejidad por orden/tag](reports/figures/E2/e2_perplejidad_tags.png) |
| Morfosintaxis | [POS global](reports/figures/E3/pos_global.png) · [POS por tag](reports/figures/E3/pos_tags.png) · [POS por década](reports/figures/E3/pos_decadas.png) |
| Sintaxis | [Distribuciones](reports/figures/E4/distribuciones.png) · [Por tag](reports/figures/E4/comparacion_tags.png) · [Por década](reports/figures/E4/comparacion_decadas.png) · [Árbol transitivo](reports/figures/E4/arbol_transitive.png) · [Subordinada](reports/figures/E4/arbol_subordinate.png) · [Coordinación](reports/figures/E4/arbol_coordination.png) · [Fragmento](reports/figures/E4/arbol_fragment.png) |
| Embeddings | [PCA de validation](reports/figures/E5/pca_validation.png) |
| Identidad visual | [Marca](apps/web/public/assets/brand/) · [Ilustraciones](apps/web/public/assets/illustrations/) · [Portadas de muestra](apps/web/public/assets/covers/) |

El [inventario de figuras](reports/articulo_nlp/00_INVENTARIO_FIGURAS.md) enlaza celdas de origen, ejes, universos y límites. Para un informe, revisar la imagen y escribir un pie con población, partición o muestra, unidades y parámetros. En la segunda entrega del artículo se usó la ECDF de longitud por tag. Los recursos visuales de la app sirven para ilustrar el producto.

Para capturas de interfaz, arrancar la API y usar el [verificador web](scripts/verify_text_web.py) siguiendo la [guía de reproducción](docs/API_TEXTO_WEB.md#verificación-reproducible), o capturar el portal actual en `/`, el reproductor en `/reproductor.html` y anotación en `/anotacion.html`. Las capturas históricas `runtime/text_web_1440.png` y `runtime/text_web_390.png` son salidas locales. Para documentar el piloto acústico se pueden abrir las páginas locales generadas por los scripts del piloto y capturar el caso de escucha que se está comentando.

## 5. Reproducción y cierre

Desde la raíz del repositorio, la demo ligera se abre con `py -3 apps/web/serve.py --open`. Para consultar el catálogo real hay que preparar el entorno, restaurar o construir `artifacts/releases/lyrics-serving-v1/` y preparar el índice `lyrics-original-v1` si se quiere mostrar la letra. Arrancar con `./scripts/Start-SONORA-Web.ps1` y abrir `http://127.0.0.1:8010/`. El audio depende de los archivos locales de FMA. [Entorno Windows](docs/WINDOWS.md) · [Transferencia de artefactos](docs/handoff/MIGRACION_2026-11-16.md) · [API y arranque](docs/API_TEXTO_WEB.md)

Para reproducir resultados, seguir primero la [ingesta y preparación](docs/CORPUS_LETRAS.md#9-comandos), después los pipelines y [generadores de notebooks](notebooks/evidencias/), y finalmente la [construcción y verificación de servicio](docs/API_TEXTO_WEB.md). Reutilizar los shards y checkpoints completos con sus manifiestos. En el equipo documentado, con 15,7 GB de RAM, conviene ejecutar un proceso pesado a la vez. La corrida de ingesta reportó 52 min y 0,5 GB de RSS pico, y la consolidación optimizada 30 min y 3,3 GB de RSS pico. La suite del portal en `ec3fab0` pasó 55 pruebas, con un aviso de dependencia. Las pruebas de software y la evaluación humana responden preguntas distintas.

**Siguiente hito funcional.** Formar un subconjunto FMA–Genius verificado con al menos una semilla y candidatos suficientes para probar los tres modos. Integrar descriptores acústicos, mezcla de scores normalizados, controles de peso y diversidad, y una comparación de dos canciones con audio, letras y desglose de similitud. Verificar el flujo desde una copia limpia con artefactos documentados, y medir el ranking con juicios reservados. [Aceptación funcional](docs/REQUIREMENTS.md#132-cierre-funcional-de-sonora)

**Entrega académica.** Completar revisión personal E3–E5, auditoría humana de idioma, aclaración del requisito de 150–300 páginas y redacción final con sus resultados y límites. Los notebooks, las figuras, el registro de resultados y sus manifiestos permiten rastrear cada afirmación hasta su evidencia. [Pendientes humanos](TODO-human.md) · [Estado del artículo](reports/articulo_nlp/00_ESTADO_ARTICULO.md)
