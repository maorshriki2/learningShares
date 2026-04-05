from __future__ import annotations

from market_intel.domain.entities.quiz import QuizQuestion
from market_intel.modules.portfolio.quiz_engine import QuizEngine


def next_quiz(engine: QuizEngine, context_tag: str | None = None) -> QuizQuestion:
    return engine.next_question(context_tag)
