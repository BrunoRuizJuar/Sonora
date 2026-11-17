"""Real-data integrity/latency check; does not measure recommendation relevance."""
import argparse
import json
from pathlib import Path
import threading
import time

import psutil

from sonora.recommendation.catalog import Catalog
from sonora.recommendation.lyrics import recommend_lyrics
from sonora.storage.runs import file_sha256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', type=Path, default=Path('artifacts/releases/lyrics-serving-v1'))
    parser.add_argument('--hashes', action='store_true')
    parser.add_argument('--reference', action='store_true')
    args = parser.parse_args()
    process = psutil.Process()
    peak = [0]
    stop = threading.Event()
    def sample():
        while not stop.wait(.05):
            peak[0] = max(peak[0], process.memory_info().rss)
    monitor = threading.Thread(target=sample, daemon=True)
    monitor.start()
    started = time.perf_counter()
    c = Catalog(args.release)
    report = dict(startup_seconds=time.perf_counter()-started, rows=c.manifest['rows'], release_id=c.manifest['release_id'])
    try:
        if args.hashes:
            for item in c.manifest['shards']:
                for name, signature in item['files'].items():
                    if file_sha256(args.release / item['name'] / name) != signature['sha256']:
                        raise ValueError('Hash mismatch: ' + name)
            report['all_output_hashes_verified'] = True
        for strategy in ('sgns', 'tfidf'):
            result = c.recommend(identifier='lyr_edc300ca1b86e86572b2', strategy=strategy, top_k=10, splits=('train',))
            report[strategy] = result
            print(strategy, result['elapsed_seconds'], flush=True)
        report['free_text'] = c.recommend(text='Leaving home and missing my family xyzzyunknown', strategy='sgns', top_k=5, splits=('train',))
        if args.reference:
            reference = recommend_lyrics('data/processed/nlp/lyrics_full_v1/semantics/e5-surface-v2/representations', 'lyr_edc300ca1b86e86572b2', k=10)
            actual = report['sgns']['items']
            if [r['id'] for r in actual] != [r['lyrics_id'] for r in reference['neighbors']]:
                raise ValueError('Exact reference differs')
            report['reference_top10_overlap'] = 1.0
            report['reference_max_score_error'] = max(abs(a['score']-b['cosine']) for a,b in zip(actual,reference['neighbors']))
    finally:
        c.close()
        stop.set()
        monitor.join()
    report['peak_rss_bytes'] = peak[0]
    report['total_seconds'] = time.perf_counter()-started
    Path('runtime/text_catalog_benchmark.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('peak RSS',peak[0], 'total',report['total_seconds'],flush=True)


if __name__ == '__main__':
    main()
