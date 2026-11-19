"""Prepare and evaluate a blinded, 200-lyric SGNS/EmoLex comparison."""
import argparse
from collections import defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
import random
from zipfile import ZipFile

import numpy as np

from sonora.recommendation.catalog import Catalog, words
from sonora.recommendation.lyric_text import LyricTextStore


SIZE = 200
SEED = 20261118
WEIGHTS = (0, 0.1, 0.2, 0.3)
EMOTIONS = ('anger', 'anticipation', 'disgust', 'fear', 'joy', 'sadness', 'surprise', 'trust')


def load_lexicon(path):
    with ZipFile(path) as archive:
        data = archive.read('NRC-Emotion-Lexicon/NRC-Emotion-Lexicon-Wordlevel-v0.92.txt')
    lexicon = defaultdict(list)
    for line in data.decode('utf-8-sig').splitlines():
        word, emotion, present = line.split('	')
        if present == '1' and emotion in EMOTIONS:
            lexicon[word].append(EMOTIONS.index(emotion))
    return lexicon, sha256(data).hexdigest()


def profile(text, lexicon):
    # Count each word once so repeating the chorus does not inflate the evidence.
    matches = set(words(text)).intersection(lexicon)
    counts = np.zeros(len(EMOTIONS))
    for word in matches:
        counts[lexicon[word]] += 1
    return counts / counts.sum() if len(matches) >= 3 else None, len(matches)


def sample(catalog):
    rows = []
    for shard in catalog.shards:
        if not shard['db'].execute("SELECT 1 FROM tracks WHERE split='test' LIMIT 1").fetchone():
            continue
        rows.extend((shard, row) for row in shard['db'].execute(
            "SELECT * FROM tracks WHERE split='test' AND available=1 "
            "AND rowid % 997 = 13 ORDER BY rowid"
        ))
    return random.Random(SEED).sample(rows, SIZE)


def prepare(args):
    lexicon, digest = load_lexicon(args.lexicon)
    catalog = Catalog(args.release)
    try:
        store = LyricTextStore(args.lyrics, catalog.manifest['space_id'], catalog.manifest['rows'])
        try:
            tracks, vectors, profiles, evidence = {}, [], [], {}
            for shard, row in sample(catalog):
                track_id = row['lyrics_id']
                lyric = store.get(track_id)['text']
                tracks[track_id] = dict(title=row['title'], artist=row['artist'], text=lyric)
                vectors.append(shard['vectors'][row['rowid']].copy())
                emotional, count = profile(lyric, lexicon)
                profiles.append(emotional)
                evidence[track_id] = dict(matched_words=count, profile=None if emotional is None else emotional.tolist())
        finally:
            store.close()
    finally:
        catalog.close()

    ids = list(tracks)
    cosine = np.clip(np.asarray(vectors[:12]) @ np.asarray(vectors).T, -1, 1)
    runs, pairs = {}, []
    rng = random.Random(SEED)
    for i, query in enumerate(ids[:12]):
        semantic = (cosine[i] + 1) / 2
        affinity = semantic.copy()
        if profiles[i] is not None:
            for j, candidate in enumerate(profiles):
                if candidate is not None:
                    affinity[j] = 1 - 0.5 * np.abs(profiles[i] - candidate).sum()
        rankings = {}
        for weight in WEIGHTS:
            combined = semantic + weight * (affinity - semantic)
            order = sorted((j for j in range(SIZE) if j != i),
                           key=lambda j: (combined[j], ids[j]), reverse=True)
            rankings[str(weight)] = [ids[j] for j in order[:10]]
        runs[query] = dict(group='validation' if i < 4 else 'test', rankings=rankings)
        union = sorted({candidate for ranking in rankings.values() for candidate in ranking})
        rng.shuffle(union)
        pairs.extend(dict(query_id=query, candidate_id=candidate) for candidate in union)

    design = dict(release_id=catalog.manifest['release_id'], lexicon_sha256=digest,
                  emotions=EMOTIONS, evidence=evidence, runs=runs)
    pilot_id = sha256(json.dumps(design, sort_keys=True).encode()).hexdigest()[:16]
    args.output.mkdir(parents=True, exist_ok=False)
    for filename, payload in (
        ('anotacion.json', dict(pilot_id=pilot_id, tracks=tracks, pairs=pairs)),
        ('diseno.json', dict(pilot_id=pilot_id, **design)),
    ):
        (args.output / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(tracks)} lyrics, {len(runs)} queries, {len(pairs)} pairs, '
          f'{sum(p is not None for p in profiles)} usable emotional profiles')


def ndcg(values, ideal):
    def dcg(grades):
        return sum((2**grade - 1) / math.log2(rank + 2) for rank, grade in enumerate(grades))

    ceiling = dcg(ideal[:10])
    return dcg(values) / ceiling if ceiling else 0.0


def evaluate(args):
    design = json.loads(args.design.read_text('utf-8'))
    annotations = json.loads(args.ratings.read_text('utf-8-sig'))
    if design['pilot_id'] != annotations['pilot_id']:
        raise ValueError('Ratings belong to a different pilot')
    ratings = {(r['query_id'], r['candidate_id']): r for r in annotations['ratings']}
    results = defaultdict(lambda: defaultdict(list))
    for query, run in design['runs'].items():
        rankings = run['rankings']
        union = {candidate for ranking in rankings.values() for candidate in ranking}
        for axis in ('theme', 'emotion'):
            grades = {candidate: ratings.get((query, candidate), {}).get(axis) for candidate in union}
            if any(type(grade) not in (int, float) or grade not in [i / 2 for i in range(11)] for grade in grades.values()):
                raise ValueError(f'Missing or invalid {axis} ratings for query {query}')
            ideal = sorted(grades.values(), reverse=True)
            for weight, ranking in rankings.items():
                results[run['group']][weight, axis].append(ndcg([grades[i] for i in ranking], ideal))

    averages = {group: {key: sum(scores) / len(scores) for key, scores in values.items()}
                for group, values in results.items()}
    validation = averages['validation']
    eligible = [str(w) for w in WEIGHTS if validation[str(w), 'theme'] >= validation['0', 'theme']]
    chosen = max(eligible, key=lambda w: validation[w, 'emotion'])
    for group, weights in (('validation', map(str, WEIGHTS)), ('test', dict.fromkeys(('0', chosen)))):
        for weight in weights:
            theme = averages[group][weight, 'theme']
            emotion = averages[group][weight, 'emotion']
            print(f'{group:10} weight={weight:3} theme nDCG@10={theme:.3f} emotion nDCG@10={emotion:.3f}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(required=True)
    build = commands.add_parser('prepare')
    build.add_argument('--lexicon', type=Path, required=True)
    build.add_argument('--release', type=Path, default=Path('artifacts/releases/lyrics-serving-v1'))
    build.add_argument('--lyrics', type=Path, default=Path('artifacts/releases/lyrics-original-v1'))
    build.add_argument('--output', type=Path, required=True)
    build.set_defaults(run=prepare)
    score = commands.add_parser('evaluate')
    score.add_argument('--design', type=Path, required=True)
    score.add_argument('--ratings', type=Path, required=True)
    score.set_defaults(run=evaluate)
    options = parser.parse_args()
    options.run(options)
