# E5 — protocolo de representaciones semánticas

Fecha: 2026-11-16. Protocolo ejecutado; cierre técnico/documental completado.
Resultados, revisión asistida y matriz de evidencia en
[E5_RESULTADOS.md](E5_RESULTADOS.md); revisión personal H12 pendiente.
El estado ejecutado y las limitaciones se registran en
[el handoff E5](handoff/E5_2026-11-16.md). Este protocolo no certifica resultados pendientes.

## Texto y separación de datos

Se reutilizan las 3 155 772 letras canónicas de `lyrics_full_v1`, sin ingesta,
detección de idioma o anotación nuevas. Los nombres `train-0000x-of-00010` son
shards de origen, **no** el split. Se consulta `lyrics_splits.parquet` por `lyrics_id`;
se comprueban unicidad, pertenencia y cobertura completa. No se modifica el split agrupado.

La primera representación usa `lyrics_analysis`, NFC, apóstrofo curvo → ASCII,
minúsculas y la expresión regular de palabras E1/E2: letras Unicode con apóstrofos
internos, sin números ni puntuación. El apóstrofo final no forma parte del token:
`ridin'` queda `ridin`. Se conservan negación y stopwords; no se fusionan lemas,
no se filtra por POS y no se corrige g-dropping automáticamente.

Esto es una decisión inicial de representación, **no una prohibición de corregir E3**.
Los casos de `'s`, `Yeah`, `ridin'` y adjunción siguen en su revisión asistida.
Pueden añadirse correcciones con procedencia en una capa separada; una regla general
necesita comprobar distintos contextos y registrar errores nuevos antes de aplicarla.
No se llama gold a los juicios del agente ni se reescribe la anotación original.
Una variante de lemas corregidos se compararía con esta baseline en validación.

Sólo train aporta frecuencias, DF, vocabulario, IDF, SGNS y LDA. Validación elige
candidatos; test queda reservado. Cachear palabras/metadatos o transformar test con
un modelo congelado no lo usa para ajustar ni evaluar. No se generan vecinos de test.

## Baseline y vocabulario

`DF >= 5`, `DF <= 0,8 * N_train`; máximo 100 000 términos por frecuencia de train,
con desempate alfabético. Los índices finales se ordenan alfabéticamente.
La cota de vocabulario controla RAM y coste; no recorta documentos del corpus.
Los términos excluidos se contabilizan como no cubiertos en la exportación.

`tf = 1 + ln(count)`; `idf = ln((1 + N_train)/(1 + DF)) + 1`;
normalización L2; similitud coseno. Se persisten índices, frecuencias, DF e IDF.
La recuperación inicial usa una semilla por tag observado en la muestra determinista
de validación, con al menos 20 tokens cubiertos, contra **todo train**.
Se retienen los diez mejores con desempate por ID, mediante matrices dispersas y
bloques lote × consultas; nunca se construye N × N. Vecinos sin juicios no son accuracy.

## Embeddings propios

Se adopta **Word2Vec/SGNS** como experimento inicial por su entrenamiento incremental
y coste medido en este equipo. No se adopta un encoder preentrenado como sustituto.
Dimensión 128 por presupuesto de CPU/RAM; tres épocas; candidatos de ventana máxima
5 y 10; ventana reducida aleatoriamente por Gensim; cinco negativos, distribución
unigrama^0,75, `sample=0.001`, `sg=1`, `hs=0`, semilla 42. El vocabulario es el de
train anterior, con sus frecuencias; `min_count=1` no reintroduce términos excluidos.

Se aprende una matriz objetivo (input, `wv.vectors`) y una de contexto
(`syn1neg`). El objetivo discrimina pares observados frente a negativos, sin softmax
completo. Se conservan ambas para diagnóstico; la representación de palabras usa
sólo la matriz objetivo. No son embeddings contextuales.

Se recorre todo train en cada época. No se unen letras distintas. Para evitar el
límite interno de longitud de Gensim, las letras largas se dividen en bloques de
hasta 1 000 palabras; hay ventanas entre versos, pero no entre esos bloques.
Esto puede perder contextos en sus fronteras y queda como limitación explícita.

Hash de inicialización SHA-256 estable. Un worker permite repetir el orden de
actualizaciones en el mismo entorno. Cuatro workers aceleran la corrida medida;
semilla fija no garantiza pesos idénticos con concurrencia. Todos los parámetros,
versiones, firmas de datos/código y workers forman parte de la configuración.

Para elegir ventana: mismos pares de validación dentro de ±5 posiciones,
máximo 100 000 pares de las letras de la muestra; mismos cinco negativos preextraídos
con semilla 42 y distribución aprendida de train. Se maximiza el objetivo SGNS medio.
Los negativos coincidentes con el contexto positivo se omiten. La selección es un
diagnóstico intrínseco; no es perplexity normalizada ni evaluación de recomendaciones.
El límite de pares puede concentrar este diagnóstico en las primeras letras de la
muestra ordenada: no se presenta como una medida de toda validación.

Una letra se representa sumando **palabras distintas** con sus pesos TF-IDF, y
normalizando L2. La frecuencia ya está en TF: no vuelve a multiplicarse.
OOV se omite; denominador/norma cero implica representación no disponible.
La exportación conserva `lyrics_id`, split, cobertura y versión de espacio.
El vínculo con `track_id` corresponde al catálogo verificado, todavía pendiente de audio.

## Tópicos

LDA recibe conteos, no TF-IDF, con el mismo vocabulario train acotado.
Candidatos K=20/40, priors simétricos (`alpha=eta=1/K`), inferencia variacional online,
una pasada sobre todo train, chunks de hasta 1 024 documentos no vacíos, 30 iteraciones,
`decay=0.5`, `offset=1`, semilla 42. Los vacíos no actualizan el modelo.
La primera pasada constituye una baseline; convergencia/calidad deben revisarse.
Conservar stopwords puede producir tópicos dominados por palabras funcionales: se
documentaría como fallo, no se ocultaría ni se bautizarían automáticamente como emociones.

K se selecciona provisionalmente por la cota variacional por palabra que devuelve
Gensim sobre la misma muestra de validación. Coherencia UMass y diversidad top-10
son diagnósticos complementarios. Se repite K seleccionado con semilla 43 y se emparejan
tópicos mediante asignación húngara que maximiza Jaccard de términos top-10.
La interpretación humana sigue pendiente; ni cota, coherencia ni estabilidad prueban
relevancia musical. No se ha decidido incorporar tópicos al ranking: requiere ablación
y juicios de validación del recomendador, independientes de estos diagnósticos.

## Muestras y espacio compartido

La muestra de figuras/diagnósticos contiene como máximo 2 000 letras de validación
con los menores SHA-256 de `lyrics_id`. Se publican sus IDs y la selección; no reemplaza
el entrenamiento completo. PCA de dos componentes (`svd_solver=full`, semilla 42)
se ajusta sólo a esos vectores para dibujar. Se conservan media, componentes y varianza
explicada. Proximidad o colores en 2D no prueban relevancia ni separación entre tags.

Se examinan `love`, `home`, `money`, `war` y `freedom`, si están en vocabulario:
vecinos estáticos y contextos observados ±5 palabras en esa muestra. Cada letra aporta
un vector de contexto TF-IDF agregado; se promedian con igual peso por letra dentro
de tag/década válida (1900–2022). Cada contraste informa letras, ocurrencias, palabras
vecinas y contextos con ID/posición. Mínimo descriptivo: diez letras y veinte ocurrencias;
grupos menores quedan como soporte insuficiente. Las comparaciones usan **el mismo
modelo SGNS**; no se comparan coordenadas de modelos independientes. El vector estático
de la palabra no cambia: cambian sus contextos observados. Año de fuente, mezcla de
artistas/tags y repetición son posibles confusores. No es prueba de cambio causal
de significado; un resultado nulo o insuficiente también debe conservarse.

## Operación y verificación

Un único escritor por run-id. Inicialmente se ejecutó un solo trabajo pesado;
el usuario autorizó después paralelizar E5 aprovechando recursos disponibles.
El coordinador `run_e5_models.py --parallel --workers 4` lanza tres subruns con
directorios y locks separados: SGNS ventana 5, SGNS ventana 10 y LDA. Cada candidato
SGNS usa cuatro workers y LDA un hilo BLAS. La exportación/análisis esperan a los
modelos seleccionados; no hay escritores concurrentes del mismo checkpoint.
Caché y conteos por
shard; modelos SGNS por época y LDA por shard; exportación por shard. Escrituras
atómicas y hashes de configuración/entradas/salidas. Interrupción dentro de una época
SGNS repite esa época; dentro de un shard LDA repite ese shard desde el modelo anterior.
Los checkpoints propios son pickles locales completos, incluida RNG; no cargar modelos
ajenos mediante ese mecanismo. Inferencia LDA usa semilla derivada del ID por letra
para que reanudar exportación no cambie resultados por saltar shards anteriores.

Las pruebas sintéticas comprueban aislamiento de splits, IDF, pooling, ceros/OOV,
recarga de SGNS/LDA, selección repetida y cobertura de exportación/recuperación.
Sus métricas no son resultados del corpus real. La ejecución real posterior se
verificó mediante `scripts/verify_e5_results.py`: hashes de las diez representaciones
y checkpoints, 3 155 772 IDs únicos, splits, cobertura, normas y tópicos finitos.
Salida: `reports/nlp/lyrics_full_v1/e5_verification.json`. Los resultados ejecutados
y cobertura E5-01…05 están en `E5_RESULTADOS.md` y el notebook E5. Esto no sustituye
juicios independientes sobre el recomendador ni la revisión personal del autor.
