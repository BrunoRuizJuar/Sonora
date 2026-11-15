#!/usr/bin/env python3
"""SONORA: cruce de metadatos FMA -> Genius, sin audio ni letras en memoria.

Python 3.11+. Dependencias: pyarrow y rapidfuzz.
Ejecutar desde SONORA: python scripts/check_fma_genius.py --root .

Los resultados son CANDIDATOS para revision. Ni la igualdad normalizada ni un
score fuzzy prueban que letra y grabacion correspondan. No se acepta ningun
enlace automaticamente. La fase fuzzy bloquea por artista normalizado exacto;
no encontrar candidatos no demuestra que la letra no exista.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
import html
import importlib.metadata
import json
from pathlib import Path
import re
import sys
import time
import unicodedata
import uuid

SCRIPT_VERSION = "1.0.0"
NORMALIZATION_VERSION = "nfkc-casefold-punctuation-spaces-v1"
VERSION_WORDS = {"live", "remix", "instrumental", "karaoke", "acoustic", "demo", "remaster", "remastered"}
SUMMARY_FIELDS = [
    "fma_track_id", "fma_title", "fma_artist", "metadata_subset", "genre_top",
    "title_normalized", "artist_normalized", "fma_records_same_key", "status",
    "genius_rows_for_best_key", "best_title_score", "candidate_keys_shown", "notes",
]
CANDIDATE_FIELDS = [
    "fma_track_id", "fma_title", "fma_artist", "metadata_subset", "candidate_rank",
    "method", "title_score", "artist_score", "genius_title", "genius_artist",
    "genius_file", "genius_row_zero_based", "genius_locator", "version_warning",
    "review_decision", "review_notes",
]


def normalize(value: str | None) -> str:
    """Preserve accents and version WORDS; normalize only formatting variants."""
    if not value:
        return ""
    value = unicodedata.normalize("NFKC", html.unescape(str(value))).casefold()
    value = value.replace("&", " and ")
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


@lru_cache(maxsize=100_000)
def normalize_artist(value: str | None) -> str:
    return normalize(value)


@dataclass(frozen=True, slots=True)
class FmaTrack:
    track_id: str
    title: str
    artist: str
    subset: str
    genre: str
    title_norm: str
    artist_norm: str


@dataclass(frozen=True, slots=True)
class GeniusRef:
    title: str
    artist: str
    file: str
    row: int


def locate_fma_csv(root: Path, explicit: Path | None = None) -> Path:
    if explicit:
        path = explicit.resolve()
        if not path.is_file():
            raise ValueError(f"No existe el CSV indicado: {path}")
        return path
    folder = root / "data" / "raw" / "fma"
    paths = sorted(folder.rglob("tracks.csv")) if folder.exists() else []
    if not paths:
        raise ValueError(f"No se encontro tracks.csv dentro de {folder}. Extrae fma_metadata.zip.")
    if len(paths) > 1:
        options = "\n".join(str(p) for p in paths)
        raise ValueError(f"Hay varios tracks.csv. Selecciona uno con --fma-csv:\n{options}")
    return paths[0]


def read_fma(path: Path) -> list[FmaTrack]:
    """Read the official two-row CSV header without loading biographies/features."""
    csv.field_size_limit(10 * 1024 * 1024)
    tracks: list[FmaTrack] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        top = next(reader, [])
        bottom = next(reader, [])
        columns = {(a.strip(), b.strip()): i for i, (a, b) in enumerate(zip(top, bottom))}
        required = [("track", "title"), ("artist", "name")]
        if any(key not in columns for key in required):
            raise ValueError("tracks.csv no tiene las columnas ('track','title') y ('artist','name') del FMA original.")

        def field(row: list[str], key: tuple[str, str]) -> str:
            pos = columns.get(key)
            return row[pos].strip() if pos is not None and pos < len(row) else ""

        for row in reader:
            if not row or not any(row):
                continue
            track_id = row[0].strip()
            # pandas' MultiIndex CSV adds a separate index-name row.
            if track_id in {"track_id", ""} and not any(cell.strip() for cell in row[1:]):
                continue
            if not track_id.isdigit():
                raise ValueError(f"ID FMA invalido en la linea CSV {reader.line_num}: {track_id!r}")
            track_id = str(int(track_id))
            if track_id in seen:
                raise ValueError(f"ID FMA duplicado: {track_id}")
            seen.add(track_id)
            title = field(row, ("track", "title"))
            artist = field(row, ("artist", "name"))
            tracks.append(FmaTrack(
                track_id, title, artist, field(row, ("set", "subset")),
                field(row, ("track", "genre_top")), normalize(title), normalize_artist(artist),
            ))
    if not tracks:
        raise ValueError("El archivo tracks.csv no contiene pistas.")
    return tracks


def find_genius_files(root: Path, allow_partial: bool) -> list[Path]:
    folder = root / "data" / "raw" / "genius"
    expected = [folder / f"train-{i:05d}-of-00010.parquet" for i in range(10)]
    missing = [p.name for p in expected if not p.is_file()]
    if missing and not allow_partial:
        raise ValueError("Faltan archivos de Genius en " + str(folder) + ": " + ", ".join(missing))
    files = [p for p in expected if p.is_file()]
    if allow_partial and not files:
        files = sorted(folder.glob("*.parquet"))
    if not files:
        raise ValueError(f"No hay archivos Parquet en {folder}")
    return files


def scan_genius(files: list[Path], artists: set[str], batch_size: int):
    import pyarrow.parquet as pq

    # Keep only metadata whose normalized artist occurs in FMA.
    index: dict[str, dict[str, list[GeniusRef]]] = defaultdict(lambda: defaultdict(list))
    snapshots = []
    rows_read = 0
    retained = 0
    for number, path in enumerate(files, 1):
        print(f"[Genius {number}/{len(files)}] {path.name}", flush=True)
        try:
            with pq.ParquetFile(path) as parquet:
                if not {"title", "artist"}.issubset(parquet.schema_arrow.names):
                    raise ValueError(f"{path.name} no contiene title y artist.")
                offset = 0
                for batch in parquet.iter_batches(batch_size=batch_size, columns=["title", "artist"]):
                    values = batch.to_pydict()
                    for position, (title, artist) in enumerate(zip(values["title"], values["artist"])):
                        artist_norm = normalize_artist(artist)
                        if artist_norm not in artists:
                            continue
                        title_norm = normalize(title)
                        if not title_norm:
                            continue
                        index[artist_norm][title_norm].append(
                            GeniusRef(str(title), str(artist), path.name, offset + position)
                        )
                        retained += 1
                    offset += batch.num_rows
                    rows_read += batch.num_rows
                expected_rows = parquet.metadata.num_rows
                if offset != expected_rows:
                    raise ValueError(f"Conteo inconsistente en {path.name}")
                stat = path.stat()
                snapshots.append({
                    "name": path.name, "rows": offset, "bytes": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                })
                print(f"  Filas leidas: {offset:,}; acumuladas: {rows_read:,}", flush=True)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"No se pudo leer {path.name}. Comprueba la descarga. Detalle: {exc}") from exc
    return index, snapshots, rows_read, retained


def candidate_keys(track: FmaTrack, artist_titles: dict, cutoff: float, limit: int, exact_only: bool):
    if track.title_norm in artist_titles:
        return [(track.title_norm, 100.0, "exact_normalized")]
    if exact_only or not artist_titles:
        return []
    from rapidfuzz import fuzz, process
    return [(title, float(score), "fuzzy_title_exact_artist")
            for title, score, _ in process.extract(
                track.title_norm, list(artist_titles), scorer=fuzz.ratio,
                score_cutoff=cutoff, limit=limit,
            )]


def version_warning(left: str, right: str) -> str:
    a = set(left.split()) & VERSION_WORDS
    b = set(right.split()) & VERSION_WORDS
    if a != b:
        return "version_words_differ:" + ",".join(sorted(a)) + "|" + ",".join(sorted(b))
    return ""


def write_results(tracks, index, output, cutoff, limit, exact_only):
    counts: Counter = Counter()
    subsets: dict[str, Counter] = defaultdict(Counter)
    fma_keys = Counter((t.artist_norm, t.title_norm) for t in tracks if t.artist_norm and t.title_norm)
    candidate_rows = 0
    with (output / "fma_genius_matches.csv").open("w", encoding="utf-8-sig", newline="") as a, \
         (output / "fma_genius_candidates.csv").open("w", encoding="utf-8-sig", newline="") as b:
        summary_writer = csv.DictWriter(a, fieldnames=SUMMARY_FIELDS)
        candidates_writer = csv.DictWriter(b, fieldnames=CANDIDATE_FIELDS)
        summary_writer.writeheader()
        candidates_writer.writeheader()
        for track in tracks:
            titles = index.get(track.artist_norm, {})
            choices = [] if not track.title_norm or not track.artist_norm else candidate_keys(
                track, titles, cutoff, limit, exact_only,
            )
            fanout = fma_keys[(track.artist_norm, track.title_norm)]
            notes = ""
            best_count = 0
            if not track.title_norm or not track.artist_norm:
                status = "invalid_metadata"
            elif not choices:
                status = "no_candidate_in_scope"
                notes = ("artist_not_in_genius_exact_block" if not titles else
                         "no_exact_title_in_artist_block" if exact_only else
                         "no_title_candidate_above_cutoff")
            else:
                best_count = len(titles[choices[0][0]])
                if choices[0][2] == "exact_normalized":
                    status = "exact_unique_candidate" if best_count == 1 and fanout == 1 else "exact_ambiguous"
                else:
                    close_second = len(choices) > 1 and choices[0][1] - choices[1][1] <= 3
                    status = "fuzzy_ambiguous" if best_count > 1 or fanout > 1 or close_second else "fuzzy_candidate"
                notes = "candidate_only;lyrics_and_audio_not_verified"
                for rank, (title_norm, score, method) in enumerate(choices, 1):
                    for ref in titles[title_norm]:
                        candidates_writer.writerow({
                            "fma_track_id": track.track_id, "fma_title": track.title,
                            "fma_artist": track.artist, "metadata_subset": track.subset,
                            "candidate_rank": rank, "method": method,
                            "title_score": round(score, 3), "artist_score": 100.0,
                            "genius_title": ref.title, "genius_artist": ref.artist,
                            "genius_file": ref.file, "genius_row_zero_based": ref.row,
                            "genius_locator": f"{ref.file}#row={ref.row}",
                            "version_warning": version_warning(track.title_norm, title_norm),
                            "review_decision": "", "review_notes": "",
                        })
                        candidate_rows += 1
            summary_writer.writerow({
                "fma_track_id": track.track_id, "fma_title": track.title,
                "fma_artist": track.artist, "metadata_subset": track.subset,
                "genre_top": track.genre, "title_normalized": track.title_norm,
                "artist_normalized": track.artist_norm, "fma_records_same_key": fanout,
                "status": status, "genius_rows_for_best_key": best_count,
                "best_title_score": round(choices[0][1], 3) if choices else "",
                "candidate_keys_shown": len(choices), "notes": notes,
            })
            counts[status] += 1
            subsets[track.subset or "unknown"][status] += 1

    statuses = ["exact_unique_candidate", "exact_ambiguous", "fuzzy_candidate", "fuzzy_ambiguous", "no_candidate_in_scope", "invalid_metadata"]
    with (output / "coverage_by_metadata_subset.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["metadata_subset", "fma_rows", *statuses])
        writer.writeheader()
        for subset, subset_counts in sorted(subsets.items()):
            writer.writerow({"metadata_subset": subset, "fma_rows": sum(subset_counts.values()),
                             **{key: subset_counts[key] for key in statuses}})
    return {key: counts[key] for key in statuses}, candidate_rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--fma-csv", type=Path, help="Ruta explicita si se encuentra mas de un tracks.csv")
    parser.add_argument("--batch-size", type=int, default=65_536)
    parser.add_argument("--fuzzy-cutoff", type=float, default=90.0, help="Score minimo de titulo; NO probabilidad")
    parser.add_argument("--candidates-per-track", type=int, default=3)
    parser.add_argument("--exact-only", action="store_true")
    parser.add_argument("--allow-partial-genius", action="store_true", help="Solo para una prueba parcial, declarada en el informe")
    args = parser.parse_args(argv)
    if args.batch_size < 1 or args.candidates_per_track < 1 or not 0 <= args.fuzzy_cutoff <= 100:
        parser.error("batch-size y candidates-per-track deben ser positivos; fuzzy-cutoff debe estar entre 0 y 100.")
    for package in ["pyarrow", *([] if args.exact_only else ["rapidfuzz"])]:
        try:
            importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            parser.error("Faltan dependencias. Ejecuta: python -m pip install pyarrow rapidfuzz")

    start = time.perf_counter()
    root = args.root.resolve()
    try:
        fma_path = locate_fma_csv(root, args.fma_csv)
        genius_files = find_genius_files(root, args.allow_partial_genius)
        print(f"FMA: {fma_path}", flush=True)
        tracks = read_fma(fma_path)
        print(f"Pistas FMA: {len(tracks):,}", flush=True)
        artists = {t.artist_norm for t in tracks if t.artist_norm and t.title_norm}
        index, sources, genius_rows, retained = scan_genius(genius_files, artists, args.batch_size)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = root / "data" / "interim" / "matching" / f"run_{stamp}_{uuid.uuid4().hex[:6]}"
        output.mkdir(parents=True, exist_ok=False)
        print("Construyendo candidatos y archivos de revision...", flush=True)
        counts, candidate_rows = write_results(tracks, index, output, args.fuzzy_cutoff,
                                               args.candidates_per_track, args.exact_only)
        candidate_tracks = sum(counts[k] for k in ["exact_unique_candidate", "exact_ambiguous", "fuzzy_candidate", "fuzzy_ambiguous"])
        summary = {
            "script_version": SCRIPT_VERSION,
            "normalization_version": NORMALIZATION_VERSION,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "fma_csv": str(fma_path), "fma_csv_bytes": fma_path.stat().st_size,
            "fma_rows": len(tracks), "genius_files_read": len(genius_files),
            "partial_genius_allowed": args.allow_partial_genius,
            "genius_rows_read": genius_rows, "genius_metadata_rows_retained": retained,
            "genius_sources": sources,
            "source_fingerprint_type": "file_name_row_count_size_mtime_not_content_hash",
            "counts": counts, "candidate_rows": candidate_rows,
            "fma_tracks_with_candidates": candidate_tracks,
            "metadata_candidate_rate": candidate_tracks / len(tracks),
            "human_validated_matches": None, "validated_coverage": None,
            "lyrics_read": False, "audio_read": False,
            "fuzzy_scope": "exact_normalized_artist_then_fuzzy_title",
            "fuzzy_enabled": not args.exact_only,
            "fuzzy_title_cutoff": args.fuzzy_cutoff,
            "max_fuzzy_title_keys_per_track": args.candidates_per_track,
            "batch_size": args.batch_size,
            "elapsed_seconds": round(time.perf_counter() - start, 2),
            "python": sys.version,
            "dependencies": {name: importlib.metadata.version(name) for name in
                             ["pyarrow", *([] if args.exact_only else ["rapidfuzz"]) ]},
            "output": str(output),
            "limitations": [
                "All links are candidates; no recording/lyric identity has been confirmed.",
                "Lyrics text and audio were not inspected; availability/validity is not measured.",
                "Artist aliases and artist spelling variants outside exact normalized blocks are not searched.",
                "Fuzzy scores describe string similarity, not probabilities or semantic similarity.",
                "Subset rows are literal FMA metadata labels, not cumulative audio-archive membership.",
                "Input fingerprints are metadata, not cryptographic content hashes.",
            ],
        }
        (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("\nRESULTADO: CANDIDATOS DE METADATOS; NO ENLACES VALIDADOS", flush=True)
        print(f"FMA examinadas: {len(tracks):,}")
        print(f"Genius leidas: {genius_rows:,}")
        for key, value in counts.items():
            print(f"{key}: {value:,}")
        print(f"Tasa de candidatos de metadatos: {100 * summary['metadata_candidate_rate']:.2f}%")
        print("Cobertura validada: pendiente de revisar letras/audio.")
        print(f"Resultados: {output}")
        print(f"Tiempo: {summary['elapsed_seconds']:.2f} segundos")
        return 0
    except (ValueError, OSError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
