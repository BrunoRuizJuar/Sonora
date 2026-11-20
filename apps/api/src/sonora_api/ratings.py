"""Persistent human judgments on recommendation pairs."""
from contextlib import closing, contextmanager
import sqlite3


@contextmanager
def rating_db(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_ratings (
                release_id TEXT NOT NULL,
                query_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                rater_id TEXT NOT NULL,
                strategy TEXT NOT NULL,
                rank INTEGER NOT NULL,
                theme REAL,
                emotion REAL,
                music_vibe REAL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (release_id, query_id, candidate_id, rater_id)
            )
        """)
        if 'music_vibe' not in {column[1] for column in db.execute("PRAGMA table_info(recommendation_ratings)")}:
            db.execute("ALTER TABLE recommendation_ratings ADD COLUMN music_vibe REAL")
        yield db


def read_rating(path, key):
    with rating_db(path) as db:
        row = db.execute("""
            SELECT theme, emotion, music_vibe FROM recommendation_ratings
            WHERE release_id = ? AND query_id = ? AND candidate_id = ? AND rater_id = ?
        """, key).fetchone()
    return dict(zip(('theme', 'emotion', 'music_vibe'), row)) if row else None


def save_rating(path, rating):
    with rating_db(path) as db:
        db.execute("""
            INSERT INTO recommendation_ratings
                (release_id, query_id, candidate_id, rater_id, strategy, rank, theme, emotion, music_vibe)
            VALUES (:release_id, :query_id, :candidate_id, :rater_id, :strategy, :rank, :theme, :emotion, :music_vibe)
            ON CONFLICT (release_id, query_id, candidate_id, rater_id) DO UPDATE SET
                strategy = excluded.strategy, rank = excluded.rank,
                theme = excluded.theme, emotion = excluded.emotion,
                music_vibe = excluded.music_vibe,
                updated_at = CURRENT_TIMESTAMP
        """, rating)
