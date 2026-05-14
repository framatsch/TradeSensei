/**
 * help-content.ts — Single source of truth for all help/glossary content.
 *
 * Used by:
 *  - /help page (full glossary with TOC)
 *  - HelpTooltip component (summary + "Read more" link)
 *  - tools/export_help.ts (Markdown export)
 */

// ─── Types ────────────────────────────────────────────────────────────────────

export interface HelpEntry {
  id: string;
  label: string;
  summary: string;
  detail: string;
  formula?: string;
  good?: string;
  bad?: string;
}

export interface HelpSection {
  heading: string;
  entries: HelpEntry[];
}

// ─── Dictionary ───────────────────────────────────────────────────────────────

export const HELP_SECTIONS: HelpSection[] = [
  // ── Dashboard Metrics ────────────────────────────────────────────────────
  {
    heading: "Dashboard Metrics",
    entries: [
      {
        id: "net-pnl",
        label: "Net P&L",
        summary: "Your total realized profit or loss across all closed trades.",
        detail:
          "Net P&L is the sum of all individual trade outcomes after commissions and fees. A positive value means your account has grown; a negative value means it has shrunk. This is the single most direct measure of trading performance.",
        good: "Positive and growing over time.",
        bad: "Negative or declining — review your strategy and risk management.",
      },
      {
        id: "win-rate",
        label: "Win Rate",
        summary: "The percentage of your trades that closed with a profit.",
        detail:
          "A high win rate feels good psychologically but does not guarantee profitability — a 30% win rate can still be profitable if your average win is large enough relative to your average loss.",
        formula: "Win Rate = Winning Trades / Total Trades × 100",
        good: "Above 50% in most strategies, but context matters.",
        bad: "A very high win rate combined with a low profit factor may indicate you are cutting winners short and letting losers run.",
      },
      {
        id: "profit-factor",
        label: "Profit Factor",
        summary: "Gross Profit divided by Gross Loss.",
        detail:
          "Profit Factor tells you how many dollars of profit you earn for every dollar you lose. A value of 1.5 means you earn $1.50 for every $1.00 lost. This metric normalises for the number of trades and is more meaningful than Net P&L in isolation.",
        formula: "Profit Factor = Gross Profit / |Gross Loss|",
        good: "Above 1.5 is considered solid; above 2.0 is excellent.",
        bad: "Below 1.0 means you are losing money overall.",
      },
      {
        id: "max-drawdown",
        label: "Max Drawdown (Max DD)",
        summary:
          "The largest peak-to-trough decline in your account equity, expressed as a percentage.",
        detail:
          "Max Drawdown measures downside risk. It answers: 'What is the worst losing streak I have experienced?' A drawdown of -20% means your account fell 20% from a previous high before recovering. Lower is better.",
        formula: "Max DD = (Trough Value − Peak Value) / Peak Value × 100",
        good: "Below -20% is manageable for most traders.",
        bad: "A large Max DD relative to your average monthly return may mean you cannot psychologically stick to your strategy.",
      },
      {
        id: "avg-rrr",
        label: "Average RRR",
        summary: "Your average winner divided by your average loser.",
        detail:
          "Risk/Reward Ratio (RRR) compares how much you make on a typical winning trade versus how much you lose on a typical losing trade. An RRR of 1.5R means your average winner is 1.5× larger than your average loser. Combined with Win Rate, it determines your long-run expectancy.",
        formula: "Avg RRR = Avg Win / |Avg Loss|",
        good: "Above 1.0 — you make more per winner than you lose per loser.",
        bad: "Below 1.0 requires a very high win rate just to break even.",
      },
      {
        id: "gross-profit",
        label: "Gross Profit",
        summary: "Total dollar amount earned across all winning trades.",
        detail:
          "Gross Profit sums up every positive trade result before netting against losses. It shows the raw earning power of your winning trades. Compare it to Gross Loss to understand the balance between your wins and losses.",
        good: "High Gross Profit relative to Gross Loss gives a Profit Factor above 1.",
      },
      {
        id: "gross-loss",
        label: "Gross Loss",
        summary: "Total dollar amount lost across all losing trades.",
        detail:
          "Gross Loss sums up every negative trade result. It does not include commissions or fees — it reflects pure trade outcomes. A high Gross Loss compared to Gross Profit indicates your strategy needs improvement in either reducing loss size or increasing win size.",
        bad: "If Gross Loss consistently exceeds Gross Profit, reconsider position sizing and stop-loss placement.",
      },
      {
        id: "sharpe-ratio",
        label: "Sharpe Ratio",
        summary: "Risk-adjusted return — how much return you earn per unit of risk.",
        detail:
          "The Sharpe Ratio divides the average return of your trades by their standard deviation. A higher Sharpe means you are generating more return for each unit of volatility (risk) you take on. It allows you to compare two strategies even if they have different overall returns.",
        formula: "Sharpe = (Mean Return − Risk-Free Rate) / Std Dev of Returns",
        good: "≥ 2.0 Excellent · ≥ 1.0 Good · ≥ 0 Acceptable",
        bad: "Below 0 — you are taking on risk without being compensated for it.",
      },
    ],
  },

  // ── Performance Overview Charts ──────────────────────────────────────────
  {
    heading: "Performance Overview Charts",
    entries: [
      {
        id: "monthly-pnl",
        label: "Monthly PnL",
        summary: "Your net profit or loss broken down by calendar month.",
        detail:
          "Each bar represents the sum of all trades closed within a given month. Green bars indicate a profitable month; red bars indicate a losing month. Use this chart to identify seasonal patterns, consistent losing periods, or improving trends over time.",
        good: "Consistent green bars indicate a reliable edge. Look for a trend of increasing monthly PnL.",
        bad: "Large swings between months may indicate inconsistent position sizing or overtrading around specific events.",
      },
      {
        id: "pnl-by-asset-class",
        label: "PnL by Asset Class",
        summary: "Total profit or loss grouped by asset class (e.g. Equity, Option, Futures).",
        detail:
          "This chart lets you see at a glance which asset classes are driving your performance and which are dragging it down. If one class is consistently negative, it may be worth reviewing whether you have a genuine edge in that market.",
        good: "Focus and expertise in fewer asset classes often leads to better results.",
        bad: "Spreading across many classes without a clear edge dilutes your results.",
      },
      {
        id: "pnl-by-symbol",
        label: "PnL by Symbol",
        summary: "Total profit or loss grouped by individual ticker symbol.",
        detail:
          "Shows which specific instruments are contributing most to your gains or losses. A handful of symbols accounting for most of your profit (or loss) can indicate concentration risk or an over-reliance on a single setup.",
        good: "Profits spread across multiple symbols suggest a robust strategy.",
        bad: "If one symbol is responsible for the majority of your losses, review your approach to that instrument specifically.",
      },
      {
        id: "rolling-win-rate",
        label: "Rolling Win Rate",
        summary: "Win rate calculated over a sliding window of your most recent N trades.",
        detail:
          "Unlike the overall win rate, the rolling win rate shows how your consistency changes over time. A declining rolling win rate may signal strategy degradation or changed market conditions before it shows up in your overall statistics. Use the window selector (10 / 20 / 50 trades) to adjust the smoothing level.",
        good: "A rolling win rate that stays consistently above 50% indicates a stable edge.",
        bad: "A sharp drop in rolling win rate is an early warning sign to pause trading and review your setup.",
      },
      {
        id: "monthly-win-rate",
        label: "Monthly Win Rate",
        summary: "Percentage of winning trades within each calendar month.",
        detail:
          "Complements Monthly PnL by separating frequency (win rate) from magnitude (PnL). A month with high PnL but low win rate means a few large winners carried the month — which may or may not be sustainable. The 50% reference line helps you quickly spot below-average months.",
        good: "Consistent win rates above 50% month-over-month indicate a reliable process.",
        bad: "High variance between months (some very high, some very low) suggests your results depend too heavily on a small number of trades.",
      },
    ],
  },

  // ── Trade Details — Execution ─────────────────────────────────────────────
  {
    heading: "Trade Details — Execution",
    entries: [
      {
        id: "entry-price",
        label: "Entry Price",
        summary: "The price at which the position was opened.",
        detail:
          "The average fill price when you entered the trade. For options this is the premium paid or received per contract. Used to calculate gross P&L and return percentage.",
      },
      {
        id: "exit-price",
        label: "Exit Price",
        summary: "The price at which the position was closed.",
        detail:
          "The average fill price when you exited the trade. The difference between Exit Price and Entry Price (adjusted for direction) determines your raw profit or loss per unit.",
      },
      {
        id: "quantity",
        label: "Quantity",
        summary: "The number of shares, contracts, or units traded.",
        detail:
          "Combined with Entry and Exit Price, Quantity determines the total dollar value of the position. Larger quantity means greater exposure — both upside and downside.",
      },
      {
        id: "fees-commissions",
        label: "Fees / Commissions",
        summary: "Total transaction costs paid to your broker for this trade.",
        detail:
          "Includes brokerage commissions, exchange fees, and any other costs charged at entry and exit. Fees reduce your Net P&L. Even small per-trade fees compound significantly over many trades — track them carefully.",
        bad: "High fees relative to your average profit per trade can turn a theoretically profitable strategy into a losing one.",
      },
      {
        id: "stop-loss",
        label: "Stop Loss",
        summary: "The price at which you planned to exit if the trade moved against you.",
        detail:
          "A pre-defined exit level to limit your downside. The distance from Entry Price to Stop Loss defines your risk per share, which is used to calculate Initial Risk and Realized R. If no stop loss was set, risk-based metrics will show '—'.",
        good: "Always define a stop loss before entering a trade.",
        bad: "Trading without a stop loss makes risk management impossible and skews your R-based metrics.",
      },
      {
        id: "take-profit",
        label: "Take Profit",
        summary: "The price at which you planned to exit to lock in your target profit.",
        detail:
          "A pre-defined exit level for your profit target. Used together with Stop Loss to compute the Planned RRR. If no take profit was set, the Planned RRR will show '—'.",
      },
    ],
  },

  // ── Trade Details — Performance ───────────────────────────────────────────
  {
    heading: "Trade Details — Performance",
    entries: [
      {
        id: "realized-r",
        label: "Realized R",
        summary: "How many times your initial risk you actually made or lost on this trade.",
        detail:
          "R-multiples express your trade outcome relative to the risk you took. A result of +2R means you made twice your initial risk. A result of −1R means you lost your full planned risk. This metric normalises outcomes across trades of different sizes, making it the most useful measure for evaluating individual trade quality.",
        formula: "Realized R = Net P&L / Initial Risk",
        good: "+1R or better means the trade paid at least what you risked.",
        bad: "Large negative R values (e.g. −3R) indicate either a missed stop or a trade taken without a defined stop loss.",
      },
      {
        id: "planned-rrr",
        label: "Planned RRR",
        summary: "The reward-to-risk ratio you planned before entering the trade.",
        detail:
          "Planned RRR is calculated from your Stop Loss and Take Profit levels before the trade outcome is known. A Planned RRR of 1:2 means you intended to risk $1 to make $2. Compare this to your Realized R to see whether you achieved your target or exited early.",
        formula: "Planned RRR = (Take Profit − Entry) / (Entry − Stop Loss)",
        good: "A Planned RRR ≥ 1:2 gives you a mathematical edge even at win rates below 50%.",
      },
      {
        id: "initial-risk",
        label: "Initial Risk",
        summary: "The total dollar amount you put at risk when entering this trade.",
        detail:
          "Initial Risk is the maximum you could lose if price hit your stop loss immediately after entry. It is calculated as the distance from entry to stop loss multiplied by quantity. This is the foundation for all R-multiple calculations.",
        formula: "Initial Risk = |Entry Price − Stop Loss| × Quantity",
      },
      {
        id: "return-pct",
        label: "Return %",
        summary: "Percentage return on the capital deployed in this trade.",
        detail:
          "Return % measures the profit or loss relative to the total capital used to open the position. Unlike R-multiples, this reflects absolute capital efficiency — useful for comparing trades of different sizes or asset classes.",
        formula: "Return % = Net P&L / (Entry Price × Quantity) × 100",
      },
      {
        id: "gross-pnl-trade",
        label: "Gross P&L",
        summary: "Raw profit or loss from price movement only, before fees.",
        detail:
          "Gross P&L is purely the difference between your exit and entry prices multiplied by quantity, adjusted for trade direction (long/short). It does not include commissions or fees.",
        formula: "Gross P&L = (Exit Price − Entry Price) × Quantity  [for long trades]",
      },
      {
        id: "net-pnl-trade",
        label: "Net P&L (after fees)",
        summary: "Your actual realized profit or loss after all fees are deducted.",
        detail:
          "Net P&L = Gross P&L minus all commissions and fees. This is the real impact of the trade on your account balance. The difference between Gross and Net P&L highlights the cost of execution.",
        formula: "Net P&L = Gross P&L − Fees / Commissions",
      },
      {
        id: "holding-period",
        label: "Holding Period",
        summary: "How long the position was open, from entry to exit.",
        detail:
          "The time elapsed between your open and close timestamps. Holding period helps you understand your trading style — scalpers hold for seconds to minutes, swing traders for days to weeks. Comparing holding period against P&L can reveal whether longer holds are more or less profitable for your strategy.",
      },
    ],
  },

  // ── Playbooks ─────────────────────────────────────────────────────────────
  {
    heading: "Playbooks",
    entries: [
      {
        id: "playbook",
        label: "Playbook",
        summary: "A named trading strategy or setup that you apply repeatedly.",
        detail:
          "A Playbook is a reusable template for a specific trade setup — for example 'Breakout Pullback', 'Earnings Gap Fill', or 'Opening Range Breakout'. By tagging each trade with a Playbook you can measure which strategies are profitable, which are not, and how each one performs under different market conditions.",
        good: "Clearly defined, rules-based setups that you can execute without hesitation.",
        bad: "Too many overlapping playbooks makes attribution analysis noisy. Keep each one distinct.",
      },
      {
        id: "playbook-win-rate",
        label: "Playbook Win Rate",
        summary: "The percentage of trades tagged with this Playbook that closed in profit.",
        detail:
          "Breaking out win rate per Playbook reveals which setups have a genuine statistical edge and which are underperforming. A Playbook with a low win rate but high average R can still be net profitable — always look at both metrics together.",
        formula: "Playbook Win Rate = Winning Trades (this Playbook) / Total Trades (this Playbook) × 100",
      },
      {
        id: "playbook-pnl",
        label: "Playbook P&L",
        summary: "Net profit or loss summed across all trades using this Playbook.",
        detail:
          "The total monetary result of all trades attributed to a given Playbook. This is the primary indicator of whether a strategy is worth continuing. Compare it to your overall P&L to understand what fraction of your results each Playbook is responsible for.",
        good: "A consistently positive Playbook P&L across different time periods confirms a durable edge.",
        bad: "If a Playbook's P&L is negative but you keep using it, you are funding a strategy that costs you money.",
      },
      {
        id: "playbook-adherence",
        label: "Playbook Adherence",
        summary: "A self-assessed score for how closely you followed your own rules on a trade.",
        detail:
          "Logged on each daily Check-in, Playbook Adherence captures whether you executed your strategy as planned. Low adherence on winning trades can mask undisciplined trading — you may be getting lucky rather than following your edge. Tracking it over time reveals whether psychological or process issues are distorting your results.",
        good: "High adherence on profitable trades confirms your process is sound.",
        bad: "Winning trades with low adherence, or losing trades with high adherence, both deserve review.",
      },
    ],
  },

  // ── Market Check-in ───────────────────────────────────────────────────────
  {
    heading: "Market Check-in",
    entries: [
      {
        id: "daily-checkin",
        label: "Daily Check-in",
        summary: "A structured journal entry that captures your market context and mindset for the day.",
        detail:
          "A Daily Check-in is a snapshot of your trading day — covering your pre-market bias, the market phase you identified, which indices you were watching, any custom metrics you track (e.g. sleep quality, preparation score), and your post-session notes in Markdown. Linking trades to a Check-in allows the platform to break down performance by market conditions and psychological state.",
        good: "Consistent Check-ins build a rich dataset that reveals patterns between your mental state and trade outcomes.",
        bad: "Trades without a linked Check-in appear as 'Uncategorized' in attribution charts, reducing the quality of your performance analysis.",
      },
      {
        id: "market-phase",
        label: "Market Phase",
        summary: "A label you assign to describe the overall market environment for that day.",
        detail:
          "Market Phases are user-defined categories that describe the broader market regime — for example 'Trending Up', 'Choppy/Range', 'High Volatility', or 'News-Driven'. You configure your own phases in Settings and assign a colour to each. The mini calendar in the Check-in sidebar visualises which phase you tagged each trading day, making it easy to spot how your P&L correlates with market conditions.",
        good: "Defining clear phases and using them consistently lets you measure which conditions suit your strategy best.",
      },
      {
        id: "target-index",
        label: "Target Index",
        summary: "A market index you were monitoring as macro context for that trading day.",
        detail:
          "Target Indices (e.g. S&P 500, NASDAQ, DAX) are linked to a Check-in to record which benchmarks you were watching on a given day. Multiple indices can be tagged per Check-in. Each index has a TradingView URL configured in Settings — clicking the index badge on the timeline opens the chart in an external tab so you can review the market structure for that date. No live data is embedded in the app.",
      },
      {
        id: "checkin-custom-field",
        label: "Check-in Custom Field",
        summary: "A user-defined metric you track daily alongside your trades.",
        detail:
          "Custom Fields let you capture any quantitative or qualitative data point that matters to your process — for example 'Preparation (1–5)', 'Hours of Sleep', 'Confidence Level', or 'Rule Violations'. They appear as inputs on the daily Check-in form. Over time, correlating custom field values with P&L can surface non-obvious factors that affect your performance.",
        good: "Keep custom fields focused on things you can act on. If you cannot change the factor, tracking it adds little value.",
      },
      {
        id: "checkin-attribution",
        label: "Check-in Attribution",
        summary: "Performance breakdown grouped by market phase or psychological tag from your daily Check-ins.",
        detail:
          "Attribution charts in the Portfolio Workspace aggregate your trade results by the context captured in your Check-ins. For example, the Playbook Phase Heatmap shows P&L and win rate for each combination of Playbook and Market Phase. Trades that have no linked Check-in are grouped under 'Uncategorized' so they are never silently dropped from the analysis.",
        bad: "A large 'Uncategorized' group means many trades lack context data — complete your daily Check-ins consistently to get meaningful attribution.",
      },
    ],
  },

  // ── Overview Charts (Dashboard) ──────────────────────────────────────────
  {
    heading: "Overview Charts",
    entries: [
      {
        id: "equity-curve",
        label: "Equity Curve",
        summary: "A running total of your cumulative P&L plotted over time.",
        detail:
          "The Equity Curve shows how your account value grew or fell trade by trade (or day by day). A smooth, upward-sloping curve with shallow dips is the hallmark of a consistent strategy. Steep drops reveal periods of outsized losses or overtrading — use those regions as starting points for reviewing what changed.",
        good: "A steadily rising curve with small, short drawdown periods.",
        bad: "Deep dips followed by slow recoveries — re-evaluate position sizing and risk rules during those periods.",
      },
      {
        id: "daily-pnl",
        label: "Daily P&L",
        summary: "Your net profit or loss grouped by calendar day.",
        detail:
          "Each bar represents the total P&L of all trades that closed on a given day. This view helps you spot problematic trading days (e.g. revenge-trading after a loss) and identify which days of the week tend to be profitable or unprofitable for your strategy.",
        good: "Mostly green bars with occasional small red bars indicate controlled risk management.",
        bad: "A few large red days that wipe out many small green days — consider daily loss limits.",
      },
      {
        id: "return-distribution",
        label: "Return Distribution",
        summary: "A histogram showing how frequently each P&L range occurs across your trades.",
        detail:
          "The distribution of trade returns reveals the shape of your edge. A right-skewed distribution (long right tail) means occasional large wins. A left-skewed distribution means occasional large losses. A roughly bell-shaped distribution centred above zero is typical of a consistent, rule-based strategy.",
        good: "Positive mean with a right skew — more large wins than large losses.",
        bad: "Negative mean or heavy left tail — your average loser is larger than your average winner.",
      },
    ],
  },

  // ── Strategy Analysis ─────────────────────────────────────────────────────
  {
    heading: "Strategy Analysis",
    entries: [
      {
        id: "mae-mfe",
        label: "MAE / MFE",
        summary: "Maximum Adverse Excursion vs Maximum Favourable Excursion — a scatter plot of trade efficiency.",
        detail:
          "MAE (Maximum Adverse Excursion) is the largest unrealised loss a trade experienced before it closed. MFE (Maximum Favourable Excursion) is the largest unrealised gain. Plotting MAE on the X axis and MFE on the Y axis for every trade reveals how efficiently you enter and exit. Winning trades clustered in the top-left corner (low MAE, high MFE) indicate clean entries with little heat taken. Losing trades in the bottom-right (high MAE, low MFE) indicate entries that were wrong from the start.",
        good: "Winners with low MAE — your entries were correct and price moved in your favour immediately.",
        bad: "Winners with very high MAE — you held through large adverse moves, which is unsustainable and indicates poor entry timing.",
      },
      {
        id: "duration-vs-pnl",
        label: "Duration vs P&L",
        summary: "A scatter plot comparing how long you held a trade against its outcome.",
        detail:
          "Duration vs P&L reveals whether holding longer tends to help or hurt your results. Some strategies (trend-following) benefit from longer holds; others (mean-reversion, scalping) degrade with time. Look for clusters: if your losing trades are concentrated at long durations, you may be holding losers too long. If your winners are short and your losers are long, you have the classic 'cut winners, hold losers' problem.",
        good: "Winners spread across a range of durations with a slight positive correlation.",
        bad: "Losing trades concentrated at longer durations — you are holding losers longer than winners.",
      },
      {
        id: "r-multiple-distribution",
        label: "R-Multiple Distribution",
        summary: "A histogram of how many times your initial risk you made or lost on each trade.",
        detail:
          "R-Multiple Distribution groups all your trades by their Realized R outcome and shows how many trades fell into each bucket (e.g. how many were between 0R and +1R, how many were between −1R and 0R, etc.). The shape tells you whether your distribution of outcomes matches your planned strategy. A system with a Planned RRR of 1:2 should show few trades below −1R and many trades in the +1R to +3R range.",
        formula: "Realized R = Net P&L / Initial Risk",
        good: "Most trades clustered at or above your planned R target, with losses rarely exceeding −1R.",
        bad: "A large spike at −2R or lower indicates either missed stops or trades taken without a defined stop loss.",
      },
      {
        id: "payoff-ratio",
        label: "Payoff Ratio",
        summary: "Average winning trade divided by the absolute average losing trade.",
        detail:
          "The Payoff Ratio (also called the Win/Loss Ratio) measures the dollar magnitude of your average winner relative to your average loser. A Payoff Ratio of 1.5 means that when you win, you make 50% more than you lose on a typical losing trade. Unlike Profit Factor (which accounts for frequency), Payoff Ratio focuses purely on the size relationship between wins and losses.",
        formula: "Payoff Ratio = Avg Win / |Avg Loss|",
        good: "Above 1.0 — your winners are larger than your losers on average.",
        bad: "Below 1.0 requires a win rate above 50% just to break even.",
      },
    ],
  },

  // ── Time Analysis ─────────────────────────────────────────────────────────
  {
    heading: "Time Analysis",
    entries: [
      {
        id: "time-analysis",
        label: "Time Analysis",
        summary: "Performance broken down by time dimension — hour of day, weekday, month, or year.",
        detail:
          "The Time Analysis view groups your trades by when they occurred and calculates key metrics (P&L, win rate, profit factor, trade count) for each time bucket. This reveals systematic patterns in your trading: which hours of the day you perform best, whether you overtrade on Mondays, or whether your edge degrades in certain months. Use the resolution tabs (Hourly / Weekday / Monthly / Yearly) to switch the time dimension.",
        good: "Identifying your strongest time windows and concentrating activity there can significantly improve overall results.",
        bad: "Large negative P&L in specific hours or days may indicate you are trading outside your optimal conditions — consider avoiding those windows.",
      },
      {
        id: "profit-factor-time",
        label: "Profit Factor (by Time)",
        summary: "Gross Profit divided by Gross Loss for all trades within a given time bucket.",
        detail:
          "When viewed in the Time Analysis table, Profit Factor is calculated per time bucket (e.g. per weekday or per hour). This lets you compare the quality of your edge across different time windows, not just overall. A high Profit Factor in the morning session but near 1.0 in the afternoon suggests your edge is time-dependent.",
        formula: "Profit Factor = Gross Profit / |Gross Loss|  [for trades in that time bucket]",
      },
      {
        id: "avg-net-return",
        label: "Avg Net Return",
        summary: "Average net P&L per trade within a given time bucket.",
        detail:
          "Avg Net Return in the Time Analysis table shows you the expected dollar value per trade for a given time window, after fees. A positive value means that on average, trades taken in that window made money. Comparing Avg Net Return across time buckets reveals which periods are most productive per trade.",
        formula: "Avg Net Return = Total Net P&L (bucket) / Trade Count (bucket)",
      },
    ],
  },

  // ── Portfolios & Accounts ─────────────────────────────────────────────────
  {
    heading: "Portfolios & Accounts",
    entries: [
      {
        id: "portfolio",
        label: "Portfolio",
        summary: "A named workspace that groups one or more broker accounts for unified analysis.",
        detail:
          "A Portfolio is the top-level container for your trading activity. You can create multiple Portfolios — for example separating a live account from a paper-trading account, or grouping accounts by strategy. All charts, metrics, and Check-ins in the Portfolio Workspace are scoped to the selected Portfolio. Switch between Portfolios using the dropdown in the top bar.",
      },
      {
        id: "account",
        label: "Account",
        summary: "A single broker account linked to a Portfolio.",
        detail:
          "Each Account represents one brokerage account (e.g. an IBKR account or a Schwab account). You can import trades from an Account using file uploads (Flex Query or Schwab CSV). One Portfolio can contain multiple Accounts, and their trade history is merged for analysis.",
      },
      {
        id: "equity-curve",
        label: "Equity Curve",
        summary: "A time-series chart showing how your account balance grew or shrank over time.",
        detail:
          "The Equity Curve plots your cumulative P&L trade by trade (or day by day), giving you a visual representation of your performance history. A smooth, upward-sloping curve with shallow drawdowns is the hallmark of a consistent strategy. Large dips followed by slow recoveries signal periods of over-trading or strategy breakdown.",
        good: "A steadily rising curve with small, short drawdowns.",
        bad: "Deep, extended drawdowns followed by slow recoveries — re-evaluate position sizing and risk rules.",
      },
      {
        id: "import-source",
        label: "Import Source",
        summary: "The broker or file format used to bring trades into Trade Sensei.",
        detail:
          "Trade Sensei supports importing trade history from Interactive Brokers (IBKR Flex Query XML) and Charles Schwab (CSV). Imported trades are parsed, normalised into the platform's data model, and linked to the Account you select during the import. Re-importing the same file is safe — duplicates are detected and skipped.",
      },
    ],
  },
  {
    heading: "AI & MCP Integration",
    entries: [
      {
        id: "mcp-integration",
        label: "MCP Integration",
        summary:
          "Model Context Protocol (MCP) lets you connect AI agents like Claude or Gemini directly to your Trade Sensei data.",
        detail:
          "MCP is a standard bridge between AI clients and application tools. In Trade Sensei, MCP lets your AI agent discover your metadata schema, search trades with advanced filters, bulk-enrich trade metadata, and create strategy playbooks through authenticated tool calls.",
      },
      {
        id: "mcp-pat",
        label: "Personal Access Token (PAT)",
        summary:
          "A PAT is a one-time-visible secret token required to authenticate MCP clients against your account.",
        detail:
          "Generate a PAT from Settings -> API & Tokens before connecting any MCP client. The raw token value is shown only once at creation time, so copy it to a secure vault immediately. If it is lost, revoke it and generate a new token.",
      },
      {
        id: "mcp-ai-prompts",
        label: "AI Prompt Examples",
        summary:
          "Use these copy-paste prompts to get immediate value after connecting your AI client.",
        detail:
          "Performance review: 'Show me all losing trades from last week where Mood was below 5.'\n\nEnrichment: 'Tag my trades from May 6th 2026 afternoon with Macro Volatility and add a short note.'\n\nStrategy creation: 'Create a Breakout Momentum playbook from these rules: enter after first pullback, risk 1R, move stop to break-even after 1R.'\n\nPattern analysis: 'What is my win rate on LONG EQUITY trades in the first hour of the day?'",
      },
    ],
  },
];

// ─── Lookup helper ────────────────────────────────────────────────────────────

/** Find a single HelpEntry by its id anchor. Returns undefined if not found. */
export function findHelpEntry(id: string): HelpEntry | undefined {
  for (const section of HELP_SECTIONS) {
    const entry = section.entries.find((e) => e.id === id);
    if (entry) return entry;
  }
  return undefined;
}
