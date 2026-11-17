from typing import Literal
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
