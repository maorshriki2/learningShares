from __future__ import annotations

from dataclasses import dataclass, field

from market_intel.domain.entities.quiz import QuizQuestion
from market_intel.modules.portfolio.quiz_bank import pick_quiz_for_context


@dataclass
class QuizEngine:
    last_question: QuizQuestion | None = None
    last_answer_index: int | None = None
    score: int = 0
    attempts: int = 0
    history: list[tuple[str, bool]] = field(default_factory=list)

    def next_question(self, context_tag: str | None = None) -> QuizQuestion:
        q = pick_quiz_for_context(context_tag)
        if q is None:
            raise RuntimeError("Quiz bank empty")
        self.last_question = q
        self.last_answer_index = None
        return q

    def answer(self, choice_index: int) -> tuple[bool, str]:
        if self.last_question is None:
            raise RuntimeError("No active question")
        ok = choice_index == self.last_question.correct_index
        self.attempts += 1
        if ok:
            self.score += 1
        self.history.append((self.last_question.id, ok))
        explanation = self.last_question.explanation
        self.last_answer_index = choice_index
        return ok, explanation
