"""Local playback catalog for the downloaded FMA Medium clips."""
import csv
from dataclasses import dataclass
from os import scandir
from pathlib import Path
import re
from unicodedata import combining, normalize


def search_key(value: str) -> str:
    folded = normalize('NFKD', value.casefold())
    plain = ''.join(char for char in folded if not combining(char))
    return re.sub(r'[^\w]+', ' ', plain).strip()


def audio_paths(root: Path) -> dict[int, Path]:
    paths = {}
    for directory in root.glob('[0-9][0-9][0-9]'):
        if not directory.is_dir() or not directory.resolve().is_relative_to(root):
            continue
        with scandir(directory) as entries:
            for entry in entries:
                if not re.fullmatch(fr'{directory.name}[0-9]{{3}}\.mp3', entry.name):
                    continue
                if entry.is_file(follow_symlinks=False) and entry.stat(follow_symlinks=False).st_size:
                    paths[int(entry.name[:6])] = Path(entry.path)
    return paths


@dataclass(frozen=True, slots=True)
class Recording:
    track_id: int
    title: str
    artist: str
    license: str
    path: Path
    keywords: str
    genre: str
    genres: frozenset[str]

    def public(self) -> dict:
        return {
            'track_id': self.track_id,
            'title': self.title,
            'artist': self.artist,
            'license': self.license,
            'audio_url': f'/api/v1/fma/tracks/{self.track_id}/audio',
        }


class AudioCatalog:
    def __init__(self, metadata: Path, audio_directory: Path, links: Path | None = None):
        self.root = audio_directory.resolve()
        paths = audio_paths(self.root)

        self.recordings: dict[int, Recording] = {}
        csv.field_size_limit(max(csv.field_size_limit(), 10 * 1024 * 1024))
        with metadata.open(encoding='utf-8-sig', newline='') as source:
            rows = csv.reader(source)
            columns = {name: index for index, name in enumerate(zip(next(rows, ()), next(rows, ())))}
            title_column = columns['track', 'title']
            artist_column = columns['artist', 'name']
            license_column = columns['track', 'license']
            genre_column = columns.get(('track', 'genre_top'))
            genres_column = columns.get(('track', 'genres'))
            for row in rows:
                if not row or not row[0].isascii() or not row[0].isdigit():
                    continue
                track_id = int(row[0])
                if track_id not in paths:
                    continue
                title = row[title_column].strip()
                if not title:
                    continue
                artist = row[artist_column].strip()
                license_name = row[license_column].strip()
                if track_id in self.recordings:
                    raise ValueError(f'ID FMA duplicado: {track_id}')
                keywords = search_key(f'{title} {artist} {track_id:06d} {track_id}')
                genre = row[genre_column] if genre_column is not None else ''
                genres = frozenset(re.findall(r'\d+', row[genres_column])) if genres_column is not None else frozenset()
                self.recordings[track_id] = Recording(
                    track_id, title, artist, license_name, paths[track_id], keywords, genre, genres,
                )
        if not self.recordings:
            raise ValueError('No hay pistas FMA con título y archivo MP3 local.')
        self.ordered = sorted(
            self.recordings.values(),
            key=lambda track: (search_key(track.artist), search_key(track.title), track.track_id),
        )
        self.lyrics_ids = {}
        if links is not None and links.is_file():
            with links.open(encoding='utf-8-sig', newline='') as source:
                for row in csv.DictReader(source):
                    if (row['lyrics_status'] == 'accepted' and row['locator_verified'] == 'True'
                            and row['locator_check'] == 'title_artist_normalized_equal' and row['lyrics_id']):
                        self.lyrics_ids[int(row['fma_track_id'])] = row['lyrics_id']

    def related(self, track_id: int, eligible=None, limit=20) -> list[dict]:
        origin = self.recordings[track_id]

        def relevance(track):
            shared = len(origin.genres & track.genres)
            overlap = shared / max(1, len(origin.genres | track.genres))
            genre = bool(origin.genre and origin.genre == track.genre)
            artist = bool(origin.artist and origin.artist == track.artist)
            both_have_lyrics = track_id in self.lyrics_ids and track.track_id in self.lyrics_ids
            return overlap * 4 + genre + artist * 0.5, both_have_lyrics

        ranked = sorted(
            (track for track in self.ordered if track.track_id != track_id
             and (eligible is None or track.track_id in eligible)),
            key=relevance, reverse=True,
        )
        return [track.public() for track in ranked[:limit]]

    def search(self, query: str, limit: int) -> list[dict]:
        query = query.strip()
        if 1 <= len(query) <= 6 and query.isascii() and query.isdigit():
            track = self.recordings.get(int(query))
            if track:
                return [track.public()]
        words = search_key(query).split()
        results = []
        for track in self.ordered:
            if all(word in track.keywords for word in words):
                results.append(track.public())
                if len(results) == limit:
                    break
        return results
