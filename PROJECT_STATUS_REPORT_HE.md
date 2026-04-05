# דוח מצב פרויקט — learningShares

תאריך: 2026-04-05  
פרויקט: learningShares (לשעבר Market-Intel)  
Stack: FastAPI + Streamlit

## מצב כללי

המערכת פעילה ומורכבת מ־7 דפי תוכן + דף התחלה למתחילים (`00_Start_Here`).  
המטרה: למידה מקצועית של שוק ההון בצורה פשוטה, מדורגת ואינטראקטיבית.

## יכולות עיקריות

1. **Charting Lab**
   - גרף נרות Plotly (ריבוי פאנלים: מחיר, RSI, MACD)
   - אינדיקטורים: RSI, MACD, VWAP, Ichimoku, Fibonacci
   - זיהוי תבניות
   - **מסגרות זמן:** `1m` … `1h`, `1d`, **`1wk`**, **`1mo`** (ממופה ל־yfinance)
   - סטרים WebSocket
   - **שכבת הסבר:** מדריך ב־expander + פרשנות מספרית לנר האחרון + בלוק «בתכלס» (שלב במסע בחלון, גבולות מה אפשר להסיק לגבי מומנטום — לא תחזית)

2. **Fundamentals & Valuation**
   - דוחות כספיים היסטוריים (טאבים: Income / Balance / Cash Flow מ־SEC XBRL)
   - DCF אינטראקטיבי
   - WACC, ROIC, Piotroski, Altman Z
   - **שכבת הסבר:** expanderים — איך לקרוא מדדים+DCF, ואיך לקרוא את שלושת הדוחות; **בלוק דינמי** «בתכלס» לפי הנתונים שנטענו (ROIC מול WACC, ציונים, MOS, מגמות Revenue/Net Income)

3. **Governance & Sentiment**
   - SEC filings (8-K, Form 4)
   - Insider activity
   - FinBERT sentiment

4. **Portfolio & Quizzes**
   - Paper trading (Buy/Sell/Reset)
   - Alpha מול מדד
   - **הסבר לגרף ההשוואה:** expander + פרשנות דינמית לפי הנתונים
   - חידוני למידה כלליים וקונטקסטואליים

5. **Peer Comparison**
   - השוואת מתחרים לפי P/E, EV/EBITDA, margins, growth
   - ממוצע קבוצה + ניתוח אוטומטי (בולטים)
   - **שכבת הסבר:** expander מלא על המכפילים והטבלה; **בלוק «בתכלס»** — דירוג יחסי של החברה מול המתחרים והממוצע מהמסך

6. **Macro & WACC Simulation**
   - ריביות FRED + גרף היסטוריית תשואת 10 שנים
   - סימולציית השפעת ריבית על WACC ושווי
   - **הסברים:** expanderים + פרשנות דינמית לגרף התשואות; מדריך לגרפי הסימולציה אחרי הרצה

7. **Blind Test**
   - תרחישי ניתוח היסטוריים ללא שם חברה
   - החלטה + Reveal + משוב
   - **הסבר:** expander + פרשנות דינמית לגרף המחיר היחסי

## שכבת למידה והנגשה

- Mentor Blocks בכל עמוד (What / How / Signals)
- **מדריכי קריאה (expanders)** ליד גרפים ומסכי טבלאות — `chart_reading_guide` + מפתחות ייעודיים ל־Fundamentals / Peers
- **פרשנות דינמית «בתכלס»** — רכיבים: `chart_snapshot_narrative`, `financial_snapshot_narrative` (מספרים וניסוח לפי payload בפועל)
- Tooltips / מילון מונחים (`glossary`) לפי עמוד
- Active Recall checkpoints
- Guided Learning sidebar checklist
- דף `Start Here` שמסכם החלטה בשפה פשוטה

## מימוש טכני (רכיבי UI רלוונטיים)

| אזור | קבצים עיקריים |
|------|----------------|
| מדריכי טקסט | `src/market_intel/ui/components/chart_reading_guide.py` |
| פרשנות גרפים / משטר מחיר | `src/market_intel/ui/components/chart_snapshot_narrative.py` |
| פרשנות פונדמנטלים / peers | `src/market_intel/ui/components/financial_snapshot_narrative.py` |
| טווחי זמן (כולל שבוע/חודש) | `domain/value_objects/timeframe.py`, `infrastructure/market_data/historical_bars.py` |

## תיקונים ושיפורים אחרונים (תמצית)

- תוקן כשל `400` בדף Governance באמצעות fallback בטוח לנתוני חוץ ו-cache parsing.
- תוקן bug של סימבול ריק שיצר קריאות `/market//ohlcv`.
- תוקן סנכרון סימבול בין עמודים למניעת "נתונים של מניה קודמת".
- הוסרו אזהרות `use_container_width` (הוחלף ל־`width="stretch"`).
- הרחבת הסברים ופרשנות דינמית ב־Charting, Macro, Portfolio, Blind Test, **Fundamentals**, **Peers**; הוספת timeframes `1wk` / `1mo`.

## בדיקת API (Smoke)

הנתיבים הבאים נבדקו ומחזירים `200`:

- `/api/v1/health`
- `/api/v1/market/AAPL/ohlcv`
- `/api/v1/fundamentals/AAPL/dashboard`
- `/api/v1/governance/AAPL/dashboard`
- `/api/v1/peers/AAPL`
- `/api/v1/macro/rates`
- `/api/v1/portfolio/`
- `/api/v1/blindtest/list`

## הנחיות הרצה

1. הרצה אחת (API + ממשק יחד):
   - `python scripts/run_app.py`
2. Windows (אופציונלי): EXE דרך `learningSharesDesktop.spec`; מתקין דרך `scripts/build_windows_installer.ps1` → `installer_output/`.
3. להתחיל מ:
   - `00_Start_Here`

## הערה

אם אתה רוצה, אפשר להפיק את אותו הדוח גם ל־PDF/HTML.
