"""Fact checks acotados sobre metadatos guardados; no ejecuta pipelines.
Escritura sólo en reports/articulo_nlp/. Lectura de texto: únicamente letras cuyo
conteo guardado difiere entre corpus y doc_stats. No reentrena ni reanota.
"""
from pathlib import Path
import json, re, hashlib, sys, time
from collections import Counter
from datetime import datetime, timezone
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/articulo_nlp'
sys.stdout.reconfigure(encoding='utf-8')
started=time.monotonic()
def load(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def rel(p):return p.relative_to(ROOT).as_posix()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
W=re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*",re.UNICODE)
checks={'captured_utc':datetime.now(timezone.utc).isoformat(),'procedure':rel(Path(__file__).resolve()),'scope':'Lectura de columnas de metadatos; texto sólo de discrepancias; sin modificación de originales','corpus_shards':[]}
q=load('reports/corpus/lyrics_full_v1/quality_report.json')
s=load('manifests/splits/lyrics_full_v1.json')
split_path=ROOT/'data/processed/splits/lyrics_full_v1/lyrics_splits.parquet'
split=pq.read_table(split_path,columns=['lyrics_id','group_id','split'])
groups=split.group_by('group_id').aggregate([('split','count_distinct'),('split','count')])
checks['split']={'rows':split.num_rows,'unique_lyrics_ids':pc.count_distinct(split['lyrics_id']).as_py(),'groups':groups.num_rows,'groups_in_multiple_splits':pc.sum(pc.greater(groups['split_count_distinct'],1)).as_py(),'counts':dict(zip(*[x.to_pylist() for x in split.group_by('split').aggregate([('lyrics_id','count')]).columns])),'sha256':sha(split_path),'manifest_sha256':s['parquet_sha256']}
assert checks['split']['sha256']==s['parquet_sha256']
assert checks['split']['unique_lyrics_ids']==split.num_rows==q['canonical_lyrics']
assert checks['split']['groups_in_multiple_splits']==0
assert checks['split']['groups']==s['groups']
assert all(checks['split']['counts'][k]==v['lyrics'] for k,v in s['by_split'].items())
checks['split']['maximum_registered_group_size']=pc.max(groups['split_count']).as_py()
group_splits=split.group_by(['split','group_id']).aggregate([('split','count')])
group_counts=group_splits.group_by('split').aggregate([('group_id','count')])
checks['split']['groups_by_split']=dict(zip(group_counts['split'].to_pylist(),group_counts['group_id_count'].to_pylist()))
assert checks['split']['maximum_registered_group_size']==s['group_size_max']
assert all(checks['split']['groups_by_split'][k]==val['groups'] for k,val in s['by_split'].items())

word_sums=[0,0]; chars=0; nrecords=0; tags=Counter(); reasons=Counter(); lang=Counter(); years=Counter(); diffs=[]; tag_lengths={}; lengths=[]; lines=[]; stanzas=[]
seen=np.zeros(split.num_rows,dtype=np.int16)
for cp in sorted((ROOT/'data/processed/lyrics/lyrics_full_v1/corpus').glob('*.parquet')):
    dp=ROOT/'data/processed/nlp/lyrics_full_v1/doc_stats'/cp.name
    cols=['lyrics_id','n_words','n_chars_original','n_lines','n_stanzas','n_source_records','tag','year','lang_status','lang_reason']
    corpus=pq.read_table(cp,columns=cols)
    stats=pq.read_table(dp,columns=['lyrics_id','n_words','tag'])
    assert corpus.num_rows==stats.num_rows
    assert pc.all(pc.equal(corpus['lyrics_id'],stats['lyrics_id'])).as_py(), 'ID order differs; do not compare positions'
    assert pc.all(pc.equal(corpus['tag'],stats['tag'])).as_py()
    membership=pc.index_in(corpus['lyrics_id'],value_set=split['lyrics_id'])
    assert membership.null_count==0
    np.add.at(seen,membership.to_numpy(),1)
    a=corpus['n_words'].to_numpy(); b=stats['n_words'].to_numpy()
    ix=np.flatnonzero(a!=b)
    rowgroups={}; offset=0; pf=pq.ParquetFile(cp)
    for rg in range(pf.num_row_groups):
        count=pf.metadata.row_group(rg).num_rows
        needed=[int(i) for i in ix if offset<=i<offset+count]
        if needed:
            table=pf.read_row_group(rg,columns=['lyrics_id','lyrics_analysis'])
            for i in needed:
                txt=table['lyrics_analysis'][i-offset].as_py()
                old=W.findall(txt); new=W.findall(txt.lower())
                assert len(old)==int(a[i]) and len(new)==int(b[i])
                # Court snippets are diagnostic character contexts, not lyric extracts.
                expansion=[]
                for pos,ch in enumerate(txt):
                    if len(ch.lower())>1:
                        expansion.append({'codepoint':f'U+{ord(ch):04X}','lower_codepoints':[f'U+{ord(c):04X}' for c in ch.lower()],'context':txt[max(0,pos-6):pos+7]})
                control=len(W.findall(txt.replace('\u0130','I').lower()))
                assert control==len(old), 'Dotted-I control does not explain the discrepancy'
                diffs.append({'lyrics_id':table['lyrics_id'][i-offset].as_py(),'file':rel(cp),'row_zero_based':i,'row_group_zero_based':rg,'stored_before_lower':int(a[i]),'stored_after_lower':int(b[i]),'recomputed_before_lower':len(old),'recomputed_after_lower':len(new),'control_dotted_I_replaced_before_lower':control,'delta':len(new)-len(old),'expanded_characters':expansion})
        offset+=count
    word_sums[0]+=int(pc.sum(corpus['n_words']).as_py());word_sums[1]+=int(pc.sum(stats['n_words']).as_py())
    chars+=pc.sum(corpus['n_chars_original']).as_py(); nrecords+=pc.sum(corpus['n_source_records']).as_py()
    tags.update(Counter(corpus['tag'].to_pylist()));lang.update(Counter(corpus['lang_status'].to_pylist()));reasons.update(Counter(corpus['lang_reason'].to_pylist()))
    yy=corpus['year'].to_numpy();years['below_1900']+=int((yy<1900).sum());years['above_2022']+=int((yy>2022).sum())
    lengths.append(b);lines.append(corpus['n_lines'].to_numpy());stanzas.append(corpus['n_stanzas'].to_numpy())
    tt=stats['tag'].to_numpy()
    for t in np.unique(tt):tag_lengths.setdefault(str(t),[]).append(b[tt==t])
    checks['corpus_shards'].append({'path':rel(cp),'rows':corpus.num_rows,'metadata_word_differences':len(ix)})
checks['word_count']={'before_lower':word_sums[0],'after_lower':word_sums[1],'delta':word_sums[1]-word_sums[0],'documents_differing':len(diffs),'sum_recomputed_deltas':sum(d['delta'] for d in diffs),'cases':diffs}
assert np.all(seen==1)
checks['canonical_id_membership']={'corpus_ids_cover_split_once':bool(np.all(seen==1))}
checks['corpus_metadata']={'rows':sum(x['rows'] for x in checks['corpus_shards']),'accepted_source_records_sum':nrecords,'duplicate_source_records':nrecords-split.num_rows,'tag_counts':dict(tags),'language_status_counts':dict(lang),'language_reason_counts':dict(reasons),'year':dict(years),'n_chars_original_sum':chars,'median_words_after_lower':float(np.median(np.concatenate(lengths))),'median_lines':float(np.median(np.concatenate(lines))),'median_stanzas':float(np.median(np.concatenate(stanzas))),'median_words_by_tag':{t:float(np.median(np.concatenate(v))) for t,v in tag_lengths.items()}}
assert word_sums[0]==q['canonical_total_words']
assert nrecords==q['accepted_source_records']
assert dict(tags)==q['canonical_tag_counts']
lexpath=ROOT/'data/processed/nlp/lyrics_full_v1/lexicon/lexicon.parquet'
lex=pq.read_table(lexpath,columns=['count'])
checks['lexicon']={'types':lex.num_rows,'tokens':pc.sum(lex['count']).as_py()}
assert checks['lexicon']['tokens']==word_sums[1]
assert checks['word_count']['delta']==checks['word_count']['sum_recomputed_deltas']
checks['demo_current_presence']={p:(ROOT/p).exists() for p in ['data/processed/demo/lyrics_full_v1/demo_links.parquet','data/interim/matching/SONORA_Revision_Matching/medium_prioritarios.json','data/raw/fma/fma_medium','data/raw/genius']}
checks['raw_genius_parquet_files']=[rel(p) for p in (ROOT/'data/raw/genius').glob('*.parquet')]
exc=pq.read_table(ROOT/'data/processed/lyrics/lyrics_full_v1/exclusions.parquet',columns=['status','exclusion_rule'])
checks['exclusions']={'rows':exc.num_rows,'status_counts':dict(Counter(exc['status'].to_pylist())),'rule_counts':dict(Counter(exc['exclusion_rule'].to_pylist()))}
assert checks['exclusions']['rule_counts']==q['exclusion_or_review_rule_counts']
assert nrecords+exc.num_rows==q['source_records_read']

e3=load('reports/nlp/lyrics_full_v1/e3_summary.json');e4=load('reports/nlp/lyrics_full_v1/e4_summary.json')
checks['e3_e4']={'e3_docs':e3['docs'],'e4_docs':e4['docs'],'e3_tokens':e3['tokens'],'e4_tokens':e4['global_metrics']['tokens'],'sum_global_pos':sum(x['count'] for x in e3['global_pos']),'e3_sample_docs':e3['sample_docs'],'unique_example_lyrics':len(set(x['lyrics_id'] for x in e3['examples']))}
assert checks['e3_e4']['e3_tokens']==checks['e3_e4']['e4_tokens']==checks['e3_e4']['sum_global_pos']
ep='data/processed/nlp/lyrics_full_v1/semantics/e5-surface-v2/representations/complete.json'
ex=load(ep);ver=load('reports/nlp/lyrics_full_v1/e5_verification.json');an=load('reports/nlp/lyrics_full_v1/e5_analysis.json');retr=load('reports/nlp/lyrics_full_v1/e5_embedding_retrieval.json')
sample=split.filter(pc.is_in(split['lyrics_id'],value_set=pa.array(an['sample_ids'])))
checks['e5']={'same_space_ids':len({x['space_id'] for x in [ex,ver,retr]})==1,'same_counts':ex['counts']==ver['counts'],'sample_ids_unique':len(set(an['sample_ids'])),'sample_split_counts':Counter(sample['split'].to_pylist()),'n_projected':an['n_projected'],'context_scope':an['scope'],'context_minimum_support':an['minimum_context_support'],'query_counts':len(retr['queries']),'train_candidates':retr['train_candidates'],'note':'No se releen vectores/modelos; la verificación numérica original sigue siendo evidencia documental.'}
assert checks['e5']['same_space_ids'] and checks['e5']['same_counts']
assert checks['e5']['sample_split_counts']=={'validation':2000}

checks['notebooks']={}
for p in sorted((ROOT/'notebooks/evidencias').glob('*.ipynb')):
    n=json.loads(p.read_text(encoding='utf-8'))
    checks['notebooks'][p.stem.split('_')[0]]={'path':rel(p),'sha256':sha(p),'cells':[{'index_zero_based':i,'ordinal_one_based':i+1,'id':c.get('id'),'execution_count':c.get('execution_count'),'type':c['cell_type']} for i,c in enumerate(n['cells'])]}
checks['elapsed_seconds']=round(time.monotonic()-started,3)
(OUT/'revalidacion_independiente.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in checks.items() if k not in ['corpus_shards','notebooks','word_count']},ensure_ascii=False,indent=2))
print('Word discrepancy:',{k:v for k,v in checks['word_count'].items() if k!='cases'})
print('First cases:',json.dumps(diffs[:3],ensure_ascii=False))
