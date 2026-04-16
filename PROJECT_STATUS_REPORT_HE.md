# דוח מצב פרויקט — learningShares

תאריך: 2026-04-16 (עודכן אוטומטית)  
פרויקט: learningShares (לשעבר Market-Intel)  
Stack: FastAPI + Streamlit  
מקור קוד: GitHub — `maorshriki2/learningShares` (ענף `main`)

## מצב כללי

המערכת פעילה. ה־UI עודכן כך שמוצגים למשתמש רק דפים רלוונטיים דרך ניווט סיידבר ייעודי, בלי לגעת בחישובים/דאטה.  
המטרה: למידה מקצועית של שוק ההון בצורה פשוטה, מדורגת ואינטראקטיבית.

דפי UI קיימים (Streamlit) תחת `src/market_intel/ui/pages/`:
- `02_Watchlist.py`
- `03_Fundamental_AGENT.py` (מעטפת שמרנדרת מסך קיים)
- `04_NEWS_AGENT.py` (מעטפת שמרנדרת מסך קיים)
- `05_TECHNICAL_AGENT.py` (מעטפת שמרנדרת מסך קיים)
- `06_FINAL_VERDICT_LEARNING_AGENT.py` (מעטפת שמרנדרת מסך קיים)
- `90_Portfolio_Quiz.py`
- `92_Blind_Test.py`

ניווט סיידבר (UI/UX):
- מציג רק: `Favorite Stocks`, `Watchlist`, `Fundamental AGENT`, `NEWS AGENT`, `TECHNICAL AGENT`, `FINAL VERDICT LEARNING AGENT`
- תחת **More**: `Portfolio Quiz`, `Blind Test`
- הקבצים של מסכי ה־Agent (ה־UI שהועבר מהעמודים הישנים) נמצאים תחת `src/market_intel/ui/screens/agents/`

עמודי UI ישנים שהוסרו מהתצוגה (נמחקו מ־`src/market_intel/ui/pages/` כדי שלא יופיעו כטאבים ב־Streamlit):
- `01_Start_Here.py`
- `03_Charting_Lab.py`
- `04_Fundamentals_Valuation.py`
- `05_Governance_Sentiment.py`
- `06_Peer_Comparison.py`
- `07_Valuation_Verdict.py`
- `08_Stock_360_View.py`
- `09_Chart_Technical_Verdict.py`
- `10_Market_Context_Feed.py`
- `91_Macro_Simulation.py`
- `93_Blind_CSV_Import.py`

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
| ניווט סיידבר | `src/market_intel/ui/components/sidebar_nav.py` |
| מסכי Agent (UI) | `src/market_intel/ui/screens/agents/fundamental.py`, `src/market_intel/ui/screens/agents/news.py`, `src/market_intel/ui/screens/agents/technical.py`, `src/market_intel/ui/screens/agents/final_verdict.py` |
| מעטפות Agent (דפי Streamlit) | `src/market_intel/ui/pages/03_Fundamental_AGENT.py`, `src/market_intel/ui/pages/04_NEWS_AGENT.py`, `src/market_intel/ui/pages/05_TECHNICAL_AGENT.py`, `src/market_intel/ui/pages/06_FINAL_VERDICT_LEARNING_AGENT.py` |
| טווחי זמן (כולל שבוע/חודש) | `domain/value_objects/timeframe.py`, `infrastructure/market_data/historical_bars.py` |
| Watchlist + יקום טיקרים | `src/market_intel/ui/pages/02_Watchlist.py`, `src/market_intel/ui/components/watchlist_universe.py` |
| Summary API (מחיר/Market Cap/Vol/Beta) | `src/market_intel/api/routers/instruments.py`, `src/market_intel/application/dto/instrument_dto.py` |

## תיקונים ושיפורים אחרונים (תמצית)

- 2026-04-16 — UI/UX: ניווט סיידבר חדש + מעבר למסכי `screens/agents` + מעטפות Agent נקיות ב־`ui/pages` + הסתרת עמודי UI ישנים ע"י הסרה מ־`ui/pages` (ללא שינוי חישובים/דאטה)
- 2026-04-09 — test eap fix
- 2026-04-09 — test script stderr fix
- 2026-04-09 — Initial commit: learningShares project and git helper scripts
- 2026-04-09 — Market Intel: API routes, UI pages, watchlist fallback, analytics modules
- 2026-04-05 — Initial commit

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
   - `Watchlist` (או לבחור מסך מתוך הסיידבר)

## הערה

אם אתה רוצה, אפשר להפיק את אותו הדוח גם ל־PDF/HTML.
