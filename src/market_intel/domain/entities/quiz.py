from typing import Literal

from pydantic import BaseModel, Field


class QuizQuestion(BaseModel):
    id: str
    prompt: str
    choices: list[str] = Field(min_length=2)
    correct_index: int = Field(..., ge=0)
    explanation: str
    context_tag: str = ""
    difficulty: Literal["easy", "medium", "hard"] = "medium"
