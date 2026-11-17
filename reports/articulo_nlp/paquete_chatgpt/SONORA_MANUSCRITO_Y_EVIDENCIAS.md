# SONORA — Manuscrito y evidencias para conversión a LaTeX/PDF

## Cómo utilizar este documento

Este es el archivo de entrada principal. Contiene TODO el texto del artículo redactado hasta esta entrega, seguido de controles para verificarlo. El manuscrito sigue siendo parcial: se han redactado Introducción, Corpus y referencias; no se han redactado las secciones 03 y 05–12 ni el resumen definitivo. No rellenar esas secciones con información supuesta. Autoría, afiliación y plantilla institucional no confirmadas.

La PARTE I es el contenido que debe convertirse al cuerpo del PDF. La PARTE II contiene material editorial de apoyo: no incorporarlo íntegramente al cuerpo del artículo. Puede usarse para notas de trazabilidad o un anexo técnico claramente separado, si resulta necesario. No convertir actas de revisión entre sesiones en referencias científicas.

Las citas bibliográficas conservan [1]–[18]. Los localizadores E1–E5 y «celda» pertenecen a esa evidencia; la celda empieza en cero e incluye Markdown. No confundirla con In[n]. Mantener nombre del notebook y celda en las citas o en notas al pie. La figura incluida procede del PNG externo generado por E1, celda 28 (ordinal 29, ID 6e450d0a), copiado sin modificación. No afirmar que fue extraída del output incrustado.

Se adjuntan snapshots de los cinco notebooks y archivos de apoyo en fuentes/. Los textos originales completos, MP3 y modelos binarios no forman parte de este paquete. Los enlaces relativos de este documento apuntan a archivos incluidos. En el PDF, las rutas de fuentes locales deben tratarse como localizadores documentales, no como enlaces públicos que el lector pueda abrir sin los adjuntos.

## PARTE I — MANUSCRITO DISPONIBLE


# Estructura lingüística y representaciones textuales para la recuperación de canciones en SONORA

**Título provisional. Borrador parcial — segunda entrega.** Introducción y Corpus revisados críticamente, con citas a notebooks y celdas. No acredita cierre de las cinco evidencias. Autoría y afiliación: [PENDIENTE: incorporar sólo datos confirmados]. [Índice](fuentes/articulo/INDICE.md) · [Fact checks](fuentes/articulo/00_FACT_CHECKS.md). Los índices de celda de las citas empiezan en cero; no son contadores de ejecución.

# 2. Introducción

Las letras de canciones ofrecen una vía para estudiar relaciones entre lenguaje y recuperación musical. Una búsqueda por título o artista localiza una entidad conocida, pero no describe las relaciones textuales que permiten explorar otras canciones. En SONORA, el problema de procesamiento de lenguaje natural (PLN), entendido como el análisis computacional del lenguaje, consiste en caracterizar un corpus de letras en inglés y examinar cómo distintas representaciones de ese contenido sustentan la recuperación de canciones. El resultado tangible previsto es un recomendador basado en contenido: una canción semilla se compara con otras mediante propiedades de sus letras y, en una etapa adicional, de su audio [1].

Este problema exige conectar la representación con las propiedades del material analizado. La frecuencia de una palabra depende tanto de su difusión entre canciones como de su repetición dentro de una letra. Los saltos de verso tampoco equivalen necesariamente a límites de oración. Asimismo, las contracciones y las grafías coloquiales afectan la tokenización, es decir, la división del texto en unidades analizables. El corpus y las anotaciones actuales permiten estudiar estos factores, aunque una anotación automática no constituye una interpretación lingüística validada. Por ello, la investigación integra construcción y exploración del corpus, estadística del lenguaje, análisis morfosintáctico, análisis sintáctico y representación semántica; cada nivel aporta información para interpretar los siguientes [1, 2]. La distinción entre difusión y repetición se examina en [14, E2, celdas 19, 20](fuentes/notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb); los errores ilustrativos de anotación y segmentación, en [15, E3, celda 9](fuentes/notebooks/evidencias/E3_morfosintaxis.ipynb) y [16, E4, celda 7](fuentes/notebooks/evidencias/E4_sintaxis_dependencias.ipynb).

Se conserva la pregunta principal ya adoptada por el proyecto: **¿qué diferencias aparecen en la recuperación de canciones relevantes al representar letras en inglés con TF-IDF, embeddings propios y distribuciones temáticas, y cómo se relacionan esas diferencias con la estructura lingüística del corpus?** [1]. TF-IDF pondera términos según su frecuencia en una letra y su presencia en los documentos de entrenamiento. Los embeddings son vectores aprendidos a partir de contextos de palabras; la implementación actual utiliza Word2Vec con muestreo negativo, SGNS. Las distribuciones temáticas se obtienen mediante LDA, un modelo probabilístico que representa cada documento como mezcla de tópicos y cada tópico como distribución de palabras. Estos métodos cumplen funciones distintas: compartir palabras, aproximar relaciones de contexto y describir temas no son operaciones equivalentes [3]. Su comparación debe distinguir cambios de vecinos recuperados de mejoras de relevancia juzgadas por personas.

El objetivo general es estudiar la relación entre estructura lingüística y recuperación basada en letras con evidencia reproducible. Para ello se documentan las decisiones de selección, limpieza y partición; se caracterizan vocabulario, frecuencias y secuencias de palabras; se examinan categorías gramaticales, lemas y dependencias; y se analizan las representaciones semánticas y sus resultados de recuperación. La evaluación integrada deberá contrastar los métodos con un protocolo de relevancia independiente de los puntajes internos. Las hipótesis de mayor recuperación semántica mediante embeddings o de valor adicional de los tópicos permanecen abiertas; una similitud alta no representa un porcentaje de gusto ni demuestra superioridad [1, 3].

El universo textual comprende **3 155 772 letras canónicas** aceptadas automáticamente como inglesas en la corrida `lyrics_full_v1`, obtenidas de diez Parquet de Genius; no se restringe a las canciones con audio [2, 4]; [13, E1, celdas 6, 14, 22](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb). Los análisis descriptivos pueden utilizar el corpus completo. El ajuste de vocabularios y modelos se separa de esa descripción: entrenamiento utiliza `train`, selección utiliza `validation` y la evaluación final se reserva para `test`. Una transformación de todas las particiones con parámetros ya fijados no equivale a ajustar con todas ellas [3, 5]; [17, E5, celdas 1, 3](fuentes/notebooks/evidencias/E5_semantica.ipynb). Esta separación de ajuste se refiere a los modelos KenLM y E5; la anotación descriptiva con spaCy preentrenado utiliza un criterio de normalización gráfica derivado del léxico completo, como se precisa en §4.6.

Para la demo musical se adoptó FMA Medium. El reporte conservado de `lyrics_full_v1` registra **886 grabaciones** retenidas por coincidencia exacta de título y artista normalizados, vinculadas a **850 localizadores Genius** y **849 letras canónicas** [2, 4]. Son resultados de aquella ejecución: la auditoría actual no encontró la tabla `demo_links.parquet`, la selección original ni la carpeta de audio en las rutas documentadas de este equipo [18]. Esa correspondencia de metadatos no valida por sí sola el contenido de la letra ni la relación auditiva con cada grabación. El recuperador textual actual ordena vectores de letras por similitud coseno ([17, E5, celda 9](fuentes/notebooks/evidencias/E5_semantica.ipynb)); la extracción acústica, la fusión de señales y la integración funcional deben documentarse según sus ejecuciones reales [6]. La combinación futura de letras y audio seguirá siendo recomendación basada en contenido mientras no utilice interacciones reales de usuarios. El objetivo central de este artículo es el estudio de PLN, con la recomendación como aplicación y la modalidad acústica como extensión condicionada a evidencia disponible.

Esta primera versión presenta la introducción y la preparación del corpus. [PENDIENTE: completar la comparación de relevancia entre representaciones y la evaluación final antes de responder definitivamente la pregunta de investigación.] Los resultados técnicos existentes permiten continuar la redacción de los análisis, pero no justifican anticipar una respuesta favorable a las hipótesis.

# 4. Corpus y preparación

## 4.1. Fuentes y unidades de análisis

El corpus textual procesado procede del snapshot de `theelderemo/genius-lyrics-cleaned`, distribuido mediante Hugging Face [7]. El manifiesto y las salidas guardadas documentan que la corrida `lyrics_full_v1` leyó diez archivos Parquet y **3 179 588 registros** ([13, E1, celdas 3, 6](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb)). En este equipo se conserva el corpus procesado; `data/raw/genius/` sólo contiene `.gitkeep`, por lo que no se revalidó la entrada original desde sus Parquet. La suma de registros aceptados representados en el corpus y filas de exclusión reproduce el total declarado [18]. El esquema de entrada documentado contiene `title`, `artist`, `tag`, `year` y `lyrics`; no existe una columna de idioma ni un identificador único, según el esquema de origen guardado en [13, E1, celdas 2, 3](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb). Cada fila se localiza mediante el nombre del archivo y su posición global desde cero. Los nombres de archivo que empiezan por `train-` pertenecen a la distribución de origen y no identifican el conjunto de entrenamiento de SONORA [2, 4].

Una fila de origen, una letra y una grabación son unidades diferentes. Una letra canónica es un texto aceptado conservado una sola vez tras la deduplicación definida en §4.4. Puede corresponder a varias filas de origen y a varias grabaciones. La demo parte de FMA Medium, cuya documentación especifica 25 000 clips de 30 segundos [8]; esa fuente acústica no restringe la selección textual. La identidad de los Parquet de aquella ejecución quedó registrada mediante hashes SHA-256, huellas del contenido de cada archivo. Sin embargo, no se registró la revisión remota de la descarga Genius: los hashes identifican el snapshot local y no resuelven esa omisión de procedencia [4, 9]. La tarjeta pública tampoco sustituye la revisión de condiciones aplicables a cada contenido.

## 4.2. Vistas textuales y limpieza

La preparación conserva tres vistas, versión `lyrics-views-v1` [2, 10]. La original retiene el texto leído. La estructural normaliza Unicode a NFC, homogeneiza saltos de línea, espacios y apóstrofos, y elimina artefactos de formato o extracción cuando coinciden con reglas explícitas, incluidos sufijos `Embed`, una línea de sugerencias y determinadas etiquetas HTML. NFC homogeneiza representaciones Unicode canónicamente equivalentes; no convierte automáticamente todas las grafías tipográficas o caracteres visualmente semejantes en una sola palabra.

La vista de análisis elimina anotaciones editoriales entre corchetes, como encabezados de sección, y utiliza los encabezados de línea como fronteras de estrofa. Conserva mayúsculas, puntuación, contracciones, negación y saltos de verso. No expande instrucciones como `[Chorus x2]` ni elimina los estribillos escritos varias veces. Esta decisión evita reconstruir contenido ausente, pero mantiene el peso de las repeticiones transcritas en las frecuencias posteriores ([13, E1, celda 9](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb); [14, E2, celda 19](fuentes/notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb)). Por ello, frecuencia de uso y número de letras que contienen una palabra se distinguirán en el análisis estadístico.

Se excluyen textos vacíos, textos con menos de cinco palabras en la vista de análisis y ciertos marcadores de ausencia de letra de hasta treinta palabras. La longitud elevada y problemas como caracteres de reemplazo se registran como banderas, sin exclusión automática ([13, E1, celdas 5, 6, 7, 8](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb)). Cada registro conserva estado y motivo; la eliminación del conjunto aceptado no equivale a borrar su trazabilidad [2, 4].

## 4.3. Identificación del idioma y resultados de selección

La identificación del idioma se aplica sobre extractos del inicio, centro y final de la vista de análisis, de hasta 800 caracteres por ventana. Así se reduce la dependencia de la introducción y de encabezados potencialmente ingleses. El detector primario es `lingua-language-detector` 2.2.0, en modo de alta precisión y con todos sus idiomas; `py3langid` 0.4.0 interviene cuando la decisión primaria no es concluyente [2, 10]. Son herramientas existentes, no modelos de idioma entrenados por SONORA ([13, E1, celdas 10, 11](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb)).

La aceptación directa requiere inglés como primera opción, confianza de al menos 0,99 y veinte palabras o más. En los demás casos se requiere acuerdo de ambos detectores en inglés, con confianza secundaria de al menos 0,50. El acuerdo en otro idioma conduce a exclusión cuando el texto tiene al menos veinte palabras; los desacuerdos y otros casos no concluyentes quedan en revisión. Esas confianzas son puntajes de los detectores y no tasas de exactitud empíricas del corpus.

**Tabla 1. Flujo de selección de `lyrics_full_v1`. Las primeras cinco filas usan como universo los 3 179 588 registros de origen; la deduplicación opera sobre los 3 177 443 aceptados [4].** Fuente: [13, E1, celdas 6, 14](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb); revalidación de metadatos procesados y exclusiones [18].

| Etapa o motivo | Cantidad | Unidad |
|---|---:|---|
| Entrada leída | 3 179 588 | registros |
| Aceptados | 3 177 443 | registros |
| Idioma incierto, en revisión | 1 914 | registros |
| Excluidos por idioma no inglés | 155 | registros |
| Excluidos por marcador de ausencia / menos de cinco palabras | 75 / 1 | registros |
| Aceptados consolidados como duplicados exactos | 21 671 | registros |
| Corpus canónico resultante | 3 155 772 | letras |

Los estados aceptado, revisión y exclusión reconcilian la entrada. El conjunto canónico representa letras **aceptadas automáticamente como inglesas**, sin garantía de monolingüismo de cada pasaje. La anotación sintáctica posterior identificó un caso de idioma/contexto incierto dentro de una letra aceptada; no permite estimar su prevalencia [11]; [16, E4, celdas 7, 10](fuentes/notebooks/evidencias/E4_sintaxis_dependencias.ipynb). La auditoría humana prevista contiene 200 aceptados, 200 inciertos y 100 no ingleses, con semilla 42, y permanece pendiente [4]. [PENDIENTE: revisar esa muestra y documentar errores del detector antes de informar una exactitud de idioma.]

## 4.4. Deduplicación, identidad y grupos relacionados

La clave de deduplicación se obtiene de la vista de análisis con `casefold` y espacios consecutivos colapsados; el hash SHA-256 de esa clave identifica el texto. `casefold` realiza una normalización de caja para comparar cadenas. El identificador `lyrics_id` conserva veinte dígitos hexadecimales del hash y el registro canónico es el primero en orden de archivo y fila. La correspondencia con todas las filas de origen se mantiene separada [2, 10]; [13, E1, celdas 13, 14](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb). Los agregados por letra utilizan `tag`, `year`, título y artista del registro canónico seleccionado; conservar las correspondencias de origen no implica incorporar todas sus etiquetas en cada agregado. Los **21 671 registros** consolidados no son necesariamente errores: el hash demuestra igualdad según la regla, pero no distingue por sí solo covers, reediciones y duplicación de extracción.

Antes de particionar se agrupan letras idénticas y letras con igual artista normalizado y título base, eliminando sufijos de versión documentados. Los componentes relacionados contienen **3 145 790 grupos**, con un máximo de **24 letras**, revalidados desde las particiones [18]. La agrupación utiliza los metadatos de todas las filas aceptadas, no únicamente los del primer registro canónico. Las conexiones son transitivas: un componente no tiene necesariamente un único artista o título. Agrupar antes del reparto reduce la presencia de versiones relacionadas en conjuntos distintos [10, código `lyrics_corpus.py`, función `_group_roots`]. La regla no detecta exhaustivamente casi duplicados ni covers con texto modificado y artista diferente, por lo que no demuestra ausencia total de contaminación entre particiones [5].

## 4.5. Particiones y separación entre descripción y ajuste

Se aplica SHA-256 a la cadena `42:<group_id>` y se transforma en un valor normalizado del intervalo [0,1). Los valores inferiores a 0,70 se asignan a entrenamiento; los comprendidos entre 0,70 y 0,90, a prueba; el resto, a validación. El grupo completo hereda una sola asignación. Como se distribuyen grupos de distinto tamaño, las fracciones documentales resultantes se aproximan al objetivo 70/20/10 [5].

**Tabla 2. Reparto producido por grupos. Porcentajes de letras calculados sobre 3 155 772 documentos, redondeados a dos decimales; grupos sobre 3 145 790 componentes [5].** Revalidación directa de letras y grupos por partición [18]; [13, E1, celda 25](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) presenta los conteos documentales por split.

| Partición | Letras | % de letras | Grupos |
|---|---:|---:|---:|
| Entrenamiento (`train`) | 2 208 832 | 69,99 | 2 201 895 |
| Prueba (`test`) | 631 651 | 20,02 | 629 609 |
| Validación (`validation`) | 315 289 | 9,99 | 314 286 |

Los modelos KenLM de E2 y TF-IDF, SGNS y LDA de E5 aprenden vocabularios o parámetros con entrenamiento; validación selecciona configuraciones y prueba se reserva para evaluación final ([14, E2, celdas 24, 25](fuentes/notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb); [17, E5, celdas 1, 3, 11](fuentes/notebooks/evidencias/E5_semantica.ipynb)). Esta separación no implica que todo preprocesamiento se haya fijado exclusivamente en entrenamiento: spaCy es preentrenado y el criterio descriptivo de g-dropping consulta el léxico completo. En cambio, las distribuciones descriptivas del corpus pueden reunir las tres particiones, siempre que no se reutilicen para seleccionar modelos. E5 ya transformó todas las letras con un espacio fijado desde entrenamiento; disponer de vectores de prueba no significa haberlos utilizado para ajuste ni haber efectuado la evaluación final [3, 12]. El procedimiento de asignación mantiene los grupos juntos. La revalidación directa del Parquet encontró **3 155 772 `lyrics_id` únicos** y **cero grupos registrados presentes en más de una partición**; su SHA-256 coincide con el manifiesto. También se comprobó que cada ID del corpus aparece una vez en la tabla de particiones. Esto verifica la separación de los IDs y grupos registrados, sin demostrar ausencia de casi duplicados no detectados [18].

## 4.6. Tokenización, segmentación y primeras observaciones

Un token es una unidad obtenida por una regla de segmentación. Para estadística léxica, `regex-words-v1` aplica minúsculas y reconoce secuencias de letras Unicode con apóstrofos internos: `don't` constituye un token; dígitos y puntuación quedan fuera. Para categorías gramaticales, lemas y dependencias se utiliza spaCy 3.8.18 y el modelo preentrenado `en_core_web_sm` 3.8.0, que puede separar contracciones y contar puntuación. Sus totales responden a unidades diferentes y no se suman ni comparan como si fueran la misma medición [2, 13]; [13, E1, celdas 15, 16](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) y [15, E3, celdas 1, 3](fuentes/notebooks/evidencias/E3_morfosintaxis.ipynb).

El léxico posterior registra **902 376 353 tokens y 1 277 145 tipos**, donde un tipo es una forma distinta. El reporte de preparación conserva **902 376 173 palabras** calculadas antes de la conversión a minúsculas. La revalidación comparó por ID los conteos de los diez shards de metadatos: **56 letras** presentan diferencias, que suman exactamente **180 tokens**. Sólo se releyó el texto de esas letras. En ellas, convertir `İ` (U+0130) a minúsculas produce `i` seguida de la marca combinante U+0307; la expresión regular trata esa marca como separador y puede dividir una secuencia de letras. Ambos conteos guardados se reprodujeron exactamente. Como control, sustituir `İ` por `I` antes de convertir a minúsculas recuperó, en cada uno de los 56 casos, el conteo previo. Este control explica la diferencia de conteos en esta versión; no es una corrección aplicada al corpus, no demuestra igualdad de las secuencias de tokens ni determina el idioma de las letras [18]. En adelante, los análisis estadísticos que reutilicen el léxico deben indicar expresamente su total de 902 376 353 tokens [4, 13]; [13, E1, celda 22](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) y [14, E2, celda 3](fuentes/notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb).

La segmentación sintáctica fuerza una frontera en cada salto de verso y permite divisiones adicionales del parser. Un parser predice relaciones gramaticales; una frontera forzada es una decisión de procesamiento, no una prueba de que el verso sea una oración completa. La comparación guardada en E1 utiliza una **muestra de las primeras 400 letras del shard 5**. Con segmentación predeterminada, 3 018 de 4 746 segmentos cruzaban al menos un salto; con fronteras forzadas se obtuvieron 16 955 segmentos y ninguno lo cruzaba. Esta comparación describe el efecto de la regla, sin medir exactitud sintáctica ni justificar que todo cruce sea erróneo ([13, E1, celda 19](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb), código y tabla guardada; no se repitió la anotación de esa muestra). La regla puede fragmentar oraciones que continúan entre versos [13].

Para la morfosintaxis se aplica además una normalización de ciertas grafías con omisión de la `g` final, mediante un texto sombra que permite al modelo analizar una forma terminada en `-ing` y conserva la forma original. El criterio exige que la forma expandida aparezca al menos veinte veces en el léxico del corpus. Es un recurso descriptivo de anotación, no una mejora de precisión demostrada por una ablación. El umbral de veinte apariciones se calcula en el léxico completo; por tanto, esta anotación descriptiva depende también de datos ajenos a `train`. E5 utiliza formas superficiales, conserva stopwords y negación, y no utiliza lemas, etiquetas POS ni la expansión inferida de g-dropping [2, 3; código `semantics.py`, función `words`]. Esto evita atribuir a E5 aquella dependencia de la anotación; tampoco demuestra una evaluación de relevancia ([13, E1, celdas 15, 17](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb); [15, E3, celda 9](fuentes/notebooks/evidencias/E3_morfosintaxis.ipynb); [17, E5, celdas 3, 9](fuentes/notebooks/evidencias/E5_semantica.ipynb)).

La mediana del corpus es **242 palabras, 37 versos y 6 estrofas por letra**, como medidas marginales ([13, E1, celdas 20, 23](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb)). El campo `tag` contiene 1 336 051 letras `pop`, 959 763 `rap`, 621 148 `rock`, 153 552 `rb` y 85 258 `country`. Estas son etiquetas de fuente, no géneros musicalmente validados [4]. La figura 1 compara longitudes dentro de cada tag mediante una distribución acumulada: para cada longitud indica qué proporción de letras no la supera.

![Distribuciones acumuladas de longitud por tag](figuras/e1_longitud_por_tag.png)

**Figura 1. Distribución acumulada de palabras por letra según el tag de origen, sobre las 3 155 772 letras canónicas de `lyrics_full_v1`.** Eje horizontal logarítmico: palabras por letra; eje vertical: proporción acumulada dentro de cada tag. La leyenda informa los tamaños y la línea horizontal marca 0,5. Fuente: [13, E1, celda 28](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) (celda 29 contando desde uno; ID `6e450d0a`; ejecución guardada `In[19]`). Se copió sin modificación el PNG externo `reports/figures/E1/e1_longitud_por_tag.png` generado por esa celda; no se extrajo ni regeneró una imagen del output. El hash de copia y original se conserva en el inventario y en la verificación de esta entrega. Las medianas tabuladas en [13, E1, celda 25](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) y revalidadas desde `doc_stats` [18] son 204 (`pop`), 408 (`rap`), 187 (`rock`), 284 (`rb`) y 215 (`country`) palabras. La separación describe longitudes y no significancia estadística ni propiedades causales de los géneros [13].

La curva de `rap` se desplaza hacia longitudes mayores; su mediana duplica la de `pop` en las tablas guardadas. Esto implica que los conteos agregados de tokens ponderan de forma distinta a los grupos, incluso antes de analizar contenido. Por tanto, las secciones posteriores distinguirán porcentajes por token, tamaños documentales y comparaciones dentro de tag. El campo `year` presenta 1 673 valores anteriores a 1900 y 392 posteriores a 2022, que se señalan como dudosos; las comparaciones temporales delimitan el intervalo válido y no reconstruyen fechas desconocidas ([13, E1, celda 24](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb)). Los tamaños, las medianas y los conteos de años dudosos se revalidaron directamente desde las columnas procesadas [18].

## 4.7. Vínculos de la demo y límites de preparación

El reporte conservado registra **886 grabaciones retenidas**, **850 localizadores Genius distintos** y **849 letras canónicas**; documenta dos filas Genius con un texto deduplicado. Su campo `demo.locator_check.title_artist_normalized_equal` registra **886 comprobaciones de vínculos**, no 886 localizadores distintos; `demo.lyrics_status.accepted` registra 886 grabaciones enlazadas con letras aceptadas. La igualdad de metadatos y la aceptación lingüística son comprobaciones diferentes: la bandera `has_lyrics` por sí sola no demuestra ambas [4, 10]. Las grabaciones heredan la partición textual: 575 de entrenamiento, 210 de prueba y 101 de validación. Esos conteos se refieren a grabaciones, no al reparto global de letras [4].

El mismo reporte registra históricamente 886 archivos de audio presentes y cero grabaciones elegibles para el catálogo combinado. La auditoría de este equipo no encontró `data/processed/demo/lyrics_full_v1/demo_links.parquet`, `medium_prioritarios.json` ni `data/raw/fma/fma_medium/` en sus rutas documentadas. Por tanto, aquellos conteos no acreditan presencia actual de audio ni permiten rehacer aquí la comprobación de vínculos [18]. [PENDIENTE: localizar o restaurar la tabla de vínculos y el audio antes de verificar el catálogo actual; no se realizó esa restauración para redactar.] Un archivo existente no acredita decodificación correcta, correspondencia auditiva, letra revisada o autorización de reproducción. Por eso estas coincidencias no se describen como 886 canciones multimodales validadas. La preparación del corpus textual sí está completa según sus reglas automáticas; la validación humana del idioma, el criterio docente de extensión de 150–300 páginas y la validación del catálogo musical permanecen pendientes [2, 4]. Estas limitaciones acompañan el análisis sin reducir su universo al subconjunto con audio.

# 13. Referencias verificadas de esta entrega

Sistema único de citas numéricas [n], conservado en las secciones y en el integrado. Enlaces como [13, E1, celda 22] añaden evidencia y localizador al número bibliográfico. Toda celda se numera desde cero; el ordinal desde uno, ID y contador de ejecución se distinguen en el mapa de citas. Las entradas internas son evidencia de implementación, no publicaciones revisadas por pares. Fecha de consulta externa: 16 de noviembre de 2026, hora local. No se atribuye autoría institucional al artículo.

[1] SONORA. *Especificación de requisitos académicos, funcionales y técnicos*, v1.2, 12 de noviembre de 2026. Documento interno: [docs/REQUIREMENTS.md](fuentes/docs/REQUIREMENTS.md), §§2–5, 13 y 15.

[2] SONORA. *Corpus completo de letras en inglés y vínculos de la demo*. Documento técnico interno: [docs/CORPUS_LETRAS.md](fuentes/docs/CORPUS_LETRAS.md), §§1–7, 11–13.

[3] SONORA. *E5 — protocolo de representaciones semánticas*, 16 de noviembre de 2026. Protocolo interno: [docs/E5_METODO.md](fuentes/docs/E5_METODO.md). Describe TF-IDF, SGNS y LDA de la implementación; las publicaciones metodológicas originales se incorporarán verificadas en la sección 03.

[4] SONORA. *Quality report: lyrics_full_v1*, generado el 14 de noviembre de 2026 UTC. Artefacto de resultados: [quality_report.json](fuentes/reports/corpus/lyrics_full_v1/quality_report.json). Localizadores por clave en 00_REGISTRO_RESULTADOS.md.

[5] SONORA. *Manifiesto de particiones lyrics_full_v1*. Artefacto reproducible: [manifests/splits/lyrics_full_v1.json](fuentes/manifests/splits/lyrics_full_v1.json), seed, group_rules, by_split y actual_fraction_lyrics.

[6] SONORA. *Recuperación textual ítem a ítem*. Código interno: [lyrics.py](fuentes/packages/sonora/src/sonora/recommendation/lyrics.py), función recommend_lyrics; [main.py](fuentes/apps/api/src/sonora_api/main.py), estado de API; [ranking.yaml](fuentes/config/ranking.yaml), hipótesis de combinación. El código se cita como implementación, no como prueba empírica de calidad.

[7] theelderemo. *genius-lyrics-cleaned*. Dataset en Hugging Face, sin fecha de publicación comprobada. [Tarjeta oficial](https://huggingface.co/datasets/theelderemo/genius-lyrics-cleaned). Verificados identificador y esquema público. Revisión de la copia local no registrada. No se asume que una licencia declarada por el depositante resuelva derechos sobre cada letra. DOI visible en tarjeta no se incorpora como identificador verificado del snapshot local.

[8] Responsables del repositorio mdeff/fma. *FMA: A Dataset For Music Analysis*. [Repositorio oficial de datos y documentación](https://github.com/mdeff/fma). Documentación de variantes y clips; no se atribuye un año bibliográfico al repositorio consultado. La publicación metodológica FMA y sus autores se verificarán antes de añadirla a antecedentes.

[9] SONORA. *Manifiestos de la entrada Genius y de la corrida completa*. [genius_snapshot.json](fuentes/manifests/sources/genius_snapshot.json) y [lyrics_full_v1.json](fuentes/manifests/runs/lyrics_full_v1.json). Hashes y procedencia de la copia local.

[10] SONORA. *Configuración y preparación lingüística*. [lyrics_corpus.yaml](fuentes/config/lyrics_corpus.yaml); [lyrics_text.py](fuentes/packages/sonora/src/sonora/preprocessing/lyrics_text.py), build_views/dedup_key/language_excerpt; [lyrics_corpus.py](fuentes/packages/sonora/src/sonora/ingestion/lyrics_corpus.py), _group_roots y consolidación; [language.py](fuentes/packages/sonora/src/sonora/nlp/language.py), needs_secondary/decide. Fuentes de software local.

[11] SONORA. *Revisión lingüística y cierre de E4*, 16 de noviembre de 2026. [E4_REVISION.md](fuentes/docs/E4_REVISION.md), ejemplo lyr_9b869033ae33f65fdae4, sent_i=56, line_i=61; revisión del autor pendiente.

[12] SONORA. *Exportación del espacio E5 e5-surface-v2*. [complete.json](fuentes/data/processed/nlp/lyrics_full_v1/semantics/e5-surface-v2/representations/complete.json), counts y space_id; [trained.json](fuentes/artifacts/models/lyrics_full_v1/e5-surface-v2/trained.json), modelos seleccionados y test_consumed. Artefactos locales, fuera de Git; disponibilidad no garantizada en otra copia.

[13] SONORA. *Evidencia 1 — Construcción y exploración del corpus de letras*. [Notebook ejecutado](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb), celdas base cero 15, 19–25 y 28. [Manifiesto NLP](fuentes/manifests/nlp/lyrics_full_v1.json), lexicon y annotations; [lexicon.py](fuentes/packages/sonora/src/sonora/nlp/lexicon.py), count_file. Las salidas son evidencia guardada con las reservas registradas en los controles.

Pendientes bibliográficos: publicaciones primarias de TF-IDF/recuperación, SGNS, LDA, spaCy, KenLM, Zipf y antecedentes específicos de recuperación musical. No se incluyen referencias no comprobadas ni citas secundarias como si se hubieran leído los originales.


[14] SONORA. *Evidencia 2 — Estadística del corpus y modelo de lenguaje de n-gramas*. [Notebook E2](fuentes/notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb). Celdas e IDs exactos de esta versión en [00_CITAS_NOTEBOOKS.md](fuentes/articulo/00_CITAS_NOTEBOOKS.md); SHA-256 en revalidacion_independiente.json. Fuente de evidencia guardada, no publicación metodológica.

[15] SONORA. *Evidencia 3 — Morfosintaxis*. [Notebook E3](fuentes/notebooks/evidencias/E3_morfosintaxis.ipynb). Celdas e IDs exactos de esta versión en [00_CITAS_NOTEBOOKS.md](fuentes/articulo/00_CITAS_NOTEBOOKS.md); SHA-256 en revalidacion_independiente.json. Fuente de evidencia guardada, no publicación metodológica.

[16] SONORA. *Evidencia 4 — Sintaxis y dependencias*. [Notebook E4](fuentes/notebooks/evidencias/E4_sintaxis_dependencias.ipynb). Celdas e IDs exactos de esta versión en [00_CITAS_NOTEBOOKS.md](fuentes/articulo/00_CITAS_NOTEBOOKS.md); SHA-256 en revalidacion_independiente.json. Fuente de evidencia guardada, no publicación metodológica.

[17] SONORA. *Evidencia 5 — Semántica*. [Notebook E5](fuentes/notebooks/evidencias/E5_semantica.ipynb). Celdas e IDs exactos de esta versión en [00_CITAS_NOTEBOOKS.md](fuentes/articulo/00_CITAS_NOTEBOOKS.md); SHA-256 en revalidacion_independiente.json. Fuente de evidencia guardada, no publicación metodológica.

[18] SONORA, auditoría para el artículo. *Revalidación independiente de conteos, particiones y casos Unicode*, 16 de noviembre de 2026, hora local. [Procedimiento](fuentes/articulo/revalidar_hallazgos.py) y [resultados](fuentes/articulo/revalidacion_independiente.json). Lectura de metadatos de los diez shards; texto sólo en 56 letras discrepantes. Sin ejecución de pipelines ni cambios al corpus.


---

## FIN DE LA PARTE I

## PARTE II — EVIDENCIA Y CONTROLES EDITORIALES

Los siguientes documentos apoyan la conversión; no son secciones nuevas del artículo.


---

### A. Alcance y pendientes

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

Se utilizó exclusivamente la sesión de apoyo **Document SONORA project** (`01a1e751-d65d-7ce1-bc85-282069bb1d6c`), con cuatro rondas documentadas. Se revisaron individualmente R01–R19 y once objeciones metodológicas. [Fact checks](fuentes/articulo/00_FACT_CHECKS.md) y [registro del intercambio](fuentes/articulo/revision_cruzada_sonora.json). Las respuestas se contrastaron con código y artefactos; repetir un reporte entre sesiones no se contó como revalidación independiente.

La revalidación propia confirmó IDs, grupos, conteos de particiones, ausencia de solapamiento de grupos registrados, exclusiones, tamaños por tag, medianas y años dudosos. La diferencia de 180 tokens quedó explicada en 56 letras. El tiempo y el procedimiento están en revalidacion_independiente.json. No se ejecutaron pipelines, notebooks ni entrenamiento. Se corrigieron la actualidad de demo/audio, la confusión entre 886 comprobaciones y 850 localizadores, la generalización train-only y el alcance de metadatos canónicos.

Las citas inline distinguen E1–E5 y celda base cero. 00_CITAS_NOTEBOOKS.md conserva ordinal, ID y ejecución. Todas las figuras candidatas tienen notebook/celda de generación o visualización; Figura 1 mantiene origen externo y hash. Resumen/conclusiones y secciones siguientes siguen pendientes. El constructor histórico construir_entrega.py se bloqueó para evitar que sobrescriba estas correcciones; esta revisión se aplica con actualizar_revalidacion.py.



---

### B. Veredictos por hallazgo

# Fact checks de los hallazgos publicados

Revisión de todos los 19 registros iniciales y de sus interpretaciones. La revalidación propia no toma como confirmación independiente que la otra sesión repita el mismo reporte. Resultado computable: [revalidacion_independiente.json](fuentes/articulo/revalidacion_independiente.json). Procedimiento de lectura: [revalidar_hallazgos.py](fuentes/articulo/revalidar_hallazgos.py). Crítica cruzada: [revision_cruzada_sonora.json](fuentes/articulo/revision_cruzada_sonora.json).

| Hallazgo | Veredicto | Evidencia y límite | Cita notebook o fuente correcta |
|---|---|---|---|
| R01 | Corroborado desde salidas procesadas; entrada original no disponible | 3 177 443 registros representados + 2145 exclusiones/revisión = 3 179 588; data/raw/genius sin Parquet | [13, E1, celdas 3, 6](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R02 | Revalidado desde metadatos | Suma n_source_records de canónicas = 3 177 443 | [13, E1, celdas 6, 14](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R03 | Revalidado desde metadatos e IDs | Diez shards: 3 155 772 filas; cobertura exacta una vez en split | [13, E1, celdas 14, 22](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R04 | Revalidado; denominador aclarado | 3 177 443 aceptados menos 3 155 772 canónicas = 21 671; denominador de duplicación: aceptados | [13, E1, celda 14](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R05 | Revalidado desde exclusions.parquet | 1914 review; 155 no inglés, 75 placeholders y 1 texto corto | [13, E1, celdas 6, 11](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R06 | Reconciliado con casos; pendiente anterior resuelto | 56 letras; diferencia +180. Control U+0130 antes de lower recupera conteo previo en cada caso | No figura la explicación de U+0130 en el notebook; fuente primaria del hallazgo nuevo: [18] |
| R07 | Revalidado desde count y doc_stats | 902 376 353 tokens; 1 277 145 filas/tipos del léxico | [13, E1, celda 22](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb); [14, E2, celda 3](fuentes/notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb) |
| R08 | Revalidado directamente en el Parquet | 3 145 790 grupos, máximo 24 letras; 0 multisbplit; 2 208 832/631 651/315 289 letras y 2 201 895/629 609/314 286 grupos; SHA coincide. No descarta duplicados no detectados | [13, E1, celda 25](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb); asignación por grupos en manifiesto/código, no demostrada por esa celda sola |
| R09 | Acotado a resultado histórico; actualidad no verificable | 886 grabaciones, 850 localizadores y 849 letras en quality_report.demo; tablas/audio ausentes en rutas previstas | Sin celda E1–E5 que revalide demo; citar [4], claves demo, y [18] |
| R10 | Revalidado desde metadatos canónicos | Cinco conteos coinciden; tag del primer canónico no representa todas las etiquetas originales | [13, E1, celda 25](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R11 | Revalidado desde columnas numéricas | Medianas 242 palabras, 37 versos, 6 estrofas; marginales, no una canción típica íntegra | [13, E1, celdas 20, 23](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R12 | Corroborado en output; no reanotado | Tabla 4746/3018 vs 16955/0 en muestra 400. No se repite spaCy; no mide precisión | [13, E1, celda 19](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R13 | Revalidado desde year | 1673 anteriores a 1900, 392 posteriores a 2022; no reconstruye fechas reales | [13, E1, celda 24](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R14 | Corroborado entre reportes y notebook | Suma POS = 1 033 733 693; docs coincide con corpus. Anotaciones individuales no releídas; ejemplos de 3 letras | [15, E3, celdas 1, 3, 9](fuentes/notebooks/evidencias/E3_morfosintaxis.ipynb) |
| R15 | Corroborado entre artefactos; no reparseado | Tokens E4 coinciden con E3; global_metrics guardadas, sin recalcular todos los arcos | [16, E4, celdas 1, 5, 7, 9](fuentes/notebooks/evidencias/E4_sintaxis_dependencias.ipynb) |
| R16 | Corroborado entre manifiestos y notebook | counts y space_id iguales a auditoría E5; no se releen todos los vectores/modelos | [17, E5, celdas 1, 3](fuentes/notebooks/evidencias/E5_semantica.ipynb) |
| R17 | Muestra y pertenencia revalidadas; alcance completo pendiente | 2000 IDs distintos, todos validation; PCA/contextos no son corpus completo | [17, E5, celdas 5, 7](fuentes/notebooks/evidencias/E5_semantica.ipynb) |
| R18 | Auditoría previa corroborada documentalmente | Valores de norma/cobertura guardados coinciden con notebook. No se repite validación de vectores | [17, E5, celda 1](fuentes/notebooks/evidencias/E5_semantica.ipynb) |
| R19 | Revalidado desde doc_stats por tag | 204/408/187/284/215 palabras; sin significancia inferida | [13, E1, celdas 25, 28](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |

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



---

### C. Registro de cifras y denominadores

# Registro de resultados — segunda entrega

Verificación original y revalidación se distinguen por resultado. Índices base cero; [convención e IDs](fuentes/articulo/00_CITAS_NOTEBOOKS.md). Valores/configuraciones completos: [resultados_verificados.json](fuentes/articulo/resultados_verificados.json). Evaluación crítica individual: [00_FACT_CHECKS.md](fuentes/articulo/00_FACT_CHECKS.md).

| ID | Fuente y localizador | Valor y unidad | Universo / denominador | Estado actualizado y límite |
|---|---|---|---|---|
| R01 | `reports/corpus/lyrics_full_v1/quality_report.json` · `source_records_read` | 3179588; registros | lyrics_full_v1; corpus real completo; denominador 10 Parquet | Corroborado desde salidas procesadas; entrada original no disponible. Snapshot remoto sin revisión; SHA-256 locales en manifiesto. [13, E1, celdas 3, 6](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R02 | `reports/corpus/lyrics_full_v1/quality_report.json` · `accepted_source_records` | 3177443; registros | lyrics_full_v1; corpus real completo; denominador 3179588 | Revalidado desde metadatos. Aceptación automática; no validación humana de todas las letras. [13, E1, celdas 6, 14](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R03 | `reports/corpus/lyrics_full_v1/quality_report.json` · `canonical_lyrics` | 3155772; letras | lyrics_full_v1; corpus real completo; denominador 3179588 | Revalidado desde metadatos e IDs. Aceptación automática; no validación humana de todas las letras. [13, E1, celdas 14, 22](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R04 | `reports/corpus/lyrics_full_v1/quality_report.json` · `accepted_duplicate_source_records` | 21671; registros | lyrics_full_v1; corpus real completo; denominador 3177443 | Revalidado; denominador aclarado. Aceptación automática; no validación humana de todas las letras. [13, E1, celda 14](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R05 | `reports/corpus/lyrics_full_v1/quality_report.json` · `exclusion_or_review_rule_counts` | {"language_uncertain": 1914, "non_english": 155, "placeholder_text": 75, "too_few_words": 1}; registros por regla | lyrics_full_v1; corpus real completo; denominador 3179588 | Revalidado desde exclusions.parquet. 1914 en revisión no pertenecen al corpus aceptado. [13, E1, celdas 6, 11](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R06 | `reports/corpus/lyrics_full_v1/quality_report.json` · `canonical_total_words` | 902376173; palabras regex antes de minúsculas | lyrics_full_v1; corpus real completo; denominador 3155772 | Reconciliado con casos; pendiente anterior resuelto. Diferencia de +180 reconciliada en 56 letras; control mecánico no demuestra calidad lingüística ni identidad de secuencias. No figura la explicación de U+0130 en el notebook; fuente primaria del hallazgo nuevo: [18] |
| R07 | `manifests/nlp/lyrics_full_v1.json` · `lexicon.tokens / lexicon.types` | {"tokens": 902376353, "types": 1277145}; tokens / tipos | lyrics_full_v1; corpus real completo; denominador 3155772 | Revalidado desde count y doc_stats. No confundir con tokenización spaCy ni R06. [13, E1, celda 22](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb); [14, E2, celda 3](fuentes/notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb) |
| R08 | `manifests/splits/lyrics_full_v1.json` · `by_split / actual_fraction_lyrics / groups` | Ver detalle estructurado, R08; letras, grupos y fracciones | lyrics_full_v1; corpus real completo; denominador 3155772 | Revalidado directamente en el Parquet. No hay solapamiento de grupos registrados; no se descartan casi duplicados no detectados. [13, E1, celda 25](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb); asignación por grupos en manifiesto/código, no demostrada por esa celda sola |
| R09 | `reports/corpus/lyrics_full_v1/quality_report.json` · `demo` | Ver detalle estructurado, R09; grabaciones / localizadores / letras | Demo histórica de lyrics_full_v1: 886 grabaciones; archivos fuente/demo/audio no presentes en rutas previstas del equipo actual; denominador 886 | Acotado a resultado histórico; actualidad no verificable. Cifras históricas del reporte, no catálogo local revalidado. Sin celda E1–E5 que revalide demo; citar [4], claves demo, y [18] |
| R10 | `reports/corpus/lyrics_full_v1/quality_report.json` · `canonical_tag_counts` | {"pop": 1336051, "rap": 959763, "rock": 621148, "rb": 153552, "country": 85258}; letras por tag | lyrics_full_v1; corpus real completo; denominador 3155772 | Revalidado desde metadatos canónicos. Tags no son géneros verificados; selección de registro canónico pierde multiplicidad de metadatos. [13, E1, celda 25](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R11 | `reports/corpus/lyrics_full_v1/quality_report.json` · `canonical_n_words.p50 / canonical_n_lines.p50 / canonical_n_stanzas.p50` | {"palabras": 242, "versos": 37, "estrofas": 6}; medianas por letra | lyrics_full_v1; corpus real completo; denominador 3155772 | Revalidado desde columnas numéricas. Medianas marginales; no describen necesariamente una misma canción. [13, E1, celdas 20, 23](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R12 | `notebooks/evidencias/E1_construccion_exploracion.ipynb` · `cells[19].outputs: tabla default/lines` | {"default_segments": 4746, "default_crossing": 3018, "forced_segments": 16955, "forced_crossing": 0}; segmentos | Muestra real: primeras 400 letras del shard 5; denominador 400 | Corroborado en output; no reanotado. Muestra dirigida; cruzar versos no equivale por sí solo a error. [13, E1, celda 19](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R13 | `notebooks/evidencias/E1_construccion_exploracion.ipynb` · `cells[24].outputs: year` | {"below_1900": 1673, "above_2022": 392}; letras con año dudoso | lyrics_full_v1; corpus real completo; denominador 3155772 | Revalidado desde year. No determina fecha verdadera ni motivo del error. [13, E1, celda 24](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |
| R14 | `reports/nlp/lyrics_full_v1/e3_summary.json` · `version / docs / tokens / sample_docs` | {"version": "e3-morphology-v1", "docs": 3155772, "tokens": 1033733693, "sample_docs": 5000}; conteos; ver campos | lyrics_full_v1; corpus real completo; denominador 3155772 | Corroborado entre reportes y notebook. Agregados completos; ejemplos dirigidos y revisión humana pendientes; no precisión lingüística. [15, E3, celdas 1, 3, 9](fuentes/notebooks/evidencias/E3_morfosintaxis.ipynb) |
| R15 | `reports/nlp/lyrics_full_v1/e4_summary.json` · `version / docs / global_metrics` | Ver detalle estructurado, R15; conteos; ver campos | lyrics_full_v1; corpus real completo; denominador 3155772 | Corroborado entre artefactos; no reparseado. Agregados completos; ejemplos dirigidos y revisión humana pendientes; no precisión lingüística. [16, E4, celdas 1, 5, 7, 9](fuentes/notebooks/evidencias/E4_sintaxis_dependencias.ipynb) |
| R16 | `data/processed/nlp/lyrics_full_v1/semantics/e5-surface-v2/representations/complete.json` · `counts / space_id` | Ver detalle estructurado, R16; documentos y tokens; identificador de espacio | lyrics_full_v1; corpus real completo; denominador 3155772 | Corroborado entre manifiestos y notebook. Disponibilidad no mide calidad; transformar test no equivale a evaluarlo. [17, E5, celdas 1, 3](fuentes/notebooks/evidencias/E5_semantica.ipynb) |
| R17 | `reports/nlp/lyrics_full_v1/e5_analysis.json` · `scope / n_projected / projection` | {"scope": "bottom-SHA256 sample of <=2000 validation lyrics; models fitted on full train", "n_projected": 2000, "variance_ratio": [0.23323145508766174, 0.09852376580238342]}; letras y fracciones de varianza | Muestra real de 2000 letras de validation; modelos ajustados con todo train; denominador 2000 | Muestra y pertenencia revalidadas; alcance completo pendiente. Proyección y contextos sobre muestra; falta análisis semántico contextual sobre todo el corpus pertinente. [17, E5, celdas 5, 7](fuentes/notebooks/evidencias/E5_semantica.ipynb) |
| R18 | `reports/nlp/lyrics_full_v1/e5_verification.json` · `unique_ids / token_coverage_by_split / max_embedding_norm_error / max_topic_sum_error` | Ver detalle estructurado, R18; IDs; fracciones; errores absolutos | lyrics_full_v1; corpus real completo; denominador 3155772 | Auditoría previa corroborada documentalmente. Es evidencia de la otra sesión, no auditoría repetida aquí; integridad numérica no equivale a calidad semántica. [17, E5, celda 1](fuentes/notebooks/evidencias/E5_semantica.ipynb) |
| R19 | `notebooks/evidencias/E1_construccion_exploracion.ipynb` · `cells[25].outputs: mediana palabras por tag` | {"pop": 204, "rap": 408, "rock": 187, "rb": 284, "country": 215}; palabras regex por letra; mediana | lyrics_full_v1; corpus real completo; denominador {'pop': 1336051, 'rap': 959763, 'rock': 621148, 'rb': 153552, 'country': 85258} | Revalidado desde doc_stats por tag. Medianas guardadas; no significancia ni etiquetas de género validadas. [13, E1, celdas 25, 28](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) |

Todos estos registros proceden de datos reales; no se incorporan métricas de fixtures. Los denominadores de cada porcentaje específico se explicarán al redactar su sección. Ninguna celda se ejecutó para esta revisión; sólo se realizaron los cálculos acotados del procedimiento enlazado.



---

### D. Notebooks, índices de celda e identificadores

# Citas a notebooks y convención de celdas

Las citas inline usan el número bibliográfico, E1–E5 y el índice de celda base cero: incluye celdas Markdown y código. No es el contador `In[n]`. El ordinal base uno facilita encontrarla en visores que enumeran desde uno. El ID identifica esta celda en el snapshot; puede cambiar si el notebook se regenera. Los enlaces abren el archivo, sin prometer navegación a una celda que todos los visores soporten.

| Evidencia | Referencia | Notebook | SHA-256 de la versión revisada |
|---|---|---|---|
| E1 | [13] | [E1_construccion_exploracion.ipynb](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) | `0042d469b7e1fb95490fe642b5c3d76b2052ffc90536a8a42d7e8144460d05d6` |
| E2 | [14] | [E2_estadistica_modelos_lenguaje.ipynb](fuentes/notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb) | `cac056b511313b5a0411fe0611c5675b72b6bef452d99da5b5ee2ed8790a686a` |
| E3 | [15] | [E3_morfosintaxis.ipynb](fuentes/notebooks/evidencias/E3_morfosintaxis.ipynb) | `8dfc8d715215914f86e11ca27b515e6fe289fa5936cee229a16a53cb79a1021b` |
| E4 | [16] | [E4_sintaxis_dependencias.ipynb](fuentes/notebooks/evidencias/E4_sintaxis_dependencias.ipynb) | `6b6c3403b9ee5a455b050ef81676740e42d700031b190218796a75f6bcb8c7d8` |
| E5 | [17] | [E5_semantica.ipynb](fuentes/notebooks/evidencias/E5_semantica.ipynb) | `128fb74f286db1056fd843c72714442393aa81dc17dc479fb8eea1e1bd6d816f` |

## Localizadores de todas las celdas

| Evidencia | Celda base cero | Ordinal base uno | ID de celda | Ejecución guardada | Tipo |
|---|---:|---:|---|---|---|
| E1 | 0 | 1 | `14c036f6` | — | markdown |
| E1 | 1 | 2 | `c7f64d86` | 1 | code |
| E1 | 2 | 3 | `576e85db` | — | markdown |
| E1 | 3 | 4 | `9bc980bb` | 2 | code |
| E1 | 4 | 5 | `0267b34d` | 3 | code |
| E1 | 5 | 6 | `cb6974fc` | — | markdown |
| E1 | 6 | 7 | `a45f1813` | 4 | code |
| E1 | 7 | 8 | `3dfb907b` | 5 | code |
| E1 | 8 | 9 | `0e006390` | 6 | code |
| E1 | 9 | 10 | `a5b2a2d3` | — | markdown |
| E1 | 10 | 11 | `0a634d7a` | — | markdown |
| E1 | 11 | 12 | `badcbee7` | 7 | code |
| E1 | 12 | 13 | `d5bb6218` | 8 | code |
| E1 | 13 | 14 | `17ec676c` | — | markdown |
| E1 | 14 | 15 | `1b97b987` | 9 | code |
| E1 | 15 | 16 | `853367fb` | — | markdown |
| E1 | 16 | 17 | `5c311146` | 10 | code |
| E1 | 17 | 18 | `ae9949e7` | 11 | code |
| E1 | 18 | 19 | `3561ce18` | — | markdown |
| E1 | 19 | 20 | `78ae3643` | 12 | code |
| E1 | 20 | 21 | `a5e867af` | 13 | code |
| E1 | 21 | 22 | `a4fa13ed` | — | markdown |
| E1 | 22 | 23 | `0862941e` | 14 | code |
| E1 | 23 | 24 | `e0543ae0` | 15 | code |
| E1 | 24 | 25 | `4bed3b94` | 16 | code |
| E1 | 25 | 26 | `aa2f3f3f` | 17 | code |
| E1 | 26 | 27 | `9fb752b5` | — | markdown |
| E1 | 27 | 28 | `838986fd` | 18 | code |
| E1 | 28 | 29 | `6e450d0a` | 19 | code |
| E1 | 29 | 30 | `e1f9abae` | 20 | code |
| E1 | 30 | 31 | `de117d38` | 21 | code |
| E1 | 31 | 32 | `193d77ab` | — | markdown |
| E2 | 0 | 1 | `43e3c2ac` | — | markdown |
| E2 | 1 | 2 | `aa4bf3f7` | 1 | code |
| E2 | 2 | 3 | `a8cd9ba1` | — | markdown |
| E2 | 3 | 4 | `b1201f6c` | 2 | code |
| E2 | 4 | 5 | `24e600fd` | — | markdown |
| E2 | 5 | 6 | `3aa5925e` | 3 | code |
| E2 | 6 | 7 | `b5b6dbde` | 4 | code |
| E2 | 7 | 8 | `9a86e567` | — | markdown |
| E2 | 8 | 9 | `13b10d54` | 5 | code |
| E2 | 9 | 10 | `3a3d5327` | 6 | code |
| E2 | 10 | 11 | `7f7f1c08` | — | markdown |
| E2 | 11 | 12 | `8b337301` | 7 | code |
| E2 | 12 | 13 | `615dec9b` | 8 | code |
| E2 | 13 | 14 | `80d65ce9` | — | markdown |
| E2 | 14 | 15 | `3de13293` | 9 | code |
| E2 | 15 | 16 | `d27a1060` | 10 | code |
| E2 | 16 | 17 | `48906361` | — | markdown |
| E2 | 17 | 18 | `2573313f` | 11 | code |
| E2 | 18 | 19 | `5b1a954e` | — | markdown |
| E2 | 19 | 20 | `51d14a6c` | 12 | code |
| E2 | 20 | 21 | `b7cfbc65` | 13 | code |
| E2 | 21 | 22 | `b9c955a0` | — | markdown |
| E2 | 22 | 23 | `39af9e77` | 14 | code |
| E2 | 23 | 24 | `1c1c52ae` | 15 | code |
| E2 | 24 | 25 | `9efa86f2` | — | markdown |
| E2 | 25 | 26 | `a1e17295` | 16 | code |
| E2 | 26 | 27 | `58033b93` | 17 | code |
| E2 | 27 | 28 | `144ee93c` | 18 | code |
| E2 | 28 | 29 | `2f299d9f` | — | markdown |
| E3 | 0 | 1 | `607e12db` | — | markdown |
| E3 | 1 | 2 | `fee85a28` | 1 | code |
| E3 | 2 | 3 | `dbf2e936` | — | markdown |
| E3 | 3 | 4 | `48319be1` | 2 | code |
| E3 | 4 | 5 | `5ed5b4f7` | — | markdown |
| E3 | 5 | 6 | `77b710c3` | 3 | code |
| E3 | 6 | 7 | `2aa0b276` | — | markdown |
| E3 | 7 | 8 | `21023f25` | 4 | code |
| E3 | 8 | 9 | `cd5bcc16` | — | markdown |
| E3 | 9 | 10 | `5d68e089` | 5 | code |
| E3 | 10 | 11 | `9a6671bd` | — | markdown |
| E3 | 11 | 12 | `6941f168` | — | markdown |
| E4 | 0 | 1 | `ccc33d89` | — | markdown |
| E4 | 1 | 2 | `891963e9` | 1 | code |
| E4 | 2 | 3 | `3235dbe9` | — | markdown |
| E4 | 3 | 4 | `e7a854fa` | 2 | code |
| E4 | 4 | 5 | `e7067275` | — | markdown |
| E4 | 5 | 6 | `6ae76f8f` | 3 | code |
| E4 | 6 | 7 | `d8820153` | — | markdown |
| E4 | 7 | 8 | `16aaaf6e` | 4 | code |
| E4 | 8 | 9 | `276795ab` | — | markdown |
| E4 | 9 | 10 | `587e16da` | 5 | code |
| E4 | 10 | 11 | `d20cf8b7` | — | markdown |
| E5 | 0 | 1 | `b0e5a8ac` | — | markdown |
| E5 | 1 | 2 | `25b0bcbd` | 1 | code |
| E5 | 2 | 3 | `42e5ca9d` | — | markdown |
| E5 | 3 | 4 | `544fa661` | 2 | code |
| E5 | 4 | 5 | `4f361ba2` | — | markdown |
| E5 | 5 | 6 | `6d079148` | 3 | code |
| E5 | 6 | 7 | `fc55edfa` | — | markdown |
| E5 | 7 | 8 | `85db111b` | 4 | code |
| E5 | 8 | 9 | `df805767` | — | markdown |
| E5 | 9 | 10 | `932a5245` | 5 | code |
| E5 | 10 | 11 | `42aef672` | — | markdown |
| E5 | 11 | 12 | `dbfd0934` | 6 | code |
| E5 | 12 | 13 | `f8c88348` | — | markdown |

Las citas acreditan lo que el notebook documenta o guarda; no garantizan actualidad por sí mismas. Los fact checks distinguen relectura de salidas, recálculo desde metadatos y límites sin resolver. Para una afirmación de demo sin celda que la respalde, se cita el reporte JSON; no se inventa una cita E1.



---

### E. Procedencia de imágenes

# Inventario de figuras

Los assets de marca, portadas y fondos de apps/web son ilustraciones de interfaz, no evidencia científica. No se incorporan. No se crearon imágenes artificiales ni se regeneraron curvas. Sólo la ECDF E1 se incorpora en esta entrega; inspeccionada visualmente. Las demás son candidatas pendientes de lectura visual y cotejo específico de ejes antes de publicarse.

| Archivo (ruta desde raíz) | Sección | Representación, ejes y parámetros | Universo y límites |
|---|---|---|---|
| `reports/figures/E1/e1_letras_por_decada.png` | 04 | Barras: x década de year; y letras; años 1900–2022 | Metadato de fuente; excluye años dudosos; décadas no equilibradas |
| `reports/figures/E1/e1_longitud_letras.png` | 04 | Histograma de palabras por letra; x logarítmico, y letras; 70 bordes logarítmicos | Corpus canónico completo; cola y mediana; no prueba normalidad |
| `reports/figures/E1/e1_longitud_por_tag.png` | 04 | ECDF: x palabras por letra logarítmico; y proporción acumulada [0,1]; colores cinco tags; línea y=0,5 | Corpus completo por tag; no prueba significancia ni género validado |
| `reports/figures/E1/e1_repeticion_por_tag.png` | 04/05 | Distribución de proporción de versos repetidos; x [0,1]; series por tag | Corpus completo; depende del transcriptor; revisar unidades y barras antes de incluir |
| `reports/figures/E2/e2_difusion_repeticion.png` | 05 | x % letras con palabra; y ocurrencias por letra que la usa; escalas log; categorías | Palabras con ≥100000 ocurrencias, no todo vocabulario |
| `reports/figures/E2/e2_espectro.png` | 05 | Espectro V(m) por orden; frecuencias m≤200 | Corpus completo; sólo intervalo visible, no toda la cola |
| `reports/figures/E2/e2_logodds_tags.png` | 05 | Barras z de log-odds por tag contra resto; prior 10000; contenido ≥1000 | Corpus completo; prior descriptivo; etiquetas y desbalance condicionan contraste |
| `reports/figures/E2/e2_perplejidad_tags.png` | 05/10 | x tag; y perplejidad; curvas órdenes 2/3/4 KenLM | Ajuste train y evaluación validation con finales de verso; no relevancia |
| `reports/figures/E2/e2_top_palabras_politicas.png` | 05 | Ranking de frecuencias bajo tres políticas de filtrado | Corpus completo; lista de stopwords/vocablos modifica universo retenido |
| `reports/figures/E2/e2_zipf.png` | 05 | Rango–frecuencia; ajustes logarítmicos Zipf y Mandelbrot | Uni/bi/trigramas completos; tramos de ajuste distintos; R² no prueba ley universal |
| `reports/figures/E3/pos_decadas.png` | 06 | Evolución descriptiva global de seis POS por década; no desagregada por tag en la figura | Años válidos; umbral de soporte; no causalidad |
| `reports/figures/E3/pos_global.png` | 06 | Barras POS global; conteos y porcentajes en notebook | Tokens spaCy; especificar denominador al seleccionar |
| `reports/figures/E3/pos_tags.png` | 06 | Mapa de calor POS por tag | Excluir PUNCT/SYM/SPACE según código; no exactitud de anotación |
| `reports/figures/E4/arbol_coordination.png` | 07 | Árbol cabeza→dependiente; etiquetas de dependencia, token, POS e índice; sin ejes numéricos | Cuatro casos dirigidos del shard 0; ver e4_examples.json; no precisión del parser |
| `reports/figures/E4/arbol_fragment.png` | 07 | Árbol cabeza→dependiente; etiquetas de dependencia, token, POS e índice; sin ejes numéricos | Cuatro casos dirigidos del shard 0; ver e4_examples.json; no precisión del parser |
| `reports/figures/E4/arbol_subordinate.png` | 07 | Árbol cabeza→dependiente; etiquetas de dependencia, token, POS e índice; sin ejes numéricos | Cuatro casos dirigidos del shard 0; ver e4_examples.json; no precisión del parser |
| `reports/figures/E4/arbol_transitive.png` | 07 | Árbol cabeza→dependiente; etiquetas de dependencia, token, POS e índice; sin ejes numéricos | Cuatro casos dirigidos del shard 0; ver e4_examples.json; no precisión del parser |
| `reports/figures/E4/comparacion_decadas.png` | 07 | Métricas sintácticas globales por década; no desagregadas por tag en la figura | Años válidos y composición variable; no seguimiento longitudinal |
| `reports/figures/E4/comparacion_tags.png` | 07 | Métricas sintácticas por tag | Medias por segmento y por arco; no complejidad artística |
| `reports/figures/E4/distribuciones.png` | 07 | Histogramas de longitud sin puntuación y profundidad | Segmentos completos; truncamiento visual declarado; medias no truncadas |
| `reports/figures/E5/pca_validation.png` | 08 | PCA: x componente 1, y componente 2; colores por tag; dos componentes | Muestra 2000 validation; 23,323 % y 9,852 % de varianza; no calidad semántica |

## Imágenes incrustadas y procedencia de celdas

Celdas base cero. El código íntegro de cada celda está en auditoria_notebooks.json y permite recuperar límites, leyenda y parámetros. No se presupone identidad binaria entre el PNG externo y el incrustado.
- `notebooks/evidencias/E1_construccion_exploracion.ipynb`, celda 27, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E1_construccion_exploracion.ipynb`, celda 28, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E1_construccion_exploracion.ipynb`, celda 29, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E1_construccion_exploracion.ipynb`, celda 30, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb`, celda 6, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb`, celda 15, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb`, celda 17, output 1: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb`, celda 20, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb`, celda 23, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb`, celda 26, output 1: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E3_morfosintaxis.ipynb`, celda 3, output 1: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E3_morfosintaxis.ipynb`, celda 5, output 6: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E3_morfosintaxis.ipynb`, celda 5, output 7: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E4_sintaxis_dependencias.ipynb`, celda 3, output 0: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E4_sintaxis_dependencias.ipynb`, celda 5, output 2: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E4_sintaxis_dependencias.ipynb`, celda 5, output 3: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E4_sintaxis_dependencias.ipynb`, celda 7, output 4: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E4_sintaxis_dependencias.ipynb`, celda 7, output 8: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E4_sintaxis_dependencias.ipynb`, celda 7, output 12: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E4_sintaxis_dependencias.ipynb`, celda 7, output 16: PNG guardado; parámetros y fuente de datos en esa celda.
- `notebooks/evidencias/E5_semantica.ipynb`, celda 5, output 1: PNG guardado; parámetros y fuente de datos en esa celda.

La copia seleccionada es figuras/e1_longitud_por_tag.png, procedente de reports/figures/E1/e1_longitud_por_tag.png; E1 celda 28. El hash de copia se registra en verificacion_entrega.json. La figura E5 procede de packages/sonora/src/sonora/nlp/semantic_analysis.py y e5_analysis.json, y también está incrustada en E5_semantica.ipynb, celda 5.



## Procedencia precisa por notebook

Índices base cero; ordinal desde uno e ID se dan para desambiguar. «Generada» identifica código de gráfica; «mostrada» identifica una imagen preexistente que el notebook carga. Sólo Figura 1 se incluye en el artículo actual.

| Imagen | Notebook y celda | Ordinal / ID | Relación con el notebook |
|---|---|---|---|
| `e1_longitud_letras.png` | [13, E1, celda 27](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) | 28 / `838986fd` | Generada y guardada por código de celda |
| `e1_longitud_por_tag.png` | [13, E1, celda 28](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) | 29 / `6e450d0a` | Generada y guardada por código de celda |
| `e1_letras_por_decada.png` | [13, E1, celda 29](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) | 30 / `e1f9abae` | Generada y guardada por código de celda |
| `e1_repeticion_por_tag.png` | [13, E1, celda 30](fuentes/notebooks/evidencias/E1_construccion_exploracion.ipynb) | 31 / `de117d38` | Generada y guardada por código de celda |
| `e2_zipf.png` | [14, E2, celda 15](fuentes/notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb) | 16 / `d27a1060` | Generada y guardada por código de celda |
| `e2_top_palabras_politicas.png` | [14, E2, celda 6](fuentes/notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb) | 7 / `b5b6dbde` | Generada y guardada por código de celda |
| `e2_perplejidad_tags.png` | [14, E2, celda 26](fuentes/notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb) | 27 / `58033b93` | Generada y guardada por código de celda |
| `e2_logodds_tags.png` | [14, E2, celda 23](fuentes/notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb) | 24 / `1c1c52ae` | Generada y guardada por código de celda |
| `e2_espectro.png` | [14, E2, celda 17](fuentes/notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb) | 18 / `2573313f` | Generada y guardada por código de celda |
| `e2_difusion_repeticion.png` | [14, E2, celda 20](fuentes/notebooks/evidencias/E2_estadistica_modelos_lenguaje.ipynb) | 21 / `b7cfbc65` | Generada y guardada por código de celda |
| `pos_global.png` | [15, E3, celda 3](fuentes/notebooks/evidencias/E3_morfosintaxis.ipynb) | 4 / `48319be1` | Generada y guardada por código de celda |
| `pos_tags.png` | [15, E3, celda 5](fuentes/notebooks/evidencias/E3_morfosintaxis.ipynb) | 6 / `77b710c3` | Generada y guardada por código de celda |
| `pos_decadas.png` | [15, E3, celda 5](fuentes/notebooks/evidencias/E3_morfosintaxis.ipynb) | 6 / `77b710c3` | Generada y guardada por código de celda |
| `distribuciones.png` | [16, E4, celda 3](fuentes/notebooks/evidencias/E4_sintaxis_dependencias.ipynb) | 4 / `e7a854fa` | Generada y guardada por código de celda |
| `comparacion_tags.png` | [16, E4, celda 5](fuentes/notebooks/evidencias/E4_sintaxis_dependencias.ipynb) | 6 / `6ae76f8f` | Generada y guardada por código de celda |
| `comparacion_decadas.png` | [16, E4, celda 5](fuentes/notebooks/evidencias/E4_sintaxis_dependencias.ipynb) | 6 / `6ae76f8f` | Generada y guardada por código de celda |
| `arbol_transitive.png` | [16, E4, celda 7](fuentes/notebooks/evidencias/E4_sintaxis_dependencias.ipynb) | 8 / `16aaaf6e` | Generada por pipeline; mostrada por Image en celda |
| `arbol_subordinate.png` | [16, E4, celda 7](fuentes/notebooks/evidencias/E4_sintaxis_dependencias.ipynb) | 8 / `16aaaf6e` | Generada por pipeline; mostrada por Image en celda |
| `arbol_fragment.png` | [16, E4, celda 7](fuentes/notebooks/evidencias/E4_sintaxis_dependencias.ipynb) | 8 / `16aaaf6e` | Generada por pipeline; mostrada por Image en celda |
| `arbol_coordination.png` | [16, E4, celda 7](fuentes/notebooks/evidencias/E4_sintaxis_dependencias.ipynb) | 8 / `16aaaf6e` | Generada por pipeline; mostrada por Image en celda |
| `pca_validation.png` | [17, E5, celda 5](fuentes/notebooks/evidencias/E5_semantica.ipynb) | 6 / `6d079148` | Generada por pipeline; mostrada por Image en celda |

La procedencia del árbol E4 reside además en e4_examples.json; la PCA E5 en e5_analysis.json. Para incluir otra figura deberá revisarse visualmente y añadir pie, universo, parámetros y límite. No se atribuye una imagen externa a una extracción del output si sólo se copió su PNG guardado.
