from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


_DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "case_studies.json"


def _load_studies() -> list[dict[str, Any]]:
    with open(_DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


class CaseStudyEngine:
    def __init__(self) -> None:
        self._studies: list[dict[str, Any]] = _load_studies()

    def list_ids(self) -> list[str]:
        return [s["id"] for s in self._studies]

    def get_blind(self, study_id: str) -> dict[str, Any]:
        study = self._find(study_id)
        return {
            "id": study["id"],
            "codename": study["codename"],
            "year": study["year"],
            "sector": study["sector"],
            "price_at_snapshot": study["price_at_snapshot"],
            "financials_summary": study["financials_summary"],
            "piotroski_score": study["piotroski_score"],
            "altman_z": study["altman_z"],
            "altman_zone": study["altman_zone"],
            "price_chart_data": study["price_chart_data"],
        }

    def get_reveal(self, study_id: str, decision: str, explanation: str) -> dict[str, Any]:
        study = self._find(study_id)
        price_later = study["price_one_year_later"]
        price_now = study["price_at_snapshot"]
        actual_return_pct = (
            ((price_later - price_now) / price_now * 100) if price_now > 0 else -100.0
        )
        decision_correct = self._grade(decision, actual_return_pct)
        return {
            "id": study["id"],
            "reveal_name": study["reveal_name"],
            "outcome_label": study["outcome_label"],
            "price_at_snapshot": price_now,
            "price_one_year_later": price_later,
            "actual_return_pct": round(actual_return_pct, 1),
            "red_flags": study["red_flags"],
            "expert_analysis": study["expert_analysis"],
            "your_decision": decision,
            "your_explanation": explanation,
            "decision_correct": decision_correct,
            "grade_explanation": self._grade_text(decision, actual_return_pct, decision_correct),
        }

    def random_id(self) -> str:
        return random.choice(self._studies)["id"]

    def _find(self, study_id: str) -> dict[str, Any]:
        for s in self._studies:
            if s["id"] == study_id:
                return s
        raise KeyError(f"study_id not found: {study_id}")

    @staticmethod
    def _grade(decision: str, return_pct: float) -> bool:
        d = decision.lower()
        if "קנייה" in d or "buy" in d:
            return return_pct > 0
        if "שורט" in d or "short" in d or "מכירה" in d:
            return return_pct < -15
        return -10 < return_pct < 10

    @staticmethod
    def _grade_text(decision: str, return_pct: float, correct: bool) -> str:
        direction = "עלה" if return_pct >= 0 else "ירד"
        abs_r = abs(return_pct)
        outcome = f"המניה {direction} {abs_r:.0f}% בשנה שלאחר מכן."
        if correct:
            return f"✅ החלטה נכונה! {outcome}"
        else:
            return f"❌ החלטה שגויה. {outcome} שים לב לנורות האדומות שזוהו."
