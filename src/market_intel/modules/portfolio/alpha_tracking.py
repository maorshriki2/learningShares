from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf


@dataclass(frozen=True)
class AlphaSnapshot:
    date: str
    portfolio_return_pct: float
    spy_return_pct: float
    alpha_pct: float


async def fetch_benchmark_returns(
    benchmark: str = "SPY",
    lookback_days: int = 365,
) -> pd.DataFrame:
    def _sync() -> pd.DataFrame:
        t = yf.Ticker(benchmark)
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=lookback_days + 5)
        df = t.history(start=start, end=end, interval="1d", auto_adjust=True)
        if df.empty:
            return df
        df = df[["Close"]].rename(columns={"Close": "close"})
        df["pct_return"] = df["close"].pct_change() * 100.0
        df.index = pd.to_datetime(df.index)
        return df

    return await asyncio.to_thread(_sync)


async def compute_alpha_series(
    portfolio_start_value: float,
    portfolio_current_value: float,
    portfolio_inception_date: datetime,
    benchmark: str = "SPY",
) -> dict[str, object]:
    spy_df = await fetch_benchmark_returns(benchmark, lookback_days=365)
    days_held = (datetime.now(timezone.utc) - portfolio_inception_date.replace(tzinfo=timezone.utc if portfolio_inception_date.tzinfo is None else portfolio_inception_date.tzinfo)).days
    if portfolio_start_value <= 0:
        portfolio_total_return = 0.0
    else:
        portfolio_total_return = (portfolio_current_value - portfolio_start_value) / portfolio_start_value * 100.0

    spy_total_return = 0.0
    if not spy_df.empty and len(spy_df) > 1:
        first_close = float(spy_df["close"].iloc[0])
        last_close = float(spy_df["close"].iloc[-1])
        if first_close > 0:
            spy_total_return = (last_close - first_close) / first_close * 100.0

    alpha = portfolio_total_return - spy_total_return
    spy_dates = spy_df.index.strftime("%Y-%m-%d").tolist() if not spy_df.empty else []
    spy_values: list[float] = []
    if not spy_df.empty and len(spy_df) > 0:
        base = float(spy_df["close"].iloc[0])
        spy_values = [round(float(v) / base * portfolio_start_value, 2) for v in spy_df["close"]]

    return {
        "portfolio_total_return_pct": round(portfolio_total_return, 2),
        "spy_total_return_pct": round(spy_total_return, 2),
        "alpha_pct": round(alpha, 2),
        "days_measured": max(days_held, 1),
        "benchmark": benchmark,
        "spy_dates": spy_dates,
        "spy_normalized_values": spy_values,
        "outperforming": alpha > 0,
    }


def generate_contextual_quiz(
    positions: list[dict[str, object]],
    prices: dict[str, float],
) -> list[dict[str, object]]:
    questions: list[dict[str, object]] = []
    for pos in positions[:3]:
        sym = str(pos.get("symbol", ""))
        last_px = float(prices.get(sym) or pos.get("last_price") or 0)
        avg_cost = float(pos.get("avg_cost") or 0)
        if last_px <= 0 or avg_cost <= 0:
            continue
        change_pct = (last_px - avg_cost) / avg_cost * 100.0
        if abs(change_pct) < 5:
            questions.append(
                {
                    "id": f"ctx_{sym}_flat",
                    "prompt": f"המניה {sym} שבתיק שלך עלתה פחות מ-5% מהקנייה. מה המשמעות?",
                    "choices": [
                        "הייתה טעות קנייה",
                        "השוק עדיין מגלה את הערך, או שהקטליסטורים עדיין לא מימשו",
                        "חייבים למכור מיד",
                        "P/E מתחת לממוצע בהגדרה",
                    ],
                    "correct_index": 1,
                    "explanation": f"תנועה קטנה לאחר כניסה אינה בהכרח שלילית — ייתכן שהשוק עוד לא מגלם את ה-thesis שלך. חשוב לבדוק אם הפונדמנטלים עדיין תקפים.",
                    "context_tag": "portfolio",
                }
            )
        elif change_pct > 20:
            questions.append(
                {
                    "id": f"ctx_{sym}_up",
                    "prompt": f"מניית {sym} בתיק שלך עלתה {change_pct:.0f}% מהקנייה. מה כדאי לבדוק עכשיו?",
                    "choices": [
                        "למכור מיד — רווח לוקים",
                        "לבדוק אם שווי השוק עדיין מציג מרג'ין ביטחון",
                        "להכפיל את הפוזיציה כי היא עולה",
                        "להמתין לדיבידנד",
                    ],
                    "correct_index": 1,
                    "explanation": "כשמניה עלתה משמעותית, חשוב לחזור ל-DCF ולבדוק: האם המחיר הנוכחי כבר גבוה מהשווי ההוגן? מה ה-Margin of Safety הנוכחי?",
                    "context_tag": "portfolio",
                }
            )
        elif change_pct < -15:
            questions.append(
                {
                    "id": f"ctx_{sym}_down",
                    "prompt": f"מניית {sym} ירדה {abs(change_pct):.0f}% מהקנייה. מה השאלה הראשונה?",
                    "choices": [
                        "האם הפונדמנטלים השתנו לרעה, או רק המחיר ירד?",
                        "מיד לצאת להפסד",
                        "להכפיל פוזיציה ללא בדיקה",
                        "לבדוק רק את הגרף הטכני",
                    ],
                    "correct_index": 0,
                    "explanation": "ירידת מחיר ≠ ירידה בערך. השאלה הקריטית: האם המניפסט המקורי לקנייה עדיין תקף? אם הפונדמנטלים לא השתנו, ירידה יכולה להיות הזדמנות. אם הנתונים השתנו — צא.",
                    "context_tag": "portfolio",
                }
            )
    return questions
