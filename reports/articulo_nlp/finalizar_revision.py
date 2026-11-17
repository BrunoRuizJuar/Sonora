"""Control editorial final de la segunda entrega; no procesa datos."""
from pathlib import Path
import json,re,hashlib
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/articulo_nlp'
removed={}
for name in ['02_INTRODUCCION.md','04_CORPUS_Y_PREPARACION.md','13_REFERENCIAS.md']:
    p=OUT/name;txt=p.read_text(encoding='utf-8');total=0
    while True:
        txt,count=re.subn(r'([^\n]{80,}?) \1',r'\1',txt)
        total+=count
        if not count:break
    if total:p.write_text(txt,encoding='utf-8')
    removed[name]=total
parts=['# Estructura lingüística y representaciones textuales para la recuperación de canciones en SONORA',
'**Título provisional. Borrador parcial — segunda entrega.** Introducción y Corpus revisados críticamente, con citas a notebooks y celdas. No acredita cierre de las cinco evidencias. Autoría y afiliación: [PENDIENTE: incorporar sólo datos confirmados]. [Índice](INDICE.md) · [Fact checks](00_FACT_CHECKS.md). Los índices de celda de las citas empiezan en cero; no son contadores de ejecución.']
for name in ['02_INTRODUCCION.md','04_CORPUS_Y_PREPARACION.md','13_REFERENCIAS.md']:parts.append((OUT/name).read_text(encoding='utf-8').strip())
integrated='\n\n'.join(parts)+'\n'
(OUT/'ARTICULO_COMPLETO.md').write_text(integrated,encoding='utf-8')
assert 'PENDIENTE: reconciliar los 180' not in integrated
assert 'La revalidación directa' in integrated
assert all(f', E{i}, celda' in integrated for i in range(1,6))
assert 'mantiene los grupos juntos; La' not in integrated
assert not re.search(r'([^\n]{80,}?) \1',integrated)
broken=[]
for p in OUT.glob('*.md'):
    if p.name=='LECTURA_NOTEBOOKS.md':continue
    for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if target.startswith(('http:','https:','#')):continue
        if not (p.parent/target.split('#')[0]).exists():broken.append([p.name,target])
assert not broken,broken
n=json.loads((OUT/'revalidacion_independiente.json').read_text(encoding='utf-8'))['notebooks']
for ev,x in n.items():assert hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest()==x['sha256']
paths=['packages/sonora/src/sonora/ingestion/lyrics_corpus.py','packages/sonora/src/sonora/nlp/annotate.py','pipelines/nlp/annotate_corpus.py','packages/sonora/src/sonora/nlp/semantics.py','packages/sonora/src/sonora/preprocessing/lyrics_text.py','packages/sonora/src/sonora/nlp/doc_stats.py','reports/articulo_nlp/revalidar_hallazgos.py','reports/articulo_nlp/actualizar_revalidacion.py','reports/articulo_nlp/finalizar_revision.py']+[x['path'] for x in n.values()]
sources=[{'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in paths]
(OUT/'fuentes_segunda_entrega.json').write_text(json.dumps({'sources':sources,'verified_utc':datetime.now(timezone.utc).isoformat(),'notes':'Hashes al finalizar. No se releen corpus ni modelos grandes.'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
vf=OUT/'verificacion_segunda_entrega.json';v=json.loads(vf.read_text(encoding='utf-8'))
v.update(final_editorial_check_utc=datetime.now(timezone.utc).isoformat(),notebook_hashes_unchanged=True,inline_E1_E5_citations_present=True,duplicated_editorial_insertions_removed=removed,broken_local_links=broken,integrated_matches_sections=True)
vf.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(v,ensure_ascii=True,indent=2))
