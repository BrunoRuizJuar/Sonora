from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    track_id: str | None = Field(default=None, min_length=1, max_length=100)
    text: str | None = Field(default=None, min_length=1, max_length=10000)
    mode: Literal['lyrics', 'audio', 'mixed'] = 'lyrics'
    strategy: Literal['sgns', 'tfidf'] = 'sgns'
    top_k: int = Field(default=10, ge=1, le=50)
    candidate_splits: list[Literal['train', 'validation', 'test']] = Field(default=['train', 'validation', 'test'], min_length=1)
    max_per_artist: int | None = Field(default=None, ge=1, le=50)
    exclude_known_covers: bool = False

    @model_validator(mode='after')
    def one_input(self):
        if (self.track_id is None) == (self.text is None):
            raise ValueError('Especifica exactamente track_id o text')
        if self.text is not None and not self.text.strip():
            raise ValueError('Texto vacÃ­o')
        return self


RaterId = Annotated[str, Field(pattern=r'^[0-9a-f]{32}$')]
Grade = Annotated[float, Field(strict=True, ge=0, le=5, multiple_of=0.5)]


class RatingScores(BaseModel):
    model_config = ConfigDict(extra='forbid')
    theme: Grade | None = None
    emotion: Grade | None = None
    music_vibe: Grade | None = None

    @model_validator(mode='after')
    def has_rating(self):
        if self.theme is None and self.emotion is None and self.music_vibe is None:
            raise ValueError('Califica al menos una escala')
        return self


class RecommendationRating(RatingScores):
    rater_id: RaterId
    release_id: str = Field(min_length=1, max_length=100)
    query_id: str = Field(min_length=1, max_length=100)
    candidate_id: str = Field(min_length=1, max_length=100)
    strategy: Literal['sgns', 'tfidf']
    rank: int = Field(ge=1, le=50)


class AudioRating(RatingScores):
    rater_id: RaterId
    query_id: int = Field(gt=0)
    candidate_id: int = Field(gt=0)


class SongRating(RatingScores):
    rater_id: RaterId
    query_id: str = Field(min_length=1, max_length=100)
    candidate_id: str = Field(min_length=1, max_length=100)
    rank: int = Field(default=0, ge=0, le=20)
