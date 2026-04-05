from __future__ import annotations

import random

from market_intel.domain.entities.quiz import QuizQuestion


def build_default_quiz_bank() -> list[QuizQuestion]:
    return [
        QuizQuestion(
            id="pe_eps_1",
            prompt="P/E fell while EPS grew. What is a plausible interpretation?",
            choices=[
                "Price fell faster than earnings improved",
                "EPS always moves P/E in the same direction",
                "P/E cannot change if EPS grows",
                "The company must be unprofitable",
            ],
            correct_index=0,
            explanation="P/E is price divided by EPS. If EPS rises but price falls (or rises slower), P/E compresses.",
            context_tag="valuation",
            difficulty="medium",
        ),
        QuizQuestion(
            id="wacc_dcf_1",
            prompt="Increasing WACC in a DCF, holding cash flows constant, tends to:",
            choices=[
                "Increase intrinsic value",
                "Decrease intrinsic value",
                "Leave intrinsic value unchanged",
                "Only affect revenue growth",
            ],
            correct_index=1,
            explanation="Higher discount rates reduce present value of future cash flows.",
            context_tag="dcf",
            difficulty="easy",
        ),
        QuizQuestion(
            id="insider_1",
            prompt="Clustered open-market insider buying near lows may suggest:",
            choices=[
                "Guaranteed near-term rally",
                "Insiders see value, but information may be incomplete",
                "SEC filings are always noise",
                "Insiders cannot trade their stock",
            ],
            correct_index=1,
            explanation="Insider buys are a sentiment signal, not a certain outcome; context and structure matter.",
            context_tag="governance",
            difficulty="medium",
        ),
        QuizQuestion(
            id="rsi_1",
            prompt="RSI near 70 in a strong uptrend often indicates:",
            choices=[
                "Automatic reversal tomorrow",
                "Momentum strength; overbought is not always a sell signal alone",
                "The stock must be delisted",
                "Volume is always declining",
            ],
            correct_index=1,
            explanation="RSI is bounded momentum; regime and trend context matter for interpretation.",
            context_tag="technical",
            difficulty="hard",
        ),
    ]


def pick_quiz_for_context(tag: str | None) -> QuizQuestion | None:
    bank = build_default_quiz_bank()
    if tag:
        filtered = [q for q in bank if q.context_tag == tag]
        if filtered:
            return random.choice(filtered)
    return random.choice(bank)
