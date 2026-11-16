"""Build E4 from existing full-corpus syntax aggregates and directed examples."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from nbbuild import ROOT, build, md, code

CELLS=[md(r'''
# Evidencia 4 — Sintaxis y dependencias

**SONORA · E4-01…04 · corpus completo `lyrics_full_v1`.**

Se reutilizan spaCy 3.8.18 y `en_core_web_sm` 3.8.0, sin NER, ya ejecutados.
No se vuelve a anotar ni se ajusta ningún modelo. Los análisis descriptivos incluyen
todos los splits: no constituyen evaluación predictiva sobre test.
Pipeline: `pipelines/nlp/e4_syntax.py`; módulo: `sonora.nlp.syntax`.

Las métricas cubren las **3 155 772 letras**, los diez shards y las 6 317 partes
de oraciones. Los árboles y la auditoría estructural detallada usan una selección
declarada; no sustituyen los agregados del corpus completo.

## 1. Convenciones y denominadores (E4-03)

- Unidad: segmento que devuelve el parser con frontera forzada por salto de verso.
  Un verso puede subdividirse y una oración gramatical puede continuar en otro verso.
  Por eso llamamos a la unidad **segmento anotado**, no oración gramatical certificada.
- Longitud: `n_words` cuenta tokens sin espacio y sin `is_punct`; conserva números,
  símbolos y clíticos. Es una política distinta de excluir UPOS PUNCT/SYM/SPACE en E3.
- Profundidad: máximo número de saltos hasta la raíz de los tokens no puntuación;
  raíz = 0. Los caminos siguen el árbol original, sin comprimir nodos intermedios.
- Distancia: \(d=|tok_i-head_i|\), con índices originales de spaCy. Se excluyen
  la raíz y arcos cuyo dependiente **o cabeza** sea puntuación. Los espacios/puntuación
  entre extremos siguen aportando posiciones; no se renumera el texto.
- Media global por arco: \(\sum_s n_s\bar d_s/\sum_s n_s\).
  La media por segmento con arcos, \(\sum_s\bar d_s/|S_{arcos}|\), se muestra por separado.
  No confundir ponderación por arcos con media de medias.
- Las medias de distancias de entrada están en float32; la agregación usa float64.
  La media ponderada reconstruida tiene el pequeño redondeo de las medias originales.
- Segmentos sin arcos: distancia no definida, nunca cero. Se incluyen en los
  denominadores de longitud/profundidad y se contabilizan explícitamente.
  Raíz no verbal y profundidad cero no se consideran errores automáticamente.
- Décadas: sólo `year` entre 1900 y 2022; demás años desconocidos. Los tags y años
  son metadatos de la fuente, no géneros o fechas de composición validados.

Se validaron valores finitos, conteos no negativos y coherencia entre distancia nula
y ausencia de arcos en **cada lote**. Una anomalía numérica detiene la ejecución;
no se excluyen silenciosamente filas. Esto no verifica la corrección lingüística del parser.
'''),code(r'''
import json,sys
from pathlib import Path
from collections import Counter
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import display,Markdown
ROOT=Path.cwd()
sys.path.insert(0,str(ROOT/'packages/sonora/src'))
from sonora import viz
from sonora.nlp.syntax import FIELDS, normalized, draw_tree
viz.apply_style()
FIG=ROOT/'reports/figures/E4'
summary=json.loads((ROOT/'reports/nlp/lyrics_full_v1/e4_summary.json').read_text(encoding='utf-8'))
audit=json.loads((ROOT/'reports/nlp/lyrics_full_v1/e4_examples.json').read_text(encoding='utf-8'))
g=summary['global_metrics']
assert summary['docs']==3155772 and summary['parts']==6317
assert g['tokens']==1033733693 and g['sentences']==144457653
def show(rows):
    if not rows: return
    cols=list(rows[0])
    def fmt(v):
        if v is None: return '—'
        if isinstance(v,float): return f'{v:.4f}'
        return str(v).replace('|',r'\|').replace('\n',' / ')
    display(Markdown('\n'.join(['| '+' | '.join(cols)+' |','|'+'---|'*len(cols)]+
                    ['| '+' | '.join(fmt(r[k]) for k in cols)+' |' for r in rows])))
def combine(rows):
    return normalized([sum(r[k] for r in rows) for k in FIELDS])
def quantile_hist(hist,q):
    pairs=sorted((int(k),v) for k,v in hist.items()); target=max(1,int(np.ceil(q*sum(v for k,v in pairs))))
    total=0
    for k,v in pairs:
        total+=v
        if total>=target:return k
print('Configuración:',summary['annotation_config'])
show([{'medida':k,'valor':v} for k,v in {'letras':summary['docs'],'partes':summary['parts'],**g}.items()])
show([{'variable':k,**{f'p{int(q*100)}':quantile_hist(h,q) for q in [.5,.9,.95,.99,1]}}
      for k,h in summary['hist'].items()])
'''),md(r'''
## 2. Distribuciones del corpus completo

Percentiles por rango más próximo, ponderados por número de segmentos, no por letra.
Las figuras se recortan al p99 únicamente para legibilidad: las tablas incluyen el máximo
y los promedios conservan toda la cola. No se elimina ni winsoriza ninguna observación.
'''),code(r'''
fig,axes=plt.subplots(1,2,figsize=(12,4))
for ax,key,label in zip(axes,['n_words','depth'],['Longitud sin puntuación','Profundidad máxima']):
    h=summary['hist'][key]; limit=quantile_hist(h,.99)
    pairs=sorted((int(k),v) for k,v in h.items() if int(k)<=limit)
    ax.bar([k for k,v in pairs],[100*v/g['sentences'] for k,v in pairs],color=viz.SEQUENTIAL)
    tail=sum(v for k,v in h.items() if int(k)>limit)
    ax.set(xlabel=label,ylabel='% de todos los segmentos',title=f'{label} · hasta p99={limit}')
    ax.text(.98,.95,f'Cola fuera del gráfico: {100*tail/g["sentences"]:.2f} %',
            transform=ax.transAxes,ha='right',va='top',fontsize=8)
viz.save(fig,FIG/'distribuciones.png');plt.show()
'''),md(r'''
## 3. Comparación por tag, década y longitud (E4-03/04)

Las medias de longitud y profundidad ponderan segmentos; la distancia pondera arcos.
Se muestran letras, segmentos y arcos para conocer el soporte. La agregación global
no es una media simple de cinco tags. Comparar bandas de longitud reduce un factor
de confusión, pero las bandas siguen conteniendo longitudes y composiciones diferentes.
'''),code(r'''
groups=summary['groups']; tags=viz.TAG_ORDER
by_tag=[dict(tag=t,docs=sum(r['docs'] for r in groups if r['tag']==t),
             **combine([r for r in groups if r['tag']==t])) for t in tags]
decades=sorted({r['decade'] for r in groups if r['decade'] is not None})
by_dec=[dict(decade=d,docs=sum(r['docs'] for r in groups if r['decade']==d),
             **combine([r for r in groups if r['decade']==d])) for d in decades+[None]]
metrics=['mean_words','mean_depth','mean_dependency_distance']
cols=['docs','sentences','arcs']+metrics+['no_arcs','nonverbal_roots']
show([{'tag':r['tag'],**{k:r[k] for k in cols}} for r in by_tag])
show([{'década':r['decade'],**{k:r[k] for k in cols}} for r in by_dec])
assert sum(r['sentences'] for r in by_tag)==g['sentences']==sum(r['sentences'] for r in by_dec)
fig,axes=plt.subplots(1,3,figsize=(13,4))
for ax,key,title,unit in zip(axes,metrics,['Longitud media','Profundidad media','Distancia media por arco'],
                           ['Tokens sin puntuación','Saltos hasta la raíz','Posiciones de token']):
    ax.bar([r['tag'] for r in by_tag],[r[key] for r in by_tag],color=viz.SEQUENTIAL)
    ax.set(title=title,ylabel=unit)
    ax.tick_params(axis='x',rotation=35)
viz.save(fig,FIG/'comparacion_tags.png');plt.show()
visible=[r for r in by_dec if r['decade'] is not None and r['docs']>=1000]
fig,axes=plt.subplots(1,3,figsize=(14,4))
for ax,key,title,unit in zip(axes,metrics,['Longitud media','Profundidad media','Distancia media por arco'],
                           ['Tokens sin puntuación','Saltos hasta la raíz','Posiciones de token']):
    ax.plot([r['decade'] for r in visible],[r[key] for r in visible],marker='o')
    ax.set(title=title,xlabel='Década de year',ylabel=unit);ax.tick_params(axis='x',rotation=45)
viz.save(fig,FIG/'comparacion_decadas.png');plt.show()
show([{'tag':r['tag'],'band':r['band'],'segmentos':r['sentences'],'arcos':r['arcs'],
       **{k:r[k] for k in metrics}} for r in summary['by_length']])
show([{'tag':r['tag'],'década':r['decade'],'letras':r['docs'],'segmentos':r['sentences'],
       **{k:r[k] for k in metrics}} for r in groups if r['decade'] in [1970,2020]])
'''),md(r'''
## 4. Auditoría de grafos y árboles dirigidos (E4-01/02/04)

Selección dirigida: primera parte de tokens de cada shard (hasta 500 letras por parte).
Se auditan todos sus segmentos buscando raíz única, coherencia de ROOT, cabezas presentes
y ciclos. Son comprobaciones estructurales de los archivos exportados; un árbol puede
superarlas y ser lingüísticamente erróneo. Una cabeza ausente puede deberse a la exportación
sin espacios, por lo que no se adjudica automáticamente el fallo al parser original.

Se eligen cuatro árboles cortos (3–10 tokens): construcción con `nsubj` y `dobj`, cláusula
subordinada (`advcl/ccomp/relcl`), coordinación (`cc/conj`) y segmento sin VERB/AUX.
Se priorizan tags distintos y se exigen letras diferentes; se conserva el primer candidato
por criterio/tag en orden de archivo. Son casos ilustrativos, no prevalencias del corpus.
La etiqueta del criterio depende de predicciones del parser, por eso se revisa su lectura.

Los árboles usan **flechas cabeza → dependiente**, índices originales debajo del POS y
etiquetas de dependencia de spaCy (incluyen `dobj`; no se renombran como UD v2).
No son árboles de constituyentes. `nsubj/dobj` describen relaciones sintácticas:
no certifican papeles semánticos agente/paciente ni sentimiento.
'''),code(r'''
print('Auditoría dirigida:',audit['sample_docs'],'letras;',audit['sample_segments'],'segmentos')
print('Anomalías estructurales por tipo (pueden solaparse):',audit['graph_issues'])
print('Partes:',*audit['files'],sep='\n')
assert len(audit['examples'])>=3 and len({e['lyrics_id'] for e in audit['examples']})==len(audit['examples'])
for e in audit['examples']:
    display(Markdown(f"### {e['criterion']} · {e['tag']}\n\n`{e['lyrics_id']}` · "
                     f"`sent_i={e['sent_i']}` · `line_i={e['line_i']}`\n\nArchivo: `{e['file']}`"))
    print('Métricas del árbol:',e['audit'])
    index={r['tok_i']:r for r in e['tokens']}
    show([{'tok_i':r['tok_i'],'dependiente':r['text'],'POS':r['upos'],'lema':r['lemma'],
           'relación':r['dep'],'head_i':r['head_i'],'cabeza':index[r['head_i']]['text']}
           for r in e['tokens']])
    fig=draw_tree(e,FIG/f"arbol_{e['criterion']}.png");plt.show()
'''),md(r'''
## 5. Hallazgos calculados y límites
'''),code(r'''
lo=min(by_tag,key=lambda r:r['mean_words']);hi=max(by_tag,key=lambda r:r['mean_words'])
display(Markdown(f"""
- El corpus completo contiene **{g['sentences']:,} segmentos anotados**, con
  longitud media **{g['mean_words']:.4f}**, profundidad media **{g['mean_depth']:.4f}**
  y distancia media por arco **{g['mean_dependency_distance']:.4f}** posiciones.
  La media de distancias por segmento con arcos es **{g['mean_sentence_dependency_distance']:.4f}**;
  la diferencia se debe a la ponderación, no a otro parser.
- **{g['no_arcs']:,} segmentos** no tienen arcos incluidos
  ({100*g['no_arcs']/g['sentences']:.3f} %). Su distancia no está definida;
  no se sustituyó por cero para disminuir artificialmente la media.
- **{g['nonverbal_roots']:,} segmentos** tienen raíz con POS distinto de VERB/AUX
  ({100*g['nonverbal_roots']/g['sentences']:.3f} %). Esto permite describir salidas nominales
  o fragmentarias, pero no contar oraciones incorrectas.
- La mayor longitud media por tag es **{hi['tag']} ({hi['mean_words']:.4f})** y la menor
  **{lo['tag']} ({lo['mean_words']:.4f})**. Profundidad y distancia dependen en parte de
  longitud; las tablas por bandas y dentro de tag/década evitan atribuir directamente
  la diferencia al género. Tampoco prueban mayor complejidad artística o calidad lingüística.
- Los gráficos temporales usan grupos con al menos 1 000 letras; sus tablas conservan
  todos los grupos y años desconocidos. Cambios de composición por artista/tag y la
  fragmentación por verso impiden interpretar las curvas como evolución causal.
"""))
''')]
CELLS.append(md((ROOT/'docs/E4_REVISION.md').read_text(encoding='utf-8')))
if __name__=='__main__':
    print(build(CELLS,ROOT/'notebooks/evidencias/E4_sintaxis_dependencias.ipynb'))
