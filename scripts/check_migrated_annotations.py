"""Read-only checks of migrated Parquet metadata; never runs spaCy."""
import json
from pathlib import Path
import pyarrow.parquet as pq
from sonora.nlp.annotate import plan_tasks, part_complete

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'manifests/nlp/lyrics_full_v1.json').read_text())
annotation = manifest['annotations']['spacy_sm_v1']
corpus = sorted((root / 'data/processed/lyrics/lyrics_full_v1/corpus').glob('*.parquet'))
assert len(corpus) == 10, len(corpus)
assert annotation['status'] == 'complete' and annotation['tasks_remaining'] == 0
tasks = plan_tasks(corpus, root / annotation['path'], annotation['config']['docs_per_task'], annotation['hash'])
missing = [f'{t.shard_stem}/{t.index}' for t in tasks if not part_complete(t)]
assert len(tasks) == annotation['tasks_total'] == 6317
assert not missing, missing
corpus_rows = sum(pq.ParquetFile(p).metadata.num_rows for p in corpus)
docs_rows = sum(pq.ParquetFile(t.part('docs')).metadata.num_rows for t in tasks)
split_rows = pq.ParquetFile(root / 'data/processed/splits/lyrics_full_v1/lyrics_splits.parquet').metadata.num_rows
assert corpus_rows == docs_rows == split_rows == 3155772
result = dict(status=annotation['status'], tasks_total=len(tasks), tasks_remaining=len(missing),
              corpus_rows=corpus_rows, annotation_docs_rows=docs_rows, split_rows=split_rows)
(root / 'runtime/migrated_annotations.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result), flush=True)
