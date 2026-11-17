"""Aplica la segunda entrega editorial sobre archivos autorizados.
Lee el resultado de revalidar_hallazgos.py; no recalcula corpus ni modelos.
"""
from pathlib import Path
import json, re, hashlib
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/articulo_nlp'
if (OUT/'fuentes_segunda_entrega.json').exists():
    raise SystemExit('Segunda entrega ya aplicada; este actualizador histórico no debe sobrescribir las correcciones finales. Usar finalizar_revision.py para comprobar el estado actual.')
def read(f):return (OUT/f).read_text(encoding='utf-8')
def write(f,s):(OUT/f).write_text(s.strip()+'\n',encoding='utf-8')
def replace(text,old,new):
    if new in text:return text
    if old in text:return text.replace(old,new)
    raise ValueError('No se encontró el pasaje esperado: '+old[:100])
v=json.loads(read('revalidacion_independiente.json'))
assert v['word_count']['delta']==180 and v['word_count']['documents_differing']==56
nb=v['notebooks']
refs={'E1':13,'E2':14,'E3':15,'E4':16,'E5':17}
def cite(ev,*indices):
    text='celda '+str(indices[0]) if len(indices)==1 else 'celdas '+', '.join(map(str,indices))
    return f"[{refs[ev]}, {ev}, {text}](../../{nb[ev]['path']})"

# Citas exactas a la evidencia; no se depende de fragmentos URL de Jupyter.
intro=read('02_INTRODUCCION.md')
intro=replace(intro,'cada nivel aporta información para interpretar los siguientes [1, 2].','cada nivel aporta información para interpretar los siguientes [1, 2]. La distinción entre difusión y repetición se examina en '+cite('E2',19,20)+'; los errores ilustrativos de anotación y segmentación, en '+cite('E3',9)+' y '+cite('E4',7)+'.')
intro=replace(intro,'no se restringe a las canciones con audio [2, 4].','no se restringe a las canciones con audio [2, 4]; '+cite('E1',6,14,22)+'.')
intro=replace(intro,'Una transformación de todas las particiones con parámetros ya fijados no equivale a ajustar con todas ellas [3, 5].','Una transformación de todas las particiones con parámetros ya fijados no equivale a ajustar con todas ellas [3, 5]; '+cite('E5',1,3)+'. Esta separación de ajuste se refiere a los modelos KenLM y E5; la anotación descriptiva con spaCy preentrenado utiliza un criterio de normalización gráfica derivado del léxico completo, como se precisa en §4.6.')
intro=replace(intro,'La demo musical adopta FMA Medium y conserva **886 grabaciones** con coincidencia exacta de título y artista normalizados, vinculadas a **850 localizadores Genius** y **849 letras canónicas** [2, 4].','Para la demo musical se adoptó FMA Medium. El reporte conservado de `lyrics_full_v1` registra **886 grabaciones** retenidas por coincidencia exacta de título y artista normalizados, vinculadas a **850 localizadores Genius** y **849 letras canónicas** [2, 4]. Son resultados de aquella ejecución: la auditoría actual no encontró la tabla `demo_links.parquet`, la selección original ni la carpeta de audio en las rutas documentadas de este equipo [18].')
intro=replace(intro,'El recuperador textual actual ordena vectores de letras por similitud coseno;','El recuperador textual actual ordena vectores de letras por similitud coseno ('+cite('E5',9)+');')
write('02_INTRODUCCION.md',intro)

corpus=read('04_CORPUS_Y_PREPARACION.md')
corpus=replace(corpus,'El corpus textual procede de una copia local de `theelderemo/genius-lyrics-cleaned`, distribuido mediante Hugging Face [7]. La corrida `lyrics_full_v1` leyó diez archivos Parquet y **3 179 588 registros**.','El corpus textual procesado procede del snapshot de `theelderemo/genius-lyrics-cleaned`, distribuido mediante Hugging Face [7]. El manifiesto y las salidas guardadas documentan que la corrida `lyrics_full_v1` leyó diez archivos Parquet y **3 179 588 registros** ('+cite('E1',3,6)+'). En este equipo se conserva el corpus procesado; `data/raw/genius/` sólo contiene `.gitkeep`, por lo que no se revalidó la entrada original desde sus Parquet. La suma de registros aceptados representados en el corpus y filas de exclusión reproduce el total declarado [18].')
corpus=replace(corpus,'ni un identificador único.','ni un identificador único, según el esquema de origen guardado en '+cite('E1',2,3)+'.')
corpus=replace(corpus,'sin exclusión automática. Cada registro conserva estado y motivo;','sin exclusión automática ('+cite('E1',5,6,7,8)+'). Cada registro conserva estado y motivo;')
corpus=replace(corpus,'mantiene el peso de las repeticiones transcritas en las frecuencias posteriores.','mantiene el peso de las repeticiones transcritas en las frecuencias posteriores ('+cite('E1',9)+'; '+cite('E2',19)+').')
corpus=replace(corpus,'Son herramientas existentes, no modelos de idioma entrenados por SONORA.','Son herramientas existentes, no modelos de idioma entrenados por SONORA ('+cite('E1',10,11)+').')
corpus=replace(corpus,'**Tabla 1. Flujo de selección de `lyrics_full_v1`. Las primeras cinco filas usan como universo los 3 179 588 registros de origen; la deduplicación opera sobre los 3 177 443 aceptados [4].**','**Tabla 1. Flujo de selección de `lyrics_full_v1`. Las primeras cinco filas usan como universo los 3 179 588 registros de origen; la deduplicación opera sobre los 3 177 443 aceptados [4].** Fuente: '+cite('E1',6,14)+'; revalidación de metadatos procesados y exclusiones [18].')
corpus=replace(corpus,'no permite estimar su prevalencia [11].','no permite estimar su prevalencia [11]; '+cite('E4',7,10)+'.')
corpus=replace(corpus,'La correspondencia con todas las filas de origen se mantiene separada [2, 10].','La correspondencia con todas las filas de origen se mantiene separada [2, 10]; '+cite('E1',13,14)+'. Los agregados por letra utilizan `tag`, `year`, título y artista del registro canónico seleccionado; conservar las correspondencias de origen no implica incorporar todas sus etiquetas en cada agregado.')
corpus=replace(corpus,'Agrupar antes del reparto reduce la presencia de versiones relacionadas en conjuntos distintos.','La agrupación utiliza los metadatos de todas las filas aceptadas, no únicamente los del primer registro canónico. Las conexiones son transitivas: un componente no tiene necesariamente un único artista o título. Agrupar antes del reparto reduce la presencia de versiones relacionadas en conjuntos distintos [10, código `lyrics_corpus.py`, función `_group_roots`].')
corpus=replace(corpus,'Los modelos aprenden vocabulario y parámetros con entrenamiento; validación selecciona configuraciones y prueba se reserva para evaluación final.','Los modelos KenLM de E2 y TF-IDF, SGNS y LDA de E5 aprenden vocabularios o parámetros con entrenamiento; validación selecciona configuraciones y prueba se reserva para evaluación final ('+cite('E2',24,25)+'; '+cite('E5',1,3,11)+'). Esta separación no implica que todo preprocesamiento se haya fijado exclusivamente en entrenamiento: spaCy es preentrenado y el criterio descriptivo de g-dropping consulta el léxico completo.')
corpus=replace(corpus,'[PENDIENTE: incorporar una comprobación independiente del no solapamiento desde el Parquet para la auditoría final del artículo.]','La revalidación directa del Parquet encontró **3 155 772 `lyrics_id` únicos** y **cero grupos registrados presentes en más de una partición**; su SHA-256 coincide con el manifiesto. También se comprobó que cada ID del corpus aparece una vez en la tabla de particiones. Esto verifica la separación de los IDs y grupos registrados, sin demostrar ausencia de casi duplicados no detectados [18].')
corpus=replace(corpus,'Sus totales responden a unidades diferentes y no se suman ni comparan como si fueran la misma medición [2, 13].','Sus totales responden a unidades diferentes y no se suman ni comparan como si fueran la misma medición [2, 13]; '+cite('E1',15,16)+' y '+cite('E3',1,3)+'.')
corpus=replace(corpus,'Ambos totales corresponden al mismo conjunto documental, pero sus procedimientos difieren. [PENDIENTE: reconciliar los 180 tokens de diferencia con casos identificados; no se presupone su causa.]','La revalidación comparó por ID los conteos de los diez shards de metadatos: **56 letras** presentan diferencias, que suman exactamente **180 tokens**. Sólo se releyó el texto de esas letras. En ellas, convertir `İ` (U+0130) a minúsculas produce `i` seguida de la marca combinante U+0307; la expresión regular trata esa marca como separador y puede dividir una secuencia de letras. Ambos conteos guardados se reprodujeron exactamente. Como control, sustituir `İ` por `I` antes de convertir a minúsculas recuperó, en cada uno de los 56 casos, el conteo previo. Este control explica la diferencia de conteos en esta versión; no es una corrección aplicada al corpus, no demuestra igualdad de las secuencias de tokens ni determina el idioma de las letras [18].')
corpus=replace(corpus,'su total de 902 376 353 tokens [4, 13].','su total de 902 376 353 tokens [4, 13]; '+cite('E1',22)+' y '+cite('E2',3)+'.')
corpus=replace(corpus,'sin medir exactitud sintáctica ni justificar que todo cruce sea erróneo.','sin medir exactitud sintáctica ni justificar que todo cruce sea erróneo ('+cite('E1',19)+', código y tabla guardada; no se repitió la anotación de esa muestra).')
corpus=replace(corpus,'E5 utiliza formas superficiales y no depende de aceptar todos los lemas producidos por esa anotación [2, 3].','El umbral de veinte apariciones se calcula en el léxico completo; por tanto, esta anotación descriptiva depende también de datos ajenos a `train`. E5 utiliza formas superficiales, conserva stopwords y negación, y no utiliza lemas, etiquetas POS ni la expansión inferida de g-dropping [2, 3; código `semantics.py`, función `words`]. Esto evita atribuir a E5 aquella dependencia de la anotación; tampoco demuestra una evaluación de relevancia ('+cite('E1',15,17)+'; '+cite('E3',9)+'; '+cite('E5',3,9)+').')
corpus=replace(corpus,'como medidas marginales.','como medidas marginales ('+cite('E1',20,23)+').')
corpus=replace(corpus,'**Figura 1. Distribución acumulada de palabras por letra según el tag de origen, sobre las 3 155 772 letras canónicas de `lyrics_full_v1`.**','**Figura 1. Distribución acumulada de palabras por letra según el tag de origen, sobre las 3 155 772 letras canónicas de `lyrics_full_v1`.**')
corpus=replace(corpus,'Fuente: E1, celda 28, figura guardada `reports/figures/E1/e1_longitud_por_tag.png`, copiada sin modificación.','Fuente: '+cite('E1',28)+' (celda 29 contando desde uno; ID `6e450d0a`; ejecución guardada `In[19]`). Se copió sin modificación el PNG externo `reports/figures/E1/e1_longitud_por_tag.png` generado por esa celda; no se extrajo ni regeneró una imagen del output. SHA-256 de la copia y del original: `b66256898b22bf6d6d577dd545726e9d37c819c0a51348920c5f5da8ccbb565c`.')
corpus=replace(corpus,'Las medianas tabuladas en E1, celda 25, son','Las medianas tabuladas en '+cite('E1',25)+' y revalidadas desde `doc_stats` [18] son')
corpus=replace(corpus,'no reconstruyen fechas desconocidas [13].','no reconstruyen fechas desconocidas ('+cite('E1',24)+'). Los tamaños, las medianas y los conteos de años dudosos se revalidaron directamente desde las columnas procesadas [18].')
corpus=replace(corpus,'El reporte confirma **886 grabaciones retenidas**, **850 localizadores Genius** y **849 letras canónicas**; dos filas Genius comparten un texto deduplicado. Se verificó igualdad de título y artista normalizados en los 886 localizadores y todos enlazan con letras aceptadas.','El reporte conservado registra **886 grabaciones retenidas**, **850 localizadores Genius distintos** y **849 letras canónicas**; documenta dos filas Genius con un texto deduplicado. Su campo `demo.locator_check.title_artist_normalized_equal` registra **886 comprobaciones de vínculos**, no 886 localizadores distintos; `demo.lyrics_status.accepted` registra 886 grabaciones enlazadas con letras aceptadas. La igualdad de metadatos y la aceptación lingüística son comprobaciones diferentes: la bandera `has_lyrics` por sí sola no demuestra ambas [4, 10].')
corpus=replace(corpus,'En el mismo reporte, las 886 tienen archivo de audio local y ninguna es elegible aún para el catálogo combinado.','El mismo reporte registra históricamente 886 archivos de audio presentes y cero grabaciones elegibles para el catálogo combinado. La auditoría de este equipo no encontró `data/processed/demo/lyrics_full_v1/demo_links.parquet`, `medium_prioritarios.json` ni `data/raw/fma/fma_medium/` en sus rutas documentadas. Por tanto, aquellos conteos no acreditan presencia actual de audio ni permiten rehacer aquí la comprobación de vínculos [18]. [PENDIENTE: localizar o restaurar la tabla de vínculos y el audio antes de verificar el catálogo actual; no se realizó esa restauración para redactar.]')
write('04_CORPUS_Y_PREPARACION.md',corpus)

# Referencias uniformes; la cita inline aporta el localizador sin inventar un número de ejecución.
r=read('13_REFERENCIAS.md')
if '[14] SONORA.' not in r:
    r+='\n\n'+('\n\n'.join(f'[{refs[e]}] SONORA. *Evidencia {e[1:]} — {title}*. [Notebook {e}](../../{nb[e]["path"]}). Celdas e IDs exactos de esta versión en [00_CITAS_NOTEBOOKS.md](00_CITAS_NOTEBOOKS.md); SHA-256 en revalidacion_independiente.json. Fuente de evidencia guardada, no publicación metodológica.' for e,title in [('E2','Estadística del corpus y modelo de lenguaje de n-gramas'),('E3','Morfosintaxis'),('E4','Sintaxis y dependencias'),('E5','Semántica')]))
    r+='\n\n[18] SONORA, auditoría para el artículo. *Revalidación independiente de conteos, particiones y casos Unicode*, 16 de noviembre de 2026, hora local. [Procedimiento](revalidar_hallazgos.py) y [resultados](revalidacion_independiente.json). Lectura de metadatos de los diez shards; texto sólo en 56 letras discrepantes. Sin ejecución de pipelines ni cambios al corpus.\n'
r=replace(r,'Sistema único de citas numéricas [n], conservado en las secciones y en el integrado.','Sistema único de citas numéricas [n], conservado en las secciones y en el integrado. Enlaces como [13, E1, celda 22] añaden evidencia y localizador al número bibliográfico. Toda celda se numera desde cero; el ordinal desde uno, ID y contador de ejecución se distinguen en el mapa de citas.')
r=replace(r,'build_views/dedup_key/language_excerpt;','build_views/dedup_key/language_excerpt; [lyrics_corpus.py](../../packages/sonora/src/sonora/ingestion/lyrics_corpus.py), _group_roots y consolidación;')
write('13_REFERENCIAS.md',r)

# Catálogo de celdas estable para E1–E5.
cr=['# Citas a notebooks y convención de celdas','','Las citas inline usan el número bibliográfico, E1–E5 y el índice de celda base cero: incluye celdas Markdown y código. No es el contador `In[n]`. El ordinal base uno facilita encontrarla en visores que enumeran desde uno. El ID identifica esta celda en el snapshot; puede cambiar si el notebook se regenera. Los enlaces abren el archivo, sin prometer navegación a una celda que todos los visores soporten.','','| Evidencia | Referencia | Notebook | SHA-256 de la versión revisada |','|---|---|---|---|']
for e,a in nb.items():cr.append(f'| {e} | [{refs[e]}] | [{Path(a["path"]).name}](../../{a["path"]}) | `{a["sha256"]}` |')
cr+=['','## Localizadores de todas las celdas','','| Evidencia | Celda base cero | Ordinal base uno | ID de celda | Ejecución guardada | Tipo |','|---|---:|---:|---|---|---|']
for e,a in nb.items():
    for c in a['cells']:cr.append(f"| {e} | {c['index_zero_based']} | {c['ordinal_one_based']} | `{c['id']}` | {c['execution_count'] if c['execution_count'] is not None else '—'} | {c['type']} |")
cr+=['','Las citas acreditan lo que el notebook documenta o guarda; no garantizan actualidad por sí mismas. Los fact checks distinguen relectura de salidas, recálculo desde metadatos y límites sin resolver. Para una afirmación de demo sin celda que la respalde, se cita el reporte JSON; no se inventa una cita E1.']
write('00_CITAS_NOTEBOOKS.md','\n'.join(cr))

# Registro de la revisión cruzada con la sesión autorizada; no se trata como fuente primaria de resultados.
peer={'session_title':'Document SONORA project','session_id':'01a1e751-d65d-7ce1-bc85-282069bb1d6c','old_support_not_used':'Continue E5 work','purpose':'Crítica de evidencia y formulaciones; respuestas contrastadas con código/artefactos','rounds':[
{'round':1,'request':'Revisar cifras, actualidad, universos y referencias de Introducción/Corpus y R01–R19','response':'No hay evidencia independiente de demo ni MP3; 886/850/849 procede del reporte. KenLM en E2 c25, límites en c28. E5 c0/c5 limita muestra; closure local no resuelve alcance.','action':'Calificar evidencia histórica y no llamarla disponibilidad actual; mantener alcance E5 pendiente.'},
{'round':2,'request':'Buscar objeciones en reglas de grupos, metadatos canónicos, dependencia de g-dropping y política E5','response':'Acotar train-only a KenLM/E5; léxico de g-dropping completo; spaCy preentrenado. Union-find usa todas las filas aceptadas y transitividad. Metadatos agregados son los del canónico. 886 comprobaciones no son 886 localizadores distintos; has_lyrics sola no demuestra accepted. E5 conserva stopwords/superficie.','action':'Objeciones aceptadas y cotejadas con lyrics_corpus.py, annotate_corpus.py y semantics.py; correcciones en §§4.4–4.7.'},
{'round':3,'request':'Cuestionar la explicación Unicode y los límites del no solapamiento','response':'Control de conteos no prueba identidad de secuencias ni calidad; no contar 180 caracteres sin medición; no determinar idioma. Cero grupos solapados no elimina casi duplicados/covers; SHA no valida reglas.','action':'Texto limita conclusión a conteos de 56 casos y grupos registrados. No se corrige ni excluye ninguna letra.'},
{'round':4,'request':'Releer las formulaciones corregidas en §§4.5–4.7','response':'No se detecta inferencia material indebida. Sustituir uniforme por valor normalizado; corregir punto antes de La revalidación; §4.1 debe atribuir entrada a ejecución histórica. Revisión de formulaciones, sin repetir cálculos.','action':'Ajustes aplicados y revisada atribución histórica en §4.1.'}]}
write('revision_cruzada_sonora.json',json.dumps(peer,ensure_ascii=False,indent=2))

# Veredictos individuales de todos los resultados previamente publicados.
verdicts={
'R01':('Corroborado desde salidas procesadas; entrada original no disponible','3 177 443 registros representados + 2145 exclusiones/revisión = 3 179 588; data/raw/genius sin Parquet',cite('E1',3,6)),
'R02':('Revalidado desde metadatos','Suma n_source_records de canónicas = 3 177 443',cite('E1',6,14)),
'R03':('Revalidado desde metadatos e IDs','Diez shards: 3 155 772 filas; cobertura exacta una vez en split',cite('E1',14,22)),
'R04':('Revalidado; denominador aclarado','3 177 443 aceptados menos 3 155 772 canónicas = 21 671; denominador de duplicación: aceptados',cite('E1',14)),
'R05':('Revalidado desde exclusions.parquet','1914 review; 155 no inglés, 75 placeholders y 1 texto corto',cite('E1',6,11)),
'R06':('Reconciliado con casos; pendiente anterior resuelto','56 letras; diferencia +180. Control U+0130 antes de lower recupera conteo previo en cada caso','No figura la explicación de U+0130 en el notebook; fuente primaria del hallazgo nuevo: [18]'),
'R07':('Revalidado desde count y doc_stats','902 376 353 tokens; 1 277 145 filas/tipos del léxico',cite('E1',22)+'; '+cite('E2',3)),
'R08':('Revalidado directamente en el Parquet','3 145 790 grupos, máximo 24 letras; 0 multisbplit; 2 208 832/631 651/315 289 letras y 2 201 895/629 609/314 286 grupos; SHA coincide. No descarta duplicados no detectados',cite('E1',25)+'; asignación por grupos en manifiesto/código, no demostrada por esa celda sola'),
'R09':('Acotado a resultado histórico; actualidad no verificable','886 grabaciones, 850 localizadores y 849 letras en quality_report.demo; tablas/audio ausentes en rutas previstas','Sin celda E1–E5 que revalide demo; citar [4], claves demo, y [18]'),
'R10':('Revalidado desde metadatos canónicos','Cinco conteos coinciden; tag del primer canónico no representa todas las etiquetas originales',cite('E1',25)),
'R11':('Revalidado desde columnas numéricas','Medianas 242 palabras, 37 versos, 6 estrofas; marginales, no una canción típica íntegra',cite('E1',20,23)),
'R12':('Corroborado en output; no reanotado','Tabla 4746/3018 vs 16955/0 en muestra 400. No se repite spaCy; no mide precisión',cite('E1',19)),
'R13':('Revalidado desde year','1673 anteriores a 1900, 392 posteriores a 2022; no reconstruye fechas reales',cite('E1',24)),
'R14':('Corroborado entre reportes y notebook','Suma POS = 1 033 733 693; docs coincide con corpus. Anotaciones individuales no releídas; ejemplos de 3 letras',cite('E3',1,3,9)),
'R15':('Corroborado entre artefactos; no reparseado','Tokens E4 coinciden con E3; global_metrics guardadas, sin recalcular todos los arcos',cite('E4',1,5,7,9)),
'R16':('Corroborado entre manifiestos y notebook','counts y space_id iguales a auditoría E5; no se releen todos los vectores/modelos',cite('E5',1,3)),
'R17':('Muestra y pertenencia revalidadas; alcance completo pendiente','2000 IDs distintos, todos validation; PCA/contextos no son corpus completo',cite('E5',5,7)),
'R18':('Auditoría previa corroborada documentalmente','Valores de norma/cobertura guardados coinciden con notebook. No se repite validación de vectores',cite('E5',1)),
'R19':('Revalidado desde doc_stats por tag','204/408/187/284/215 palabras; sin significancia inferida',cite('E1',25,28))}
fc=['# Fact checks de los hallazgos publicados','','Revisión de todos los 19 registros iniciales y de sus interpretaciones. La revalidación propia no toma como confirmación independiente que la otra sesión repita el mismo reporte. Resultado computable: [revalidacion_independiente.json](revalidacion_independiente.json). Procedimiento de lectura: [revalidar_hallazgos.py](revalidar_hallazgos.py). Crítica cruzada: [revision_cruzada_sonora.json](revision_cruzada_sonora.json).','','| Hallazgo | Veredicto | Evidencia y límite | Cita notebook o fuente correcta |','|---|---|---|---|']
for k,(status,evidence,loc) in verdicts.items():fc.append(f'| {k} | {status} | {evidence} | {loc} |')
fc+=['','## Objeciones metodológicas y resolución','','| Formulación cuestionada | Resolución y fuente |','|---|---|',
'| Todo preprocesamiento se fijó en train | Se rechaza. KenLM/E5 ajustan con train; spaCy es preentrenado y el guard de g-dropping usa léxico completo (annotate_corpus.py y E1 c15/c17). E5 words excluye esa transformación. |',
'| Un grupo equivale a un artista/título único | Se rechaza. _group_roots usa todas las filas aceptadas; conexiones transitivas. |',
'| Duplicado exacto demuestra cover | Se rechaza. Hash sólo demuestra igualdad bajo su normalización, sin identificar la causa. |',
'| El corpus aceptado es enteramente monolingüe | Se rechaza. lang_status=en en todas las canónicas es una decisión automática; el pasaje incierto E4 c7 limita esa lectura. |',
'| 886 localizadores fueron comprobados | Se corrige: 886 vínculos sobre 850 localizadores distintos; aceptación de letras procede de demo.lyrics_status. |',
'| Existen 886 audios en este equipo | Se retira como afirmación actual. Lo registra un reporte histórico; faltan rutas previstas y originales. |',
'| E5 técnico cerrado satisface todo alcance contextual | Se mantiene brecha: modelos/exportación completos, contextos sólo muestra 2000. |',
'| La diferencia de 180 implica 180 caracteres o error de idioma | Se rechaza. Es diferencia de tokens por interacción lower/regex en 56 letras; no identifica idioma ni recomienda limpieza. |',
'| Cero grupos solapados demuestra cero contaminación | Se rechaza. Sólo acredita separación de IDs/grupos registrados; no detecta covers modificados ni casi duplicados omitidos. |',
'| Una imagen copiada procede necesariamente del output binario | Se distingue: Figura 1 copiada del PNG externo, generado por E1 c28; igualdad comprobada con PNG externo, no con el render incrustado. |',
'| Que todos los tests pasen demuestra calidad lingüística | Se rechaza. Fixtures comprueban software; falta referencia humana para precisión y juicios para relevancia. |',
'','La relectura de reportes/modelos no valida todos los hallazgos lingüísticos de E1–E5. Las secciones aún no redactadas tendrán su propia auditoría antes de incluir cifras o interpretaciones. No se declara una validación humana ni un cierre global del artículo.']
write('00_FACT_CHECKS.md','\n'.join(fc))

rr=json.loads(read('resultados_verificados.json'))
for rec in rr['records']:
    a,b,c=verdicts[rec['id']]
    rec['revalidation_status']=a;rec['revalidation_evidence']=b;rec['notebook_locator']=c
    if rec['id']=='R04':rec['denominator']=3177443
    if rec['id']=='R06':rec['limitations']='Diferencia de +180 reconciliada en 56 letras; control mecánico no demuestra calidad lingüística ni identidad de secuencias.'
    if rec['id']=='R08':rec['limitations']='No hay solapamiento de grupos registrados; no se descartan casi duplicados no detectados.'
    if rec['id']=='R09':rec['universe']='Demo histórica de lyrics_full_v1: 886 grabaciones; archivos fuente/demo/audio no presentes en rutas previstas del equipo actual';rec['limitations']='Cifras históricas del reporte, no catálogo local revalidado.'
rr['revalidated_utc']=v['captured_utc']
write('resultados_verificados.json',json.dumps(rr,ensure_ascii=False,indent=2))
register=['# Registro de resultados — segunda entrega','','Verificación original y revalidación se distinguen por resultado. Índices base cero; [convención e IDs](00_CITAS_NOTEBOOKS.md). Valores/configuraciones completos: [resultados_verificados.json](resultados_verificados.json). Evaluación crítica individual: [00_FACT_CHECKS.md](00_FACT_CHECKS.md).','','| ID | Fuente y localizador | Valor y unidad | Universo / denominador | Estado actualizado y límite |','|---|---|---|---|---|']
for rec in rr['records']:
    val=json.dumps(rec['value'],ensure_ascii=False)
    if len(val)>210:val='Ver detalle estructurado, '+rec['id']
    register.append(f"| {rec['id']} | `{rec['source']}` · `{rec['location']}` | {val}; {rec['unit']} | {rec['universe']}; denominador {rec['denominator']} | {rec['revalidation_status']}. {rec['limitations']} {rec['notebook_locator']} |")
register+=['','Todos estos registros proceden de datos reales; no se incorporan métricas de fixtures. Los denominadores de cada porcentaje específico se explicarán al redactar su sección. Ninguna celda se ejecutó para esta revisión; sólo se realizaron los cálculos acotados del procedimiento enlazado.']
write('00_REGISTRO_RESULTADOS.md','\n'.join(register))

# Vincular cada figura externa al notebook y celda exacta, incluso si no se publica aún.
fm={
'e1_longitud_letras.png':('E1',27),'e1_longitud_por_tag.png':('E1',28),'e1_letras_por_decada.png':('E1',29),'e1_repeticion_por_tag.png':('E1',30),
'e2_zipf.png':('E2',15),'e2_top_palabras_politicas.png':('E2',6),'e2_perplejidad_tags.png':('E2',26),'e2_logodds_tags.png':('E2',23),'e2_espectro.png':('E2',17),'e2_difusion_repeticion.png':('E2',20),
'pos_global.png':('E3',3),'pos_tags.png':('E3',5),'pos_decadas.png':('E3',5),
'distribuciones.png':('E4',3),'comparacion_tags.png':('E4',5),'comparacion_decadas.png':('E4',5),'arbol_transitive.png':('E4',7),'arbol_subordinate.png':('E4',7),'arbol_fragment.png':('E4',7),'arbol_coordination.png':('E4',7),'pca_validation.png':('E5',5)}
inv=read('00_INVENTARIO_FIGURAS.md')
inv=inv.split('\n## Procedencia precisa por notebook')[0]
inv+='\n\n## Procedencia precisa por notebook\n\nÍndices base cero; ordinal desde uno e ID se dan para desambiguar. «Generada» identifica código de gráfica; «mostrada» identifica una imagen preexistente que el notebook carga. Sólo Figura 1 se incluye en el artículo actual.\n\n| Imagen | Notebook y celda | Ordinal / ID | Relación con el notebook |\n|---|---|---|---|\n'
for name,(e,i) in fm.items():
    cell=nb[e]['cells'][i]
    mode='Generada por pipeline; mostrada por Image en celda' if e=='E5' or name.startswith('arbol_') else 'Generada y guardada por código de celda'
    inv+=f"| `{name}` | {cite(e,i)} | {i+1} / `{cell['id']}` | {mode} |\n"
inv+='\nLa procedencia del árbol E4 reside además en e4_examples.json; la PCA E5 en e5_analysis.json. Para incluir otra figura deberá revisarse visualmente y añadir pie, universo, parámetros y límite. No se atribuye una imagen externa a una extracción del output si sólo se copió su PNG guardado.\n'
write('00_INVENTARIO_FIGURAS.md',inv)

state=read('00_ESTADO_ARTICULO.md')
state=state.split('\n## Segunda entrega: revisión crítica con SONORA')[0]
state=re.sub(r'1\. R06 frente a R07:.*?(?=\n2\.)','1. R06 frente a R07: diferencia de 180 tokens RESUELTA mediante metadatos de todos los shards y recálculo de sólo 56 letras discrepantes. La expansión U+0130 al aplicar lower introduce una marca combinante que separa tokens regex; el control por sustitución recupera todos los conteos previos. Ver revalidacion_independiente.json, word_count; no se modificaron textos ni se infiere idioma.',state,flags=re.S)
state=replace(state,'6. 886 pistas / 850 localizadores / 849 letras no se contradicen: son grabaciones, filas de fuente y textos canónicos. catalog_eligible=0 en quality_report; no equivale a catálogo reproducible musicalmente.','6. 886 pistas / 850 localizadores / 849 letras son unidades diferentes y resultados históricos del reporte. El equipo actual no contiene demo_links, medium_prioritarios ni audio en las rutas documentadas; data/raw/genius sólo contiene .gitkeep. No se acredita disponibilidad actual de originales ni de demo. catalog_eligible=0 es estado del reporte histórico.')
state+='\n\n## Segunda entrega: revisión crítica con SONORA\n\nSe utilizó exclusivamente la sesión de apoyo **Document SONORA project** (`01a1e751-d65d-7ce1-bc85-282069bb1d6c`), con tres rondas documentadas. Se revisaron individualmente R01–R19 y once objeciones metodológicas. [Fact checks](00_FACT_CHECKS.md) y [registro del intercambio](revision_cruzada_sonora.json). Las respuestas se contrastaron con código y artefactos; repetir un reporte entre sesiones no se contó como revalidación independiente.\n\nLa revalidación propia confirmó IDs, grupos, conteos de particiones, ausencia de solapamiento de grupos registrados, exclusiones, tamaños por tag, medianas y años dudosos. La diferencia de 180 tokens quedó explicada en 56 letras. El tiempo y el procedimiento están en revalidacion_independiente.json. No se ejecutaron pipelines, notebooks ni entrenamiento. Se corrigieron la actualidad de demo/audio, la confusión entre 886 comprobaciones y 850 localizadores, la generalización train-only y el alcance de metadatos canónicos.\n\nLas citas inline distinguen E1–E5 y celda base cero. 00_CITAS_NOTEBOOKS.md conserva ordinal, ID y ejecución. Todas las figuras candidatas tienen notebook/celda de generación o visualización; Figura 1 mantiene origen externo y hash. Resumen/conclusiones y secciones siguientes siguen pendientes. El constructor histórico construir_entrega.py se bloqueó para evitar que sobrescriba estas correcciones; esta revisión se aplica con actualizar_revalidacion.py.\n'
write('00_ESTADO_ARTICULO.md',state)
mapping=read('00_MAPA_EVIDENCIAS.md')
mapping=mapping.split('\nSegunda entrega: [citas exactas E1–E5]')[0]
mapping=replace(mapping,'reporte corroborado, no recorrido independiente nuevo','Parquet revalidado directamente: 0 grupos multisbplit, IDs únicos y cobertura exacta')
mapping+='\n\nSegunda entrega: [citas exactas E1–E5](00_CITAS_NOTEBOOKS.md), [fact checks individuales](00_FACT_CHECKS.md) y [revalidación propia](revalidacion_independiente.json). Reglas train-only limitadas a ajuste KenLM/E5; anotación g-dropping usa léxico completo. Los datos originales Genius/demo/audio no están presentes en sus rutas previstas, aunque existen manifiestos y resultados históricos.\n'
write('00_MAPA_EVIDENCIAS.md',mapping)
idx=read('INDICE.md')
idx=idx.split('\n- [Fact checks por hallazgo]')[0]
idx=replace(idx,'**Borrador parcial: primera entrega.**','**Borrador parcial: segunda entrega, hallazgos revalidados y citas por celda.**')
idx=replace(idx,'Primera versión; pendientes idioma, procedencia y reconciliación','Revalidada; 180 tokens reconciliados; pendientes idioma/procedencia/demo actual')
idx+='\n\n- [Fact checks por hallazgo](00_FACT_CHECKS.md)\n- [Citas a E1–E5 e identificadores de celda](00_CITAS_NOTEBOOKS.md)\n- [Revalidación independiente](revalidacion_independiente.json)\n- [Revisión cruzada con SONORA](revision_cruzada_sonora.json)\n'
write('INDICE.md',idx)
# Ajustes finales surgidos de la cuarta lectura cruzada; el hash queda en controles.
corpus=read('04_CORPUS_Y_PREPARACION.md')
corpus=corpus.replace('y se transforma en un valor uniforme del intervalo [0,1).','y se transforma en un valor normalizado del intervalo [0,1).')
corpus=corpus.replace('El procedimiento de asignación mantiene los grupos juntos; La revalidación','El procedimiento de asignación mantiene los grupos juntos. La revalidación')
corpus=corpus.replace('Sus campos son `title`, `artist`, `tag`, `year` y `lyrics`;','El esquema de entrada documentado contiene `title`, `artist`, `tag`, `year` y `lyrics`;')
corpus=corpus.replace('La identidad de los Parquet locales queda registrada mediante hashes SHA-256, huellas del contenido de cada archivo.','La identidad de los Parquet de aquella ejecución quedó registrada mediante hashes SHA-256, huellas del contenido de cada archivo.')
corpus=corpus.replace('SHA-256 de la copia y del original: `b66256898b22bf6d6d577dd545726e9d37c819c0a51348920c5f5da8ccbb565c`.','El hash de copia y original se conserva en el inventario y en la verificación de esta entrega.')
corpus=corpus.replace('máximo de **24 letras**.','máximo de **24 letras**, revalidados desde las particiones [18].')
corpus=corpus.replace('componentes [5].**','componentes [5].** Revalidación directa de letras y grupos por partición [18]; '+cite('E1',25)+' presenta los conteos documentales por split.')
write('04_CORPUS_Y_PREPARACION.md',corpus)
state=read('00_ESTADO_ARTICULO.md').replace('con tres rondas documentadas','con cuatro rondas documentadas')
write('00_ESTADO_ARTICULO.md',state)
inv=read('00_INVENTARIO_FIGURAS.md')
inv=inv.replace('Evolución descriptiva POS por década y tag','Evolución descriptiva global de seis POS por década; no desagregada por tag en la figura')
inv=inv.replace('Métricas sintácticas por década y tag','Métricas sintácticas globales por década; no desagregadas por tag en la figura')
write('00_INVENTARIO_FIGURAS.md',inv)
parts=['# Estructura lingüística y representaciones textuales para la recuperación de canciones en SONORA','','**Título provisional. Borrador parcial — segunda entrega.** Introducción y Corpus revisados críticamente, con citas a notebooks y celdas. No acredita cierre de las cinco evidencias. Autoría y afiliación: [PENDIENTE: incorporar sólo datos confirmados]. [Índice](INDICE.md) · [Fact checks](00_FACT_CHECKS.md). Los índices de celda de las citas empiezan en cero; no son contadores de ejecución.','']
for f in ['02_INTRODUCCION.md','04_CORPUS_Y_PREPARACION.md','13_REFERENCIAS.md']:parts.append(read(f))
write('ARTICULO_COMPLETO.md','\n\n'.join(parts))

# Verificación de enlaces y correspondencia exacta del integrado; no audita contenido lingüístico.
broken=[]
for p in OUT.glob('*.md'):
    if p.name=='LECTURA_NOTEBOOKS.md':continue
    for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if target.startswith(('http:','https:','#')):continue
        if not (p.parent/target.split('#')[0]).exists():broken.append([p.name,target])
assert not broken, broken
integrated=read('ARTICULO_COMPLETO.md')
assert all(read(f).strip() in integrated for f in ['02_INTRODUCCION.md','04_CORPUS_Y_PREPARACION.md','13_REFERENCIAS.md'])
assert len(verdicts)==len(rr['records'])==19
image=OUT/'figuras/e1_longitud_por_tag.png'
assert image.read_bytes()==(ROOT/'reports/figures/E1'/image.name).read_bytes()
verification={'verified_utc':datetime.now(timezone.utc).isoformat(),'records_reviewed':19,'methodological_objections':11,'peer_rounds':4,'notebooks_cited':list(nb),'broken_local_links':broken,'integrated_matches_sections':True,'figure_external_copy_identical':True,'figure_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'notebook_cells_zero_based':True,'raw_inputs_currently_absent':True,'limits':'Revisión humana de idioma/anotación/relevancia pendiente; no se revalidaron todos los vectores ni todos los parses.'}
write('verificacion_segunda_entrega.json',json.dumps(verification,ensure_ascii=False,indent=2))
print(json.dumps(verification,ensure_ascii=False,indent=2))
