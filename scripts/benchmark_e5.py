"""Resource smoke benchmark on 5000 train lyrics; NOT a corpus model/result."""
from itertools import islice
import os
from pathlib import Path
import sys
import time

for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/sonora/src'))
from gensim.models import Word2Vec
from sonora.nlp.semantics import Documents
from sonora.nlp.semantic_models import load_vocab, stable_hash
from sonora.storage.runs import peak_rss_bytes, write_json_atomic

cache = ROOT / 'data/processed/nlp/lyrics_full_v1/semantics/e5-surface-v2'
texts = list(islice(Documents(cache, 'train'), 5000))
sentences = [terms[i:i+1000] for terms in texts for i in range(0, len(terms), 1000)]
vocab = load_vocab(cache)
results = []
for workers in (1, 4):
    model = Word2Vec(vector_size=128, sg=1, window=5, negative=5, sample=.001,
                     min_count=1, seed=42, hashfxn=stable_hash, workers=workers)
    model.build_vocab_from_freq({r['word']: r['train_tf'] for r in vocab})
    started = time.monotonic()
    counts = model.train(sentences, total_examples=len(sentences), epochs=1)
    result = {'workers': workers, 'seconds': time.monotonic()-started,
              'effective_words': counts[0], 'raw_words': counts[1], 'peak_rss_bytes': peak_rss_bytes()}
    results.append(result)
    print(result, flush=True)
    del model
write_json_atomic(ROOT / 'runtime/e5_benchmark.json', {
    'scope': 'first 5000 train lyrics only; discarded weights; runtime benchmark, not scientific result',
    'results': results,
})
