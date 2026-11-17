"""Auditoría de lectura e integración del borrador; no ejecuta notebooks ni modelos.
Ejecutar desde B:/SONORA: .venv/Scripts/python.exe reports/articulo_nlp/construir_entrega.py
Sólo escribe dentro de reports/articulo_nlp/. Bibliotecas: estándar de Python.
"""
from pathlib import Path
import json, hashlib, re, shutil
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/articulo_nlp'
OUT.mkdir(parents=True, exist_ok=True)
def read(p): return (ROOT/p).read_text(encoding='utf-8')
def js(p): return json.loads(read(p))
def write(p,s): (OUT/p).write_text(s.strip()+'\n',encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
now = datetime.now(timezone.utc).isoformat()

# Controles primero; se completan antes de la redacción.
for f in ['00_ESTADO_ARTICULO.md','00_MAPA_EVIDENCIAS.md','00_INVENTARIO_FIGURAS.md','00_REGISTRO_RESULTADOS.md']:
    if not (OUT/f).exists(): write(f, '# Auditoría inicial\n\nEn elaboración; no es un resultado científico.')

qpath='reports/corpus/lyrics_full_v1/quality_report.json'
q=js(qpath); spath='manifests/splits/lyrics_full_v1.json'; s=js(spath)
mpath='manifests/nlp/lyrics_full_v1.json'; m=js(mpath)
rpath='manifests/runs/lyrics_full_v1.json'; run=js(rpath)
assert q['reconciled'] and run['complete_full_corpus_run']
assert sum(q['status_counts'].values())==q['source_records_read']
assert q['accepted_source_records']-q['accepted_duplicate_source_records']==q['canonical_lyrics']
assert sum(v['lyrics'] for v in s['by_split'].values())==q['canonical_lyrics']
assert q['split']==s
assert sum(q['canonical_tag_counts'].values())==q['canonical_lyrics']

audit=[]; figures=[]; full=[]
for p in sorted((ROOT/'notebooks').rglob('*.ipynb')):
    n=json.loads(p.read_text(encoding='utf-8')); cells=[]; executions=[]
    full.append('\n# '+p.relative_to(ROOT).as_posix())
    for i,c in enumerate(n['cells']):
        source=''.join(c.get('source',[])); outputs=[]
        full.append(f'\n## Celda {i} ({c["cell_type"]}; ejecución {c.get("execution_count")})\n\n'+source)
        for oi,o in enumerate(c.get('outputs',[])):
            data=o.get('data',{})
            text=''.join(o.get('text',[]))
            if o.get('output_type')=='error': text=json.dumps(o,ensure_ascii=False)
            for kind in ['text/markdown','text/plain','text/html']:
                if kind in data:
                    value=data[kind]; text+='\n'+(''.join(value) if isinstance(value,list) else value)
            outputs.append({'type':o.get('output_type'),'mime':list(data),'text':text})
            full.append('\nSalida textual:\n'+text)
            if 'image/png' in data:
                figures.append({'notebook':p.relative_to(ROOT).as_posix(),'cell_zero_based':i,'output_zero_based':oi,'source':source,'image_sha256_encoded':hashlib.sha256(''.join(data['image/png']).encode()).hexdigest()})
        ec=c.get('execution_count')
        if c['cell_type']=='code' and ec is not None: executions.append(ec)
        cells.append({'index_zero_based':i,'type':c['cell_type'],'execution_count':ec,'source':source,'outputs':outputs})
    audit.append({'file':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'cells':cells,
                  'execution_counts':executions,'strictly_increasing':all(a<b for a,b in zip(executions,executions[1:])),
                  'errors':sum(o['type']=='error' for c in cells for o in c['outputs']),
                  'code_without_output':[c['index_zero_based'] for c in cells if c['type']=='code' and not c['outputs']]})
write('auditoria_notebooks.json',json.dumps({'captured_utc':now,'notebooks':audit},ensure_ascii=False,indent=2))
write('LECTURA_NOTEBOOKS.md','# Lectura documental de notebooks\n\nCopia de consulta de Markdown, código y outputs textuales; índices base cero. Las imágenes permanecen en sus fuentes. No se ejecutó ninguna celda.\n'+ '\n'.join(full))

# Inventario de fuentes y hashes pequeños. Los grandes corpus/modelos no se releen.
source_paths=set([qpath,spath,mpath,rpath,'CLAUDE.md','docs/REQUIREMENTS.md','docs/CORPUS_LETRAS.md','config/lyrics_corpus.yaml','config/nlp_annotation.yaml','config/ranking.yaml','config/sources.yaml','TODO-human.md'])
for base in ['docs/handoff','docs','reports/nlp/lyrics_full_v1','manifests/sources']:
    for p in (ROOT/base).rglob('*'):
        if p.is_file() and p.suffix in ['.md','.json']: source_paths.add(p.relative_to(ROOT).as_posix())
for a in audit: source_paths.add(a['file'])
for p in ['runtime/e5_status.json','artifacts/models/lyrics_full_v1/e5-surface-v2/trained.json','artifacts/models/lyrics_full_v1/e5-surface-v2/sgns_selection.json','artifacts/models/lyrics_full_v1/e5-surface-v2/lda/lda_selection.json','data/processed/nlp/lyrics_full_v1/semantics/e5-surface-v2/representations/complete.json','data/processed/nlp/lyrics_full_v1/semantics/e5-surface-v2/representations/config.json','packages/sonora/src/sonora/preprocessing/lyrics_text.py','packages/sonora/src/sonora/nlp/language.py','packages/sonora/src/sonora/nlp/lexicon.py','packages/sonora/src/sonora/recommendation/lyrics.py','apps/api/src/sonora_api/main.py']:
    if (ROOT/p).exists():source_paths.add(p)
sources=[{'path':p,'sha256':sha(ROOT/p),'bytes':(ROOT/p).stat().st_size} for p in sorted(source_paths)]
write('fuentes_auditadas.json',json.dumps({'captured_utc':now,'root':str(ROOT),'files':sources},ensure_ascii=False,indent=2))

records=[]
def result(code,path,key,value,unit,denominator,method,limit,universe='lyrics_full_v1; corpus real completo'):
    records.append(dict(id=code,source=path,location=key,value=value,unit=unit,denominator=denominator,universe=universe,origin='datos reales; no fixture',method=method,status='verificado documentalmente en artefacto guardado; sin repetir procesamiento',limitations=limit))
result('R01',qpath,'source_records_read',q['source_records_read'],'registros','10 Parquet','Ingesta lyrics-corpus-1.0.0','Snapshot remoto sin revisión; SHA-256 locales en manifiesto.')
for code,key in [('R02','accepted_source_records'),('R03','canonical_lyrics'),('R04','accepted_duplicate_source_records')]:
    result(code,qpath,key,q[key],'registros' if code!='R03' else 'letras',q['source_records_read'],'lyrics-views-v1; reglas de config/lyrics_corpus.yaml','Aceptación automática; no validación humana de todas las letras.')
result('R05',qpath,'exclusion_or_review_rule_counts',q['exclusion_or_review_rule_counts'],'registros por regla',q['source_records_read'],'Lingua 2.2.0; py3langid 0.4.0; mínimo 5 palabras','1914 en revisión no pertenecen al corpus aceptado.')
result('R06',qpath,'canonical_total_words',q['canonical_total_words'],'palabras regex antes de minúsculas',q['canonical_lyrics'],'preprocessing/lyrics_text.py: build_views','Difiere en 180 de regex-words-v1; causa exacta pendiente.')
result('R07',mpath,'lexicon.tokens / lexicon.types',{'tokens':m['lexicon']['tokens'],'types':m['lexicon']['types']},'tokens / tipos',q['canonical_lyrics'],'regex-words-v1; text.lower() antes de regex','No confundir con tokenización spaCy ni R06.')
result('R08',spath,'by_split / actual_fraction_lyrics / groups',{'counts':s['by_split'],'fractions':s['actual_fraction_lyrics'],'groups':s['groups']},'letras, grupos y fracciones',s['lyrics'],'SHA-256 de 42:group_id; umbrales 0,70 y 0,90','Fracciones en manifiesto redondeadas; no detección exhaustiva de casi duplicados.')
result('R09',qpath,'demo',q['demo'],'grabaciones / localizadores / letras',886,'Coincidencia normalizada título+artista; herencia de split','Existencia de audio no demuestra decodificación, licencia ni correspondencia auditiva. Estado de este reporte, no validación nueva.')
result('R10',qpath,'canonical_tag_counts',q['canonical_tag_counts'],'letras por tag',q['canonical_lyrics'],'Etiqueta de fuente de letra canónica','Tags no son géneros verificados; selección de registro canónico pierde multiplicidad de metadatos.')
result('R11',qpath,'canonical_n_words.p50 / canonical_n_lines.p50 / canonical_n_stanzas.p50',{'palabras':242,'versos':37,'estrofas':6},'medianas por letra',q['canonical_lyrics'],'lyrics-views-v1','Medianas marginales; no describen necesariamente una misma canción.')
e1='notebooks/evidencias/E1_construccion_exploracion.ipynb'
result('R12',e1,'cells[19].outputs: tabla default/lines',{'default_segments':4746,'default_crossing':3018,'forced_segments':16955,'forced_crossing':0},'segmentos',400,'spaCy en_core_web_sm, sin NER; batch 16; dos políticas','Muestra dirigida; cruzar versos no equivale por sí solo a error.',universe='Muestra real: primeras 400 letras del shard 5')
result('R13',e1,'cells[24].outputs: year',{'below_1900':1673,'above_2022':392},'letras con año dudoso',q['canonical_lyrics'],'Comparaciones del metadato year','No determina fecha verdadera ni motivo del error.')
for code,path,keys in [('R14','reports/nlp/lyrics_full_v1/e3_summary.json',['version','docs','tokens','sample_docs']),('R15','reports/nlp/lyrics_full_v1/e4_summary.json',['version','docs','global_metrics'])]:
    d=js(path);result(code,path,' / '.join(keys),{k:d[k] for k in keys},'conteos; ver campos',q['canonical_lyrics'],'spaCy 3.8.18; en_core_web_sm 3.8.0; spacy-lines-gdrop-v1','Agregados completos; ejemplos dirigidos y revisión humana pendientes; no precisión lingüística.')
ep='data/processed/nlp/lyrics_full_v1/semantics/e5-surface-v2/representations/complete.json'
result('R16',ep,'counts / space_id',js(ep),'documentos y tokens; identificador de espacio',q['canonical_lyrics'],'SGNS propio 128 dimensiones; 3 épocas; TF-IDF agregado, normalizado L2; LDA','Disponibilidad no mide calidad; transformar test no equivale a evaluarlo.')
ap='reports/nlp/lyrics_full_v1/e5_analysis.json'; ad=js(ap)
result('R17',ap,'scope / n_projected / projection',{'scope':ad['scope'],'n_projected':ad['n_projected'],'variance_ratio':ad['projection']['explained_variance_ratio']},'letras y fracciones de varianza',2000,'PCA 2 componentes; full SVD; seed 42','Proyección y contextos sobre muestra; falta análisis semántico contextual sobre todo el corpus pertinente.',universe='Muestra real de 2000 letras de validation; modelos ajustados con todo train')
vp='reports/nlp/lyrics_full_v1/e5_verification.json'; vd=js(vp)
result('R18',vp,'unique_ids / token_coverage_by_split / max_embedding_norm_error / max_topic_sum_error', {k:vd[k] for k in ['unique_ids','token_coverage_by_split','max_embedding_norm_error','max_topic_sum_error']},'IDs; fracciones; errores absolutos',q['canonical_lyrics'],'Auditoría guardada de representaciones y checkpoints; mismo space_id que R16','Es evidencia de la otra sesión, no auditoría repetida aquí; integridad numérica no equivale a calidad semántica.')
result('R19',e1,'cells[25].outputs: mediana palabras por tag',{'pop':204,'rap':408,'rock':187,'rb':284,'country':215},'palabras regex por letra; mediana',q['canonical_tag_counts'],'doc-stats-v1; agrupación por tag; universo completo','Medianas guardadas; no significancia ni etiquetas de género validadas.')
write('resultados_verificados.json',json.dumps({'captured_utc':now,'records':records},ensure_ascii=False,indent=2))
rows=['# Registro de resultados verificados','',f'Corte de lectura UTC: {now}. Índices de celdas base cero. Ver detalles íntegros de configuración, valores y límites en [resultados_verificados.json](resultados_verificados.json). Verificación documental y reconciliación aritmética pequeña; no se recalcularon los corpus ni se auditaron todos sus hashes.','', '| ID | Fuente y localizador | Valor / unidad | Universo y denominador | Método y límites |','|---|---|---|---|---|']
for r in records:
    val=json.dumps(r['value'],ensure_ascii=False)
    if len(val)>310:val='Detalle estructurado en resultados_verificados.json, '+r['id']
    rows.append(f"| {r['id']} | `{r['source']}` · `{r['location']}` | {val} ({r['unit']}) | {r['universe']}; denominador {r['denominator']} | {r['method']}. {r['limitations']} |")
rows+=['','Cada fila deriva de datos reales. Los ejemplos KenLM de E2 celda 27 son frases construidas manualmente, no citas del corpus. Las pruebas de tests/ usan fixtures sintéticos y se excluyen de resultados lingüísticos.','', 'Reconciliaciones realizadas: estados suman registros de origen; aceptados menos duplicados = letras canónicas; tags y particiones suman el corpus; split del quality_report coincide con manifests/splits. No se verificó nuevamente el no solapamiento recorriendo el Parquet: la asignación por grupos lo impone metodológicamente, pero falta comprobación independiente para el artículo.']
write('00_REGISTRO_RESULTADOS.md','\n'.join(rows))

write('00_MAPA_EVIDENCIAS.md', '''# Mapa de evidencias y secciones

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
''')

descriptions={
'e1_longitud_letras':('04','Histograma de palabras por letra; x logarítmico, y letras; 70 bordes logarítmicos','Corpus canónico completo; cola y mediana; no prueba normalidad'),
'e1_longitud_por_tag':('04','ECDF: x palabras por letra logarítmico; y proporción acumulada [0,1]; colores cinco tags; línea y=0,5','Corpus completo por tag; no prueba significancia ni género validado'),
'e1_letras_por_decada':('04','Barras: x década de year; y letras; años 1900–2022','Metadato de fuente; excluye años dudosos; décadas no equilibradas'),
'e1_repeticion_por_tag':('04/05','Distribución de proporción de versos repetidos; x [0,1]; series por tag','Corpus completo; depende del transcriptor; revisar unidades y barras antes de incluir'),
'e2_zipf':('05','Rango–frecuencia; ajustes logarítmicos Zipf y Mandelbrot','Uni/bi/trigramas completos; tramos de ajuste distintos; R² no prueba ley universal'),
'e2_top_palabras_politicas':('05','Ranking de frecuencias bajo tres políticas de filtrado','Corpus completo; lista de stopwords/vocablos modifica universo retenido'),
'e2_espectro':('05','Espectro V(m) por orden; frecuencias m≤200','Corpus completo; sólo intervalo visible, no toda la cola'),
'e2_difusion_repeticion':('05','x % letras con palabra; y ocurrencias por letra que la usa; escalas log; categorías','Palabras con ≥100000 ocurrencias, no todo vocabulario'),
'e2_logodds_tags':('05','Barras z de log-odds por tag contra resto; prior 10000; contenido ≥1000','Corpus completo; prior descriptivo; etiquetas y desbalance condicionan contraste'),
'e2_perplejidad_tags':('05/10','x tag; y perplejidad; curvas órdenes 2/3/4 KenLM','Ajuste train y evaluación validation con finales de verso; no relevancia'),
'pos_global':('06','Barras POS global; conteos y porcentajes en notebook','Tokens spaCy; especificar denominador al seleccionar'),
'pos_tags':('06','Mapa de calor POS por tag','Excluir PUNCT/SYM/SPACE según código; no exactitud de anotación'),
'pos_decadas':('06','Evolución descriptiva POS por década y tag','Años válidos; umbral de soporte; no causalidad'),
'distribuciones':('07','Histogramas de longitud sin puntuación y profundidad','Segmentos completos; truncamiento visual declarado; medias no truncadas'),
'comparacion_tags':('07','Métricas sintácticas por tag','Medias por segmento y por arco; no complejidad artística'),
'comparacion_decadas':('07','Métricas sintácticas por década y tag','Años válidos y composición variable; no seguimiento longitudinal'),
'pca_validation':('08','PCA: x componente 1, y componente 2; colores por tag; dos componentes','Muestra 2000 validation; 23,323 % y 9,852 % de varianza; no calidad semántica')}
figrows=['# Inventario de figuras','', 'Los assets de marca, portadas y fondos de apps/web son ilustraciones de interfaz, no evidencia científica. No se incorporan. No se crearon imágenes artificiales ni se regeneraron curvas. Sólo la ECDF E1 se incorpora en esta entrega; inspeccionada visualmente. Las demás son candidatas pendientes de lectura visual y cotejo específico de ejes antes de publicarse.','', '| Archivo (ruta desde raíz) | Sección | Representación, ejes y parámetros | Universo y límites |','|---|---|---|---|']
for p in sorted((ROOT/'reports/figures').rglob('*.png')):
    key=p.stem
    if key.startswith('arbol_'): desc=('07','Árbol cabeza→dependiente; etiquetas de dependencia, token, POS e índice; sin ejes numéricos','Cuatro casos dirigidos del shard 0; ver e4_examples.json; no precisión del parser')
    else:desc=descriptions.get(key,('pendiente','[PENDIENTE: inspeccionar ejes y unidades]','No incluir sin revisión'))
    figrows.append(f'| `{p.relative_to(ROOT).as_posix()}` | {desc[0]} | {desc[1]} | {desc[2]} |')
figrows+=['','## Imágenes incrustadas y procedencia de celdas','', 'Celdas base cero. El código íntegro de cada celda está en auditoria_notebooks.json y permite recuperar límites, leyenda y parámetros. No se presupone identidad binaria entre el PNG externo y el incrustado.']
for f in figures:figrows.append(f"- `{f['notebook']}`, celda {f['cell_zero_based']}, output {f['output_zero_based']}: PNG guardado; parámetros y fuente de datos en esa celda.")
figrows+=['','La copia seleccionada es figuras/e1_longitud_por_tag.png, procedente de reports/figures/E1/e1_longitud_por_tag.png; E1 celda 28. El hash de copia se registra en verificacion_entrega.json. La figura E5 procede de packages/sonora/src/sonora/nlp/semantic_analysis.py y e5_analysis.json, y también está incrustada en E5_semantica.ipynb, celda 5.']
write('00_INVENTARIO_FIGURAS.md','\n'.join(figrows))
(OUT/'figuras').mkdir(exist_ok=True)
shutil.copyfile(ROOT/'reports/figures/E1/e1_longitud_por_tag.png',OUT/'figuras/e1_longitud_por_tag.png')

write('00_ESTADO_ARTICULO.md','''# Estado del artículo — primera entrega incremental

Raíz comprobada: B:\\SONORA, Windows/PowerShell. Fecha local: 16 de noviembre de 2026; algunos artefactos llevan 17 de noviembre UTC. Escrituras limitadas a reports/articulo_nlp/. No se ejecutaron notebooks, entrenamientos, anotaciones ni pipelines. La terminal requirió escalación porque fallaba el inicio del aislamiento; la otra sesión se consultó y se canceló la solicitud delegada de escritura al recuperarse el acceso propio.

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

1. R06 frente a R07: preparación 902 376 173 palabras; léxico posterior 902 376 353 tokens (+180). El código de preparación aplica regex al texto sin lower y el léxico aplica lower antes de regex. Es una diferencia de procedimiento comprobada; NO se ha probado que explique los 180 casos. Se conservan ambas unidades. [PENDIENTE: reconciliación exacta por casos, sin corrida completa para redactar.]
2. E1 celda 22 rotula bytes UTF-8, pero suma n_chars_original. No usar 4 620 787 538 como bytes medidos. [PENDIENTE: reportar tamaño real sólo con medición válida.]
3. E1 celda 31 afirma que las letras multilingües quedan en revisión «por diseño». Los detectores sobre extractos no garantizan eso; E4 conserva un pasaje de idioma incierto en letra aceptada. Se redacta aceptación automática de inglés predominante, sin pureza monolingüe garantizada.
4. E1 celda 31 interpreta duplicación como covers y no scraping. Los hashes no distinguen esas causas; el artículo no adopta la generalización.
5. Handoff original y requisitos conservan pendientes históricos ya ejecutados: E2–E4 y ajuste E5. Se toma el artefacto actual por etapa; no se confunde requisito con resultado.
6. 886 pistas / 850 localizadores / 849 letras no se contradicen: son grabaciones, filas de fuente y textos canónicos. catalog_eligible=0 en quality_report; no equivale a catálogo reproducible musicalmente.
7. El snapshot remoto Genius carece de revisión registrada; hashes identifican la copia local, no reconstruyen por sí solos su descarga original. Etiqueta de licencia en una tarjeta no acredita derechos sobre todas las letras ni reproducción de audio.
8. docs/E5_RESULTADOS.md declara E5-04 completado como descripción, pero e5_analysis.json limita contextos a 2000 letras de validation. Se conserva ese avance sin equipararlo al análisis completo solicitado por el usuario. El cierre local declarado y el cierre de alcance del artículo son distintos; sigue pendiente ampliar o localizar evidencia contextual de cobertura completa.

## Pendientes de cierre

Auditoría humana de idioma (200 aceptados, 200 inciertos, 100 no ingleses), criterio docente de 150–300 páginas, lectura personal E3/E4/E5 y juicios de relevancia permanecen pendientes (TODO-human.md). No se aprueban en nombre del usuario. Faltan validación letra–grabación, decodificación/audio, licencias por pista y evaluación final de recomendación. No hay referencia humana para medir precisión POS/dependencias.

La auditoría inicial registra todos los notebooks localizados con celdas, código, salidas, errores y orden. La actualidad semántica de cada salida no queda certificada por tener contador creciente. Faltan el cotejo fino por sección y la revisión visual de las figuras candidatas distintas de la ECDF incluida. Fuentes de control pueden cambiar porque otra sesión avanza E5: fuentes_auditadas.json fija hashes y hora de lectura; revisar diferencias antes de la siguiente entrega.

## Siguiente acción

Redactar 05_ANALISIS_ESTADISTICO.md a partir de E2 y resultados KenLM existentes; comprobar tramos de Zipf, denominadores y afirmaciones contra sus tablas, sin repetir cálculo pesado. Después abordar E3, E4 y E5 con sus límites. Resumen y conclusiones definitivos se escribirán al estabilizar resultados y argumento. La versión integrada actual es un borrador parcial, no un artículo terminado.
''')

write('02_INTRODUCCION.md','''# 2. Introducción

Las letras de canciones ofrecen una vía para estudiar relaciones entre lenguaje y recuperación musical. Una búsqueda por título o artista localiza una entidad conocida, pero no describe las relaciones textuales que permiten explorar otras canciones. En SONORA, el problema de procesamiento de lenguaje natural (PLN), entendido como el análisis computacional del lenguaje, consiste en caracterizar un corpus de letras en inglés y examinar cómo distintas representaciones de ese contenido sustentan la recuperación de canciones. El resultado tangible previsto es un recomendador basado en contenido: una canción semilla se compara con otras mediante propiedades de sus letras y, en una etapa adicional, de su audio [1].

Este problema exige conectar la representación con las propiedades del material analizado. La frecuencia de una palabra depende tanto de su difusión entre canciones como de su repetición dentro de una letra. Los saltos de verso tampoco equivalen necesariamente a límites de oración. Asimismo, las contracciones y las grafías coloquiales afectan la tokenización, es decir, la división del texto en unidades analizables. El corpus y las anotaciones actuales permiten estudiar estos factores, aunque una anotación automática no constituye una interpretación lingüística validada. Por ello, la investigación integra construcción y exploración del corpus, estadística del lenguaje, análisis morfosintáctico, análisis sintáctico y representación semántica; cada nivel aporta información para interpretar los siguientes [1, 2].

Se conserva la pregunta principal ya adoptada por el proyecto: **¿qué diferencias aparecen en la recuperación de canciones relevantes al representar letras en inglés con TF-IDF, embeddings propios y distribuciones temáticas, y cómo se relacionan esas diferencias con la estructura lingüística del corpus?** [1]. TF-IDF pondera términos según su frecuencia en una letra y su presencia en los documentos de entrenamiento. Los embeddings son vectores aprendidos a partir de contextos de palabras; la implementación actual utiliza Word2Vec con muestreo negativo, SGNS. Las distribuciones temáticas se obtienen mediante LDA, un modelo probabilístico que representa cada documento como mezcla de tópicos y cada tópico como distribución de palabras. Estos métodos cumplen funciones distintas: compartir palabras, aproximar relaciones de contexto y describir temas no son operaciones equivalentes [3]. Su comparación debe distinguir cambios de vecinos recuperados de mejoras de relevancia juzgadas por personas.

El objetivo general es estudiar la relación entre estructura lingüística y recuperación basada en letras con evidencia reproducible. Para ello se documentan las decisiones de selección, limpieza y partición; se caracterizan vocabulario, frecuencias y secuencias de palabras; se examinan categorías gramaticales, lemas y dependencias; y se analizan las representaciones semánticas y sus resultados de recuperación. La evaluación integrada deberá contrastar los métodos con un protocolo de relevancia independiente de los puntajes internos. Las hipótesis de mayor recuperación semántica mediante embeddings o de valor adicional de los tópicos permanecen abiertas; una similitud alta no representa un porcentaje de gusto ni demuestra superioridad [1, 3].

El universo textual comprende **3 155 772 letras canónicas** aceptadas automáticamente como inglesas en la corrida `lyrics_full_v1`, obtenidas de diez Parquet de Genius; no se restringe a las canciones con audio [2, 4]. Los análisis descriptivos pueden utilizar el corpus completo. El ajuste de vocabularios y modelos se separa de esa descripción: entrenamiento utiliza `train`, selección utiliza `validation` y la evaluación final se reserva para `test`. Una transformación de todas las particiones con parámetros ya fijados no equivale a ajustar con todas ellas [3, 5].

La demo musical adopta FMA Medium y conserva **886 grabaciones** con coincidencia exacta de título y artista normalizados, vinculadas a **850 localizadores Genius** y **849 letras canónicas** [2, 4]. Esa correspondencia de metadatos no valida por sí sola el contenido de la letra ni la relación auditiva con cada grabación. El recuperador textual actual ordena vectores de letras por similitud coseno; la extracción acústica, la fusión de señales y la integración funcional deben documentarse según sus ejecuciones reales [6]. La combinación futura de letras y audio seguirá siendo recomendación basada en contenido mientras no utilice interacciones reales de usuarios. El objetivo central de este artículo es el estudio de PLN, con la recomendación como aplicación y la modalidad acústica como extensión condicionada a evidencia disponible.

Esta primera versión presenta la introducción y la preparación del corpus. [PENDIENTE: completar la comparación de relevancia entre representaciones y la evaluación final antes de responder definitivamente la pregunta de investigación.] Los resultados técnicos existentes permiten continuar la redacción de los análisis, pero no justifican anticipar una respuesta favorable a las hipótesis.
''')

write('04_CORPUS_Y_PREPARACION.md','''# 4. Corpus y preparación

## 4.1. Fuentes y unidades de análisis

El corpus textual procede de una copia local de `theelderemo/genius-lyrics-cleaned`, distribuido mediante Hugging Face [7]. La corrida `lyrics_full_v1` leyó diez archivos Parquet y **3 179 588 registros**. Sus campos son `title`, `artist`, `tag`, `year` y `lyrics`; no existe una columna de idioma ni un identificador único. Cada fila se localiza mediante el nombre del archivo y su posición global desde cero. Los nombres de archivo que empiezan por `train-` pertenecen a la distribución de origen y no identifican el conjunto de entrenamiento de SONORA [2, 4].

Una fila de origen, una letra y una grabación son unidades diferentes. Una letra canónica es un texto aceptado conservado una sola vez tras la deduplicación definida en §4.4. Puede corresponder a varias filas de origen y a varias grabaciones. La demo parte de FMA Medium, cuya documentación especifica 25 000 clips de 30 segundos [8]; esa fuente acústica no restringe la selección textual. La identidad de los Parquet locales queda registrada mediante hashes SHA-256, huellas del contenido de cada archivo. Sin embargo, no se registró la revisión remota de la descarga Genius: los hashes identifican el snapshot local y no resuelven esa omisión de procedencia [4, 9]. La tarjeta pública tampoco sustituye la revisión de condiciones aplicables a cada contenido.

## 4.2. Vistas textuales y limpieza

La preparación conserva tres vistas, versión `lyrics-views-v1` [2, 10]. La original retiene el texto leído. La estructural normaliza Unicode a NFC, homogeneiza saltos de línea, espacios y apóstrofos, y elimina artefactos de formato o extracción cuando coinciden con reglas explícitas, incluidos sufijos `Embed`, una línea de sugerencias y determinadas etiquetas HTML. NFC homogeneiza representaciones Unicode canónicamente equivalentes; no convierte automáticamente todas las grafías tipográficas o caracteres visualmente semejantes en una sola palabra.

La vista de análisis elimina anotaciones editoriales entre corchetes, como encabezados de sección, y utiliza los encabezados de línea como fronteras de estrofa. Conserva mayúsculas, puntuación, contracciones, negación y saltos de verso. No expande instrucciones como `[Chorus x2]` ni elimina los estribillos escritos varias veces. Esta decisión evita reconstruir contenido ausente, pero mantiene el peso de las repeticiones transcritas en las frecuencias posteriores. Por ello, frecuencia de uso y número de letras que contienen una palabra se distinguirán en el análisis estadístico.

Se excluyen textos vacíos, textos con menos de cinco palabras en la vista de análisis y ciertos marcadores de ausencia de letra de hasta treinta palabras. La longitud elevada y problemas como caracteres de reemplazo se registran como banderas, sin exclusión automática. Cada registro conserva estado y motivo; la eliminación del conjunto aceptado no equivale a borrar su trazabilidad [2, 4].

## 4.3. Identificación del idioma y resultados de selección

La identificación del idioma se aplica sobre extractos del inicio, centro y final de la vista de análisis, de hasta 800 caracteres por ventana. Así se reduce la dependencia de la introducción y de encabezados potencialmente ingleses. El detector primario es `lingua-language-detector` 2.2.0, en modo de alta precisión y con todos sus idiomas; `py3langid` 0.4.0 interviene cuando la decisión primaria no es concluyente [2, 10]. Son herramientas existentes, no modelos de idioma entrenados por SONORA.

La aceptación directa requiere inglés como primera opción, confianza de al menos 0,99 y veinte palabras o más. En los demás casos se requiere acuerdo de ambos detectores en inglés, con confianza secundaria de al menos 0,50. El acuerdo en otro idioma conduce a exclusión cuando el texto tiene al menos veinte palabras; los desacuerdos y otros casos no concluyentes quedan en revisión. Esas confianzas son puntajes de los detectores y no tasas de exactitud empíricas del corpus.

**Tabla 1. Flujo de selección de `lyrics_full_v1`. Las primeras cinco filas usan como universo los 3 179 588 registros de origen; la deduplicación opera sobre los 3 177 443 aceptados [4].**

| Etapa o motivo | Cantidad | Unidad |
|---|---:|---|
| Entrada leída | 3 179 588 | registros |
| Aceptados | 3 177 443 | registros |
| Idioma incierto, en revisión | 1 914 | registros |
| Excluidos por idioma no inglés | 155 | registros |
| Excluidos por marcador de ausencia / menos de cinco palabras | 75 / 1 | registros |
| Aceptados consolidados como duplicados exactos | 21 671 | registros |
| Corpus canónico resultante | 3 155 772 | letras |

Los estados aceptado, revisión y exclusión reconcilian la entrada. El conjunto canónico representa letras **aceptadas automáticamente como inglesas**, sin garantía de monolingüismo de cada pasaje. La anotación sintáctica posterior identificó un caso de idioma/contexto incierto dentro de una letra aceptada; no permite estimar su prevalencia [11]. La auditoría humana prevista contiene 200 aceptados, 200 inciertos y 100 no ingleses, con semilla 42, y permanece pendiente [4]. [PENDIENTE: revisar esa muestra y documentar errores del detector antes de informar una exactitud de idioma.]

## 4.4. Deduplicación, identidad y grupos relacionados

La clave de deduplicación se obtiene de la vista de análisis con `casefold` y espacios consecutivos colapsados; el hash SHA-256 de esa clave identifica el texto. `casefold` realiza una normalización de caja para comparar cadenas. El identificador `lyrics_id` conserva veinte dígitos hexadecimales del hash y el registro canónico es el primero en orden de archivo y fila. La correspondencia con todas las filas de origen se mantiene separada [2, 10]. Los **21 671 registros** consolidados no son necesariamente errores: el hash demuestra igualdad según la regla, pero no distingue por sí solo covers, reediciones y duplicación de extracción.

Antes de particionar se agrupan letras idénticas y letras con igual artista normalizado y título base, eliminando sufijos de versión documentados. Los componentes relacionados contienen **3 145 790 grupos**, con un máximo de **24 letras**. Agrupar antes del reparto reduce la presencia de versiones relacionadas en conjuntos distintos. La regla no detecta exhaustivamente casi duplicados ni covers con texto modificado y artista diferente, por lo que no demuestra ausencia total de contaminación entre particiones [5].

## 4.5. Particiones y separación entre descripción y ajuste

Se aplica SHA-256 a la cadena `42:<group_id>` y se transforma en un valor uniforme del intervalo [0,1). Los valores inferiores a 0,70 se asignan a entrenamiento; los comprendidos entre 0,70 y 0,90, a prueba; el resto, a validación. El grupo completo hereda una sola asignación. Como se distribuyen grupos de distinto tamaño, las fracciones documentales resultantes se aproximan al objetivo 70/20/10 [5].

**Tabla 2. Reparto producido por grupos. Porcentajes de letras calculados sobre 3 155 772 documentos, redondeados a dos decimales; grupos sobre 3 145 790 componentes [5].**

| Partición | Letras | % de letras | Grupos |
|---|---:|---:|---:|
| Entrenamiento (`train`) | 2 208 832 | 69,99 | 2 201 895 |
| Prueba (`test`) | 631 651 | 20,02 | 629 609 |
| Validación (`validation`) | 315 289 | 9,99 | 314 286 |

Los modelos aprenden vocabulario y parámetros con entrenamiento; validación selecciona configuraciones y prueba se reserva para evaluación final. En cambio, las distribuciones descriptivas del corpus pueden reunir las tres particiones, siempre que no se reutilicen para seleccionar modelos. E5 ya transformó todas las letras con un espacio fijado desde entrenamiento; disponer de vectores de prueba no significa haberlos utilizado para ajuste ni haber efectuado la evaluación final [3, 12]. El procedimiento de asignación mantiene los grupos juntos; [PENDIENTE: incorporar una comprobación independiente del no solapamiento desde el Parquet para la auditoría final del artículo.]

## 4.6. Tokenización, segmentación y primeras observaciones

Un token es una unidad obtenida por una regla de segmentación. Para estadística léxica, `regex-words-v1` aplica minúsculas y reconoce secuencias de letras Unicode con apóstrofos internos: `don't` constituye un token; dígitos y puntuación quedan fuera. Para categorías gramaticales, lemas y dependencias se utiliza spaCy 3.8.18 y el modelo preentrenado `en_core_web_sm` 3.8.0, que puede separar contracciones y contar puntuación. Sus totales responden a unidades diferentes y no se suman ni comparan como si fueran la misma medición [2, 13].

El léxico posterior registra **902 376 353 tokens y 1 277 145 tipos**, donde un tipo es una forma distinta. El reporte de preparación conserva **902 376 173 palabras** calculadas antes de la conversión a minúsculas. Ambos totales corresponden al mismo conjunto documental, pero sus procedimientos difieren. [PENDIENTE: reconciliar los 180 tokens de diferencia con casos identificados; no se presupone su causa.] En adelante, los análisis estadísticos que reutilicen el léxico deben indicar expresamente su total de 902 376 353 tokens [4, 13].

La segmentación sintáctica fuerza una frontera en cada salto de verso y permite divisiones adicionales del parser. Un parser predice relaciones gramaticales; una frontera forzada es una decisión de procesamiento, no una prueba de que el verso sea una oración completa. La comparación guardada en E1 utiliza una **muestra de las primeras 400 letras del shard 5**. Con segmentación predeterminada, 3 018 de 4 746 segmentos cruzaban al menos un salto; con fronteras forzadas se obtuvieron 16 955 segmentos y ninguno lo cruzaba. Esta comparación describe el efecto de la regla, sin medir exactitud sintáctica ni justificar que todo cruce sea erróneo. La regla puede fragmentar oraciones que continúan entre versos [13].

Para la morfosintaxis se aplica además una normalización de ciertas grafías con omisión de la `g` final, mediante un texto sombra que permite al modelo analizar una forma terminada en `-ing` y conserva la forma original. El criterio exige que la forma expandida aparezca al menos veinte veces en el léxico del corpus. Es un recurso descriptivo de anotación, no una mejora de precisión demostrada por una ablación. E5 utiliza formas superficiales y no depende de aceptar todos los lemas producidos por esa anotación [2, 3].

La mediana del corpus es **242 palabras, 37 versos y 6 estrofas por letra**, como medidas marginales. El campo `tag` contiene 1 336 051 letras `pop`, 959 763 `rap`, 621 148 `rock`, 153 552 `rb` y 85 258 `country`. Estas son etiquetas de fuente, no géneros musicalmente validados [4]. La figura 1 compara longitudes dentro de cada tag mediante una distribución acumulada: para cada longitud indica qué proporción de letras no la supera.

![Distribuciones acumuladas de longitud por tag](figuras/e1_longitud_por_tag.png)

**Figura 1. Distribución acumulada de palabras por letra según el tag de origen, sobre las 3 155 772 letras canónicas de `lyrics_full_v1`.** Eje horizontal logarítmico: palabras por letra; eje vertical: proporción acumulada dentro de cada tag. La leyenda informa los tamaños y la línea horizontal marca 0,5. Fuente: E1, celda 28, figura guardada `reports/figures/E1/e1_longitud_por_tag.png`, copiada sin modificación. Las medianas tabuladas en E1, celda 25, son 204 (`pop`), 408 (`rap`), 187 (`rock`), 284 (`rb`) y 215 (`country`) palabras. La separación describe longitudes y no significancia estadística ni propiedades causales de los géneros [13].

La curva de `rap` se desplaza hacia longitudes mayores; su mediana duplica la de `pop` en las tablas guardadas. Esto implica que los conteos agregados de tokens ponderan de forma distinta a los grupos, incluso antes de analizar contenido. Por tanto, las secciones posteriores distinguirán porcentajes por token, tamaños documentales y comparaciones dentro de tag. El campo `year` presenta 1 673 valores anteriores a 1900 y 392 posteriores a 2022, que se señalan como dudosos; las comparaciones temporales delimitan el intervalo válido y no reconstruyen fechas desconocidas [13].

## 4.7. Vínculos de la demo y límites de preparación

El reporte confirma **886 grabaciones retenidas**, **850 localizadores Genius** y **849 letras canónicas**; dos filas Genius comparten un texto deduplicado. Se verificó igualdad de título y artista normalizados en los 886 localizadores y todos enlazan con letras aceptadas. Las grabaciones heredan la partición textual: 575 de entrenamiento, 210 de prueba y 101 de validación. Esos conteos se refieren a grabaciones, no al reparto global de letras [4].

En el mismo reporte, las 886 tienen archivo de audio local y ninguna es elegible aún para el catálogo combinado. Un archivo existente no acredita decodificación correcta, correspondencia auditiva, letra revisada o autorización de reproducción. Por eso estas coincidencias no se describen como 886 canciones multimodales validadas. La preparación del corpus textual sí está completa según sus reglas automáticas; la validación humana del idioma, el criterio docente de extensión de 150–300 páginas y la validación del catálogo musical permanecen pendientes [2, 4]. Estas limitaciones acompañan el análisis sin reducir su universo al subconjunto con audio.
''')

write('13_REFERENCIAS.md','''# 13. Referencias verificadas de esta entrega

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
''')

states=[('01_RESUMEN.md','Título provisional; resumen definitivo al final'),('02_INTRODUCCION.md','Primera versión sustentada; evaluación principal pendiente'),('03_FUNDAMENTOS_Y_TRABAJOS_RELACIONADOS.md','Por redactar; publicaciones primarias por verificar'),('04_CORPUS_Y_PREPARACION.md','Primera versión; pendientes idioma, procedencia y reconciliación'),('05_ANALISIS_ESTADISTICO.md','Siguiente sección; E2 con resultados disponibles'),('06_ANALISIS_MORFOSINTACTICO.md','Por redactar; agregados completos, revisión personal pendiente'),('07_ANALISIS_SINTACTICO.md','Por redactar; agregados completos, revisión personal pendiente'),('08_REPRESENTACION_SEMANTICA.md','Por redactar; modelos/exportación completos, análisis contextual sólo muestra'),('09_SISTEMA_DE_RECOMENDACION.md','Por redactar; recuperación textual, audio/fusión pendientes'),('10_EVALUACION_Y_RESULTADOS_INTEGRADOS.md','Por redactar; falta evaluación de relevancia y test final'),('11_DISCUSION_Y_LIMITACIONES.md','Por redactar; límites ya registrados en controles'),('12_CONCLUSIONES.md','Definitivas al final'),('13_REFERENCIAS.md','Fuentes de esta entrega; antecedentes metodológicos pendientes'),('14_ANEXOS.md','Según necesidad; trazabilidad actual en controles')]
idx=['# Índice del artículo SONORA','','**Borrador parcial: primera entrega.** [Artículo integrado](ARTICULO_COMPLETO.md). Sólo se enlazan secciones existentes para evitar enlaces vacíos. Título provisional: *Estructura lingüística y representaciones textuales para la recuperación de canciones en SONORA*. Autoría y afiliación pendientes de información confirmada.','','| Sección prevista | Estado |','|---|---|']
for f,state in states:idx.append(f'| '+(f'[{f}]({f})' if (OUT/f).exists() else f'`{f}`')+f' | {state} |')
idx+=['','## Controles y trazabilidad','', '- [Estado y pendientes](00_ESTADO_ARTICULO.md)','- [Mapa de evidencias](00_MAPA_EVIDENCIAS.md)','- [Inventario de figuras](00_INVENTARIO_FIGURAS.md)','- [Registro de resultados](00_REGISTRO_RESULTADOS.md)','- [Auditoría documental de notebooks](auditoria_notebooks.json)','- [Procedimiento de esta entrega](construir_entrega.py)','', 'Los archivos previstos sin texto no se crean como secciones vacías. Resumen y conclusiones no se presentan como definitivos.']
write('INDICE.md','\n'.join(idx))
parts=['# Estructura lingüística y representaciones textuales para la recuperación de canciones en SONORA','', '**Título provisional. Borrador parcial — primera entrega.** Incluye Introducción, Corpus y referencias disponibles. No constituye la versión final ni acredita cierre de las cinco evidencias. Autoría y afiliación: [PENDIENTE: incorporar sólo datos confirmados]. [Índice y estado de todas las secciones](INDICE.md).','']
for f in ['02_INTRODUCCION.md','04_CORPUS_Y_PREPARACION.md','13_REFERENCIAS.md']:
    parts.extend([(OUT/f).read_text(encoding='utf-8'),''])
write('ARTICULO_COMPLETO.md','\n'.join(parts))
checks={'captured_utc':now,'notebooks':[{k:a[k] for k in ['file','sha256','execution_counts','strictly_increasing','errors','code_without_output']} for a in audit], 'embedded_png_count':len(figures),'results_records':len(records),'reconciliation_checks_passed':True,'small_source_hashes_computed_not_raw_corpus':True,'figure_copy_equal':sha(OUT/'figuras/e1_longitud_por_tag.png')==sha(ROOT/'reports/figures/E1/e1_longitud_por_tag.png'),'figure_sha256':sha(OUT/'figuras/e1_longitud_por_tag.png'),'limitations':['No pipelines rerun','Not all semantic assertions independently verified','Only selected E1 ECDF visually reviewed','Source files may change in another active session']}
write('verificacion_entrega.json',json.dumps(checks,ensure_ascii=False,indent=2))
print(json.dumps(checks,ensure_ascii=True,indent=2))
