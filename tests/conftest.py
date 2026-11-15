"""Shared fixtures. Everything here is SYNTHETIC test data, never the real Genius corpus."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "sonora" / "src"))

from sonora.ingestion import lyrics_corpus as lc  # noqa: E402
from sonora.nlp.language import LanguageScores, SecondaryScore  # noqa: E402


class FakeDetector:
    """Deterministic stand-in for lingua: texts containing Spanish marker words are 'es'."""

    name = "fake-detector"
    version = "0"
    mode = "test"
    SPANISH = {"corazón", "quiero", "contigo", "noche", "amor", "bailar"}

    def score_many(self, texts):
        out = []
        for text in texts:
            words = {w.strip(".,!?").casefold() for w in text.split()}
            hits = len(words & self.SPANISH)
            if "MIXED" in text:
                out.append(LanguageScores("en", 0.55, "es", 0.45, 0.55))
            elif hits >= 2:
                out.append(LanguageScores("es", 0.99, "pt", 0.01, 0.0))
            else:
                out.append(LanguageScores("en", 1.0, "es", 0.0, 1.0))
        return out


EN = ("[Verse 1]\nI can't stop thinking 'bout you, baby\nDon't you ever leave me now\n"
      "We were young and we were crazy\nNever gonna let you down\n\n[Chorus]\n"
      "Oh I won't, no I won't let go\nHold me close and never let me go\n")
ES = ("[Verso]\nQuiero bailar contigo esta noche\nMi corazón es tuyo amor\n"
      "Quiero bailar contigo toda la noche\nAmor amor corazón\n\n"
      "No quiero dormir sin ti esta noche\nBailar contigo es mi amor\n")


class FakeSecondary:
    name = "fake-secondary"
    version = "0"

    def classify(self, text):
        hits = len({w.strip(".,!?").casefold() for w in text.split()} & FakeDetector.SPANISH)
        return SecondaryScore("es", 0.99) if hits >= 2 else SecondaryScore("en", 0.99)


def fake_detectors():
    return FakeDetector(), FakeSecondary()


def make_shard_rows(n: int, offset: int) -> list[dict]:
    rows = []
    for i in range(n):
        g = offset + i
        if g % 17 == 3:
            lyrics = ES
        elif g % 23 == 5:
            lyrics = "   \n "
        elif g % 29 == 7:
            lyrics = "[Instrumental]"
        elif g % 31 == 11:
            lyrics = EN  # exact duplicate of a common text
        else:
            lyrics = EN.replace("baby", f"baby number {g}") + f"\nLine unique to song {g}\n"
        rows.append({"title": f"Song {g}" if g % 41 else "Song (Live)", "artist": f"Artist {g % 7}",
                     "tag": "pop", "year": 2000 + g % 20, "lyrics": lyrics})
    return rows


def write_shards(directory: Path, sizes: list[int], row_group_size: int = 13) -> list[Path]:
    import pyarrow as pa
    import pyarrow.parquet as pq

    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    offset = 0
    schema = pa.schema([("title", pa.string()), ("artist", pa.string()), ("tag", pa.string()),
                        ("year", pa.int64()), ("lyrics", pa.string())])
    for k, n in enumerate(sizes):
        rows = make_shard_rows(n, offset)
        offset += n
        path = directory / f"train-{k:05d}-of-{len(sizes):05d}.parquet"
        pq.write_table(pa.Table.from_pylist(rows, schema=schema), path, row_group_size=row_group_size)
        paths.append(path)
    return paths


@pytest.fixture()
def base_config() -> dict:
    config = lc.load_config(ROOT / "config" / "lyrics_corpus.yaml")
    return copy.deepcopy(config)


@pytest.fixture()
def project(tmp_path, base_config):
    """Synthetic project root: 3 shards with small row groups and a demo selection."""
    write_shards(tmp_path / "data" / "raw" / "genius", [120, 95, 101])
    config = base_config
    config["genius"]["pattern"] = "train-*-of-00003.parquet"
    config["genius"]["expected_files"] = 3
    config["chunk_rows"] = 40
    selection_rows = []
    # Two FMA tracks sharing one Genius row, one plain, one bad locator, one excluded (Spanish) row.
    specs = [("1", 0, 10, "Song 10", "Artist 3"), ("2", 0, 10, "Song 10", "Artist 3"),
             ("3", 1, 4, "Song 124", "Artist 5"), ("4", 2, 0, "Wrong title", "Artist 5"),
             ("5", 0, 3, "Song 3", "Artist 3")]
    for tid, shard, row, title, artist in specs:
        name = f"train-{shard:05d}-of-00003.parquet"
        selection_rows.append({
            "fma_track_id": tid, "fma_title": title, "fma_artist": artist, "metadata_subset": "medium",
            "genre_top": "Rock", "genius_file": name, "genius_row_zero_based": str(row),
            "genius_locator": f"{name}#row={row}", "original_status": "exact_unique_candidate",
            "risk_flags": [], "lyrics_validated": None, "audio_validated": None, "human_decision": None,
            "retained_for_experiment": True, "lyrics_source_group": f"{name}#row={row}",
            "fma_tracks_in_source_group": 1,
        })
    sel = tmp_path / "selection.json"
    sel.write_text(json.dumps({"count": len(specs), "rows": selection_rows}), encoding="utf-8")
    config["demo"]["selection"] = "selection.json"
    config["demo"]["expected_count"] = len(specs)
    config["demo"]["expected_distinct_genius_rows"] = 4
    audio = tmp_path / "data" / "raw" / "fma" / "fma_medium" / "000"
    audio.mkdir(parents=True)
    (audio / "000003.mp3").write_bytes(b"ID3fake")
    config["audit"].update(accepted_sample=5, uncertain_sample=5, non_english_sample=5)
    return tmp_path, config


def make_run(root: Path, config: dict, run_id: str = "t", scope: lc.Scope | None = None) -> lc.Run:
    return lc.Run(root=root, config=config, run_id=run_id, scope=scope or lc.Scope())
