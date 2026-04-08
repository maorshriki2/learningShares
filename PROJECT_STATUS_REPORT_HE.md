# דוח מצב פרויקט — learningShares

תאריך: 2026-04-06 (עודכן)  
פרויקט: learningShares (לשעבר Market-Intel)  
Stack: FastAPI + Streamlit  
מקור קוד: GitHub — `maorshriki2/learningShares` (ענף `main`)

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
   - **פורנזיקה חשבונאית (דגלים אדומים):** סריקת payload פונדמנטלי — איכות רווחים (רווח נקי מול CFO), מגמת DSO, Beneish M-Score (כשהנתונים מאפשרים). מוצג בלוק **«אזהרות אנליסט»** אוטומטי בדף הפונדמנטלים.
   - **מטריצת רגישות DCF (Stress Test):** ב־Backend — רשת WACC (±2 נק׳ אחוז) × צמיחה טרמינלית (±1 נק׳ אחוז); ב־UI — **Heatmap Plotly** של שווי הוגן למניה לפי תרחישים (השוואה למחיר השוק כשזמין).
   - **שכבת הסבר:** expanderים — איך לקרוא מדדים+DCF, ואיך לקרוא את שלושת הדוחות; **בלוק דינמי** «בתכלס» לפי הנתונים שנטענו (ROIC מול WACC, ציונים, MOS, מגמות Revenue/Net Income)

3. **Governance & Sentiment**
   - SEC filings (8-K, Form 4)
   - Insider activity
   - FinBERT sentiment
   - **לשונית «Analyst Narrative»:** סיכום נרטיבי של שיחת הרווחים (טרנסקריפט מ־Finnhub כשמוגדר מפתח / אחרת דמו) באמצעות **Claude** (דרך Backend; דורש `ANTHROPIC_API_KEY`). פלט: שלוש חוזקות, שלושה סיכונים/ניסוחים מגוננים, והשוואת סנטימנט מול הרבעון הקודם.

4. **Portfolio & Quizzes**
   - Paper trading (Buy/Sell/Reset)
   - Alpha מול מדד
   - **הסבר לגרף ההשוואה:** expander + פרשנות דינמית לפי הנתונים
   - חידוני למידה כלליים וקונטקסטואליים

5. **Peer Comparison**
   - השוואת מתחרים לפי P/E, EV/EBITDA, margins, growth
   - **Z-Score** ל־P/E ול־EV/EBITDA ביחס לקבוצת ההשוואה (בטבלה)
   - **גרף פיזור (Scatter):** צמיחת הכנסות (%) מול P/E — הדגשת המניה הנבחרת
   - ממוצע קבוצה + ניתוח אוטומטי (בולטים)
   - **שכבת הסבר:** expander מלא על המכפילים והטבלה; **בלוק «בתכלס»** — דירוג יחסי, Z-scores, וניסוח פרמיה/הנחה מול צמיחה (למשל פרמיה על הממוצע מול צמיחה מהירה יחסית)

6. **Macro & WACC Simulation**
   - ריביות FRED + גרף היסטוריית תשואת 10 שנים
   - סימולציית השפעת ריבית על WACC ושווי
   - **הסברים:** expanderים + פרשנות דינמית לגרף התשואות; מדריך לגרפי הסימולציה אחרי הרצה

7. **Blind Test**
   - תרחישי ניתוח היסטוריים ללא שם חברה
   - החלטה + Reveal + משוב
   - **הסבר:** expander + פרשנות דינמית לגרף המחיר היחסי

8. **Watchlist (סקטורים + Large/Mid/Small)**
   - עמוד Watchlist שמרכז **סקטורים/תמות** ומציג **Top 5** בכל קבוצת שווי שוק: **Large Cap / Mid Cap / Small Cap**
   - לכל מניה מוצגים: **Ticker**, **Market Cap**, **Price**, **Volatility (1Y)** (תנודתיות שנתית ממוצעת, annualized), **Beta**
   - כפתור **"ניתוח"** לכל מניה: מריץ בזמן אמת את המודלים הקיימים (טכני + פונדמנטלי + peers)

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
| פרשנות פונדמנטלים / peers + אזהרות פורנזיקה | `src/market_intel/ui/components/financial_snapshot_narrative.py` |
| פורנזיקה (Backend) | `src/market_intel/modules/fundamentals/forensics/forensic_analyzer.py` |
| מטריצת DCF (Backend) | `src/market_intel/modules/fundamentals/valuation/dcf_sensitivity.py` |
| דשבורד פונדמנטלים (אינטגרציה) | `src/market_intel/application/services/fundamentals_service.py` |
| נרטיב אנליסט (Claude) | `src/market_intel/application/services/governance_service.py`, `api/routers/governance.py` |
| Z-scores ב־peers | `src/market_intel/api/routers/peers.py` |
| UI: heatmap DCF / טאב נרטיב / scatter peers | `ui/pages/02_Fundamentals_Valuation.py`, `03_Governance_Sentiment.py`, `05_Peer_Comparison.py` |
| טווחי זמן (כולל שבוע/חודש) | `domain/value_objects/timeframe.py`, `infrastructure/market_data/historical_bars.py` |
| Watchlist + יקום טיקרים | `src/market_intel/ui/pages/09_Watchlist.py`, `src/market_intel/ui/components/watchlist_universe.py` |
| Summary API (מחיר/Market Cap/Vol/Beta) | `src/market_intel/api/routers/instruments.py`, `src/market_intel/application/dto/instrument_dto.py` |

## תיקונים ושיפורים אחרונים (תמצית)

- תוקן כשל `400` בדף Governance באמצעות fallback בטוח לנתוני חוץ ו-cache parsing.
- תוקן bug של סימבול ריק שיצר קריאות `/market//ohlcv`.
- תוקן סנכרון סימבול בין עמודים למניעת "נתונים של מניה קודמת".
- הוסרו אזהרות `use_container_width` (הוחלף ל־`width="stretch"`).
- הרחבת הסברים ופרשנות דינמית ב־Charting, Macro, Portfolio, Blind Test, **Fundamentals**, **Peers**; הוספת timeframes `1wk` / `1mo`.
- **פורנזיקה:** מנוע דגלים אדומים + בלוק «אזהרות אנליסט» בפונדמנטלים.
- **DCF:** מטריצת רגישות (WACC × צמיחה טרמינלית) + heatmap ב־Streamlit.
- **Governance:** endpoint ולשונית Analyst Narrative (Claude + טרנסקריפט); הגדרות `anthropic_api_key` / `anthropic_model` ב־`settings`.
- **Peers:** Z-scores בטבלה, scatter צמיחה–P/E, הרחבת נרטיב «בתכלס».
- **Watchlist:** עמוד חדש לפי סקטור + Large/Mid/Small, כולל endpoint ייעודי לסיכום מניה (מחיר, שווי שוק, בטא, תנודתיות 1Y) וכפתור "ניתוח" שמריץ טכני+פונדומנטלי+Peers בזמן אמת.
- **DevOps / Git:** `.gitignore` סטנדרטי (venv, `__pycache__`, `.env`, קבצי OS); הריפו מאותחל ומקושר ל־GitHub; commit ראשון ו־`main` נדחף ל־`origin`.

## בדיקת API (Smoke)

הנתיבים הבאים נבדקו ומחזירים `200`:

- `/api/v1/health`
- `/api/v1/market/AAPL/ohlcv`
- `/api/v1/fundamentals/AAPL/dashboard`
- `/api/v1/governance/AAPL/dashboard`
- `/api/v1/governance/AAPL/analyst-narrative` (דורש מפתח Anthropic לתוצאה מלאה)
- `/api/v1/peers/AAPL`
- `/api/v1/instruments/AAPL/summary`
- `/api/v1/macro/rates`
- `/api/v1/portfolio/`
- `/api/v1/blindtest/list`

## הנחיות הרצה

1. העתקת סביבה: העתק `.env.example` ל־`.env` ומלא מפתחות לפי הצורך (`ANTHROPIC_API_KEY`, Finnhub וכו').
2. הרצה אחת (API + ממשק יחד):
   - `python scripts/run_app.py`
3. Windows (אופציונלי): EXE דרך `learningSharesDesktop.spec`; מתקין דרך `scripts/build_windows_installer.ps1` → `installer_output/`.
4. להתחיל מ:
   - `00_Start_Here`

## הערה

אם אתה רוצה, אפשר להפיק את אותו הדוח גם ל־PDF/HTML.
