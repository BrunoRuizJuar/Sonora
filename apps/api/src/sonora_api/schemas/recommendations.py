"""Request contract for future recommendation endpoints."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    track_id: str = Field(min_length=1)
    mode: Literal["lyrics", "audio", "mixed"] = "lyrics"
    lyrics_weight: float = Field(default=0.5, ge=0, le=1, allow_inf_nan=False)
    exploration: float = Field(default=0.2, ge=0, le=1, allow_inf_nan=False)
    top_k: int = Field(default=10, ge=1, le=50)
    max_per_artist: int = Field(default=1, ge=1, le=50)
    exclude_known_covers: bool = True
    seed: int = Field(default=42, ge=0, le=2**32 - 1)

    @property
    def effective_weights(self) -> tuple[float, float]:
        if self.mode == "lyrics":
            return (1.0, 0.0)
        if self.mode == "audio":
            return (0.0, 1.0)
        return (self.lyrics_weight, 1.0 - self.lyrics_weight)
