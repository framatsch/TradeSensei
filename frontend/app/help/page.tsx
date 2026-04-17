/**
 * Help page — Metric glossary for the Trade Sensei.
 * Each section has an id anchor so MetricHelpLink can jump directly to it.
 * Layout: sticky TOC on the left, scrollable content on the right.
 */

import type { Metadata } from "next";
import { HelpClient } from "./HelpClient";

export const metadata: Metadata = {
  title: "Metric Reference — Trade Sensei",
};

// ─── Types ────────────────────────────────────────────────────────────────────

export interface MetricEntry {
  id: string;
  label: string;
  summary: string;
  detail: string;
  good?: string;
  bad?: string;
  formula?: string;
}

export interface Section {
  heading: string;
  entries: MetricEntry[];
}

// ─── Data ─────────────────────────────────────────────────────────────────────

const SECTIONS: Section[] = [
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
];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function HelpPage() {
  return <HelpClient sections={SECTIONS} />;
}
