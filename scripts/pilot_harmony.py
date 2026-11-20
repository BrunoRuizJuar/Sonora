"""Estimate triads and compare short progressions in the FMA listening pilot."""

from itertools import combinations, groupby
import json
import subprocess

import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import stft

from pilot_audio import OUTPUT, RATE, ROOT, decode


NOTES = "C C# D D# E F F# G G# A A# B".split()
TRIADS = [(root, third) for root in range(12) for third in (4, 3)]
TEMPLATES = np.zeros((len(TRIADS), 12))
for index, (root, third) in enumerate(TRIADS):
    TEMPLATES[index, (root + np.array([0, third, 7])) % 12] = 1 / np.sqrt(3)


def chord_segments(audio):
    frame, hop = 8192, 2048
    frequencies, times, spectrum = stft(
        audio, fs=RATE, nperseg=frame, noverlap=frame - hop,
    )
    magnitude = np.abs(spectrum)
    sustained = median_filter(magnitude, size=(1, 9))
    transient = median_filter(magnitude, size=(15, 1))
    tonal = (frequencies >= 82) & (frequencies <= 2200)
    pitches = 69 + 12 * np.log2(frequencies[tonal] / 440)
    nearest = np.rint(pitches)
    harmonic = sustained[tonal] > transient[tonal]
    values = magnitude[tonal] * harmonic * (1 - 2 * np.abs(pitches - nearest))[:, None]
    chroma = np.zeros((12, times.size))
    np.add.at(chroma, nearest.astype(int) % 12, values)
    chroma = median_filter(chroma, size=(1, 7))
    energy = np.linalg.norm(chroma, axis=0)
    scores = TEMPLATES @ (chroma / np.maximum(energy, 1e-12))
    best = scores.argmax(axis=0)
    top_two = np.partition(scores, -2, axis=0)[-2:]
    uncertain = (energy <= max(float(energy.max()) * 0.035, 1e-9)) | (
        (top_two[1] < 0.78) | (top_two[1] - top_two[0] < 0.045)
    )
    best[uncertain] = -1

    segments = []
    start = 0
    duration = audio.size / RATE
    for index, occurrences in groupby(best):
        end = start + sum(1 for _ in occurrences)
        start_seconds = min(start * hop / RATE, duration)
        end_seconds = min(end * hop / RATE, duration)
        chord = TRIADS[index] if index >= 0 and end_seconds - start_seconds >= 0.32 else None
        if segments and segments[-1][2] == chord:
            segments[-1] = (segments[-1][0], end_seconds, chord)
        else:
            segments.append((start_seconds, end_seconds, chord))
        start = end
    return segments


def progressions(segments):
    # Keep brief uncertain transitions within a phrase, and break on longer gaps.
    phrases = groupby(segments, key=lambda segment: segment[2] is None and segment[1] - segment[0] > 0.4)
    signatures = {}
    for long_gap, phrase in phrases:
        if not long_gap:
            chords = [chord for chord, _ in groupby(chord for _, _, chord in phrase if chord is not None)]
            for start in range(len(chords) - 2):
                sequence = tuple(chords[start:start + 3])
                first_root = sequence[0][0]
                key = tuple(((root - first_root) % 12, third) for root, third in sequence)
                signatures.setdefault(key, sequence)
    return signatures


def label(chord):
    if chord is None:
        return None
    root, third = chord
    return NOTES[root] + ("m" if third == 3 else "")


def main():
    sample = json.loads((OUTPUT / "resultados.json").read_text(encoding="utf-8"))["tracks"]
    tracks, signatures, errors = [], {}, []
    for row in sample:
        identifier = row["fma_track_id"]
        try:
            segments = chord_segments(decode(ROOT / row["audio_path"]))
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            errors.append({"fma_track_id": identifier, "error": str(error)})
            continue
        tracks.append({
            "fma_track_id": identifier,
            "title": row["fma_title"],
            "artist": row["fma_artist"],
            "segments": [
                {"start": round(start, 2), "end": round(end, 2), "chord": label(chord)}
                for start, end, chord in segments
            ],
        })
        signatures[identifier] = progressions(segments)

    pairs = []
    for first, second in combinations(signatures, 2):
        left, right = signatures[first], signatures[second]
        shared = sorted(left.keys() & right.keys())
        if shared:
            pairs.append({
                "fma_track_ids": [first, second],
                "similarity": len(shared) / len(left.keys() | right.keys()),
                "shared_sequences": [
                    [[label(chord) for chord in catalog[key]] for catalog in (left, right)]
                    for key in shared
                ],
            })
    pairs.sort(key=lambda pair: (len(pair["shared_sequences"]), pair["similarity"]), reverse=True)
    output = OUTPUT / "armonia.json"
    output.write_text(json.dumps({
        "method": "experimental major/minor triads from chroma; null means uncertain",
        "tracks": tracks,
        "pairs": pairs,
        "errors": errors,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(tracks)} tracks, {len(pairs)} pairs with shared sequences, {len(errors)} errors: {output}")


if __name__ == "__main__":
    main()
