# DESIGN.md — VisioTrade Performance-First UI System

**Version:** 2.0 (Zero-Blur · 60 FPS)\
**Modi:** Light Mode (*Pure White*) & Dark Mode (*Layered Anthracite*)\
**Akzent-System:** Solid Amber CTAs · Soft-Orange Selektion (ohne Gelbstich) · Leuchtendes Signal-Grün\
**Zielgruppe:** Frontend-Implementierung (Next.js / Tailwind CSS) & Coding-Agenten (Opus, Sonnet, DeepSeek)

---

## 1. Design-Philosophie & oberste Performance-Regel

Dieses Designsystem folgt strikt dem Grundsatz **Performance vor Effekten**:

1. **Zero-Blur · 60 FPS (Non-Negotiable):**
   * **KEIN `backdrop-filter: blur(...)`**, **KEIN `backdrop-saturate`**, **KEINE Ambient-Hintergrund-Orbs** und **KEINE schweren Multi-Layer-`box-shadow`s**.
   * Alle Oberflächen sind **100 % deckend (opaque)**. Die visuelle Tiefe entsteht ausschließlich durch sauber abgestuftes **3-Ebenen-Tonal-Layering** und scharfe `1px`-Hairline-Borders.
   * Dadurch bleibt das Scrollen durch große Watchlists (80+ Symbole), Live-SSE-Updates und Chart-Zooming auf jedem Gerät permanent bei **60 FPS**.
2. **90 % ruhige Neutralität / 10 % präzises Marktsignal:**
   * Kein generisches SaaS-Blau (`blue-*`, `indigo-*`, `sky-*` sind verboten).
   * Farbe gehört primär den Marktdaten (**Leuchtendes Grün** für Profit / +GEX / Edge, **Stress-Rose** für Verlust / −GEX / Stress) sowie klaren **Solid-Amber-CTAs** für echte Primäraktionen.
3. **Klares Weiß im Light Mode, gestuftes Anthrazit im Dark Mode:**
   * Im **Light Mode (*Pure White*)** liegen Top-Bar, Sidebar und Haupt-Panels in knackigem `#FFFFFF` auf einem ultraleichten `#F8F9FB`-Canvas (kein passiver Grauschleier).
   * Im **Dark Mode (*Layered Anthracite*)** wird reines `#000000` vermieden. Stattdessen heben sich `#191E28`-Panels und `#222936`-Sub-Cards plastisch vom `#11141B`-Schiefer-Anthrazit-Canvas ab.

---

## 2. Farb-Architektur (Light & Dark Mode)

Alle Tokens sind eigenständig für beide Modi kalibriert und erfüllen WCAG AA ($\ge 4{,}5:1$ Kontrast für Text).

### 2.1 Oberflächen, Text & Rahmen (3-Ebenen-Tonal-Layering)

| Rolle | CSS Variable | Light Mode (*Pure White*) | Dark Mode (*Layered Anthracite*) | Einsatz |
| :--- | :--- | :--- | :--- | :--- |
| **Level 0 · Canvas** | `--bg-canvas` | `#F8F9FB` | `#11141B` | App-Hintergrund, Scroll-Fläche hinter Panels |
| **Level 1 · Chrome & Panels** | `--bg-panel` | `#FFFFFF` | `#191E28` | Top-Bar (48px), linke Sidebar, Haupt-Cards, Tabellen-Container |
| **Level 2 · Sub-Cards & Hover** | `--bg-sub` | `#F3F5F9` | `#222936` | KPI-Kacheln (`Net credit`, `Max loss`), Sticky Table Header, Hover-Flächen |
| **Border · Panel** | `--border-panel` | `#DCE2EC` | `#2A3242` | Äußere `1px`-Kante für Top-Bar, Sidebar und Haupt-Panels |
| **Border · Sub / Hairline** | `--border-sub` | `#E4E9F2` | `#2D3647` | Innere Zeilentrenner, KPI-Box-Rahmen, Divider |
| **Top Specular Edge (Dark)** | `--top-edge` | `none` | `inset 0 1px 0 rgba(255,255,255,0.04)` | Subtile `1px`-Lichtkante oben auf Level-1-Panels im Dark Mode |
| **Text · Primary** | `--text-primary` | `#0F172A` | `#F1F5F9` | Überschriften, Ticker, Haupt-KPIs, Preise |
| **Text · Secondary** | `--text-secondary` | `#475569` | `#94A3B8` | Labels, Tab-Texte inaktiv, Beschreibungen |
| **Text · Muted** | `--text-muted` | `#64748B` | `#64748B` | Einheiten (`$`, `%`, `pts`), Zeitstempel, Metadaten |

### 2.2 Interaktion: Solid-Amber CTA & Soft-Orange Selektion (ohne Gelbstich)

> **Wichtige Farbregel:** Für helle Selektionsflächen **niemals** Buttergelb (`#FEF3C7` / `amber-100`) verwenden. Stattdessen leichtes, klares **Soft-Orange (`#FFF4ED`)** nutzen, damit es sich sauber von `#FFFFFF` absetzt, ohne gelbstichig zu wirken.

| Rolle | CSS Variable | Light Mode (*Pure White*) | Dark Mode (*Layered Anthracite*) | Einsatz |
| :--- | :--- | :--- | :--- | :--- |
| **Primary CTA · Background** | `--cta-bg` | `#D97706` *(Solid Amber)* | `#F59E0B` *(Solid Amber)* | Hauptaktionen: `+ Add Ticker`, `+ Stage trade`, `Send to order hub` |
| **Primary CTA · Hover** | `--cta-hover` | `#F59E0B` | `#FBBF24` | Hover-Zustand der Primär-Buttons (heller, damit die dunkle Schrift AA hält) |
| **Primary CTA · Border** | `--cta-border` | `#B45309` | `#D97706` | `1.5px` Kontur der Primär-Buttons |
| **Primary CTA · Text** | `--cta-text` | `#0F172A` | `#11141B` | Dunkle Schrift auf Solid Amber (AA: 5,6:1 Light · 8,6:1 Dark) |
| **Secondary Button · Bg** | `--btn-sec-bg` | `#FFFFFF` | `#222936` | Sekundäre Aktionen (`Edit watchlist`, `+ New watchlist`, inaktive Pills) |
| **Secondary Button · Border** | `--btn-sec-border` | `#C8D1DF` | `#334155` | Deutliche Kontur (nie blass/passiv) |
| **Secondary Button · Text** | `--btn-sec-text` | `#1E293B` | `#E2E8F0` | Klar lesbarer Button-Text |
| **Selection / Active · Bg** | `--sel-bg` | `#FFF4ED` *(Soft-Orange)* | `rgba(245, 158, 11, 0.14)` | Selektierte Tabellenzeilen, aktive Filter-Pills, DTE- & Exit-Rule-Pills |
| **Selection / Active · Border** | `--sel-border` | `#EA580C` / `#D97706` | `#F59E0B` | `1.5px`-Rahmen aktiver Pills, `2px`-Tab-Unterstrich, `2px`-Seitenkante |
| **Selection / Active · Text** | `--sel-text` | `#9A3412` | `#FDE68A` | Text in aktiven Pills und selektierten Sidebar-Einträgen |
| **Accent Hairline / Dot** | `--amber` | `#D97706` | `#F59E0B` | Aktiver Tab-Unterstrich (`2px`), Spot-Punkt in GEX-Range-Bar, Fokus-Punkt |

### 2.3 Marktsignale (Leuchtendes Grün, Stress-Rose & Caution)

| Rolle | CSS Variable | Light Mode (*Pure White*) | Dark Mode (*Layered Anthracite*) | Einsatz |
| :--- | :--- | :--- | :--- | :--- |
| **Positive / Vivid Green · Text** | `--emerald` | `#059669` | `#1CE88C` *(Leuchtend)* | Positives `IV-RV`, `+GEX`, Gewinn, Net Credit, Broker-Online-Dot |
| **Positive / Vivid Green · Chart** | `--emerald-chart` | `#10B981` *(Leuchtend)* | `#1CE88C` *(Leuchtend)* | Bullische Candlesticks, +GEX-Balken, Profit-Histogramm, TP-Bar |
| **Positive · Badge Bg** | `--emerald-bg` | `#D1FAE5` | `rgba(28, 232, 140, 0.16)` | Tinted Badge-Hintergrund für positive Werte |
| **Positive · Badge Border** | `--emerald-border` | `#34D399` | `rgba(28, 232, 140, 0.42)` | Feiner Rand für grüne Signal-Badges |
| **Negative / Stress · Text & Chart** | `--rose` | `#BE123C` | `#FB7185` | Negatives Gamma, Backwardation, Max Loss, Breakeven, Bärische Kerzen |
| **Negative · Badge Bg** | `--rose-bg` | `#FFF1F2` | `rgba(251, 113, 133, 0.14)` | Tinted Badge-Hintergrund für Stress/Verlust |
| **Negative · Badge Border** | `--rose-border` | `#FECDD3` | `rgba(251, 113, 133, 0.32)` | Feiner Rand für rote Signal-Badges |
| **Caution / Warning · Text** | `--caution-text` | `#9A3412` | `#FBBF24` | Warnungen (`⚠ Wide bid/ask`, `⚠ Negative edge`, Earnings < 30d) |
| **Caution · Badge Bg** | `--caution-bg` | `#FFF7ED` | `rgba(245, 158, 11, 0.09)` | Hintergrund für Warn-Badges |
| **Caution · Badge Border** | `--caution-border` | `#D97706` *(dashed)* | `#F59E0B` *(dashed)* | **Immer `1px dashed`** + `⚠`-Icon zur klaren Trennung von UI-Selektion |

---

## 3. Typografie & Zahlen-Präzision

* **UI & Überschriften:** `Inter, system-ui, -apple-system, sans-serif`
* **Finanzdaten, Ticker, Strikes, KPIs, Zeitstempel:** `IBM Plex Mono, ui-monospace, SFMono-Regular, monospace`
* **Zwingend für alle Zahlen:** `font-variant-numeric: tabular-nums;` (Tailwind: `tabular-nums`), damit Kommas, Vorzeichen und Dezimalstellen in Tabellen und KPI-Karten vertikal exakt fluchten.
* **Größen-Hierarchie:**
  * Trade-Titel (`DIA 492 / 491 P`): `18px` (`text-lg`), `font-mono font-bold tracking-tight`
  * Haupt-KPI-Werte (`$0.32`, `74.8%`): `16px–24px`, `font-mono tabular-nums font-bold`
  * Tabellen-Inhalt & Standard-UI: `12px` (`text-xs`)
  * Tabellen-Header, Badges, Chart-Achsen: `10px–11px`, `font-medium` / `font-mono`

---

## 4. Komponenten-Spezifikation (Copy-Paste-Regeln)

### 4.1 Globale Shell (`100vh` Fixed Viewport)
* **Top-Bar:** Höhe `48px` (`h-12`), `background-color: var(--bg-panel)`, `border-bottom: 1px solid var(--border-panel)`. **Kein Blur.**
* **3-Step-Trichter (`1. Scout` · `2. Analyze · [SYM]` · `3. Stage & Send`):**
  * Inaktiv: `--text-secondary`.
  * Aktiv: `--text-primary`, `font-weight: 600` + **`2px` Unterstrich** in `--amber` am unteren Rand der Leiste.
* **Stage-Badge (`1 · $102`):** Kompakte Pill mit `background: var(--sel-bg)`, `border: 1px solid var(--sel-border)`, `color: var(--sel-text)`, `font-mono tabular-nums`.
* **Linke Sidebar:** `background-color: var(--bg-panel)`, `border-right: 1px solid var(--border-panel)`. Breite `220px` in `Scout`, `150px` in `Analyze`, standardmäßig eingeklappt in `Stage & Send`.

### 4.2 Buttons & Interaktive Pills
* **Primärer CTA (`+ Add Ticker`, `+ Stage trade`, `Send to order hub`):**
  * Solid Amber: `background: var(--cta-bg)`, `color: var(--cta-text)`, `border: 1.5px solid var(--cta-border)`, `rounded-md` (`6px`), `font-semibold`.
* **Sekundärer Button (`Edit watchlist`, `+ New watchlist`):**
  * `background: var(--btn-sec-bg)`, `color: var(--btn-sec-text)`, `border: 1px solid var(--btn-sec-border)`, `rounded-md`.
* **Filter-, DTE- & Exit-Rule-Pills:**
  * Inaktiv: Identisch zu Secondary Button (`rounded-full` bei Quick-Filtern & Exit-Rules, `rounded-md` bei DTE).
  * Aktiv: **Soft-Orange Selektion** — `background: var(--sel-bg)`, `color: var(--sel-text)`, `border: 1.5px solid var(--sel-border)`, `font-weight: 600`.

### 4.3 Watchlist-Tabelle & Inline-GEX-Range-Bar
* **Tabellen-Container:** Level-1-Panel (`--bg-panel`, `border: 1px solid var(--border-panel)`, `rounded-lg`).
* **Sticky Header:** `background: var(--bg-sub)`, `border-bottom: 1px solid var(--border-sub)`, `color: var(--text-secondary)`.
* **Tabellenzeilen (Virtualisiert):**
  * Keine vertikalen Zell-Linien; nur `border-bottom: 1px solid var(--border-sub)`.
  * Hover: `background: var(--bg-sub)`.
  * Selektiert: `background: var(--sel-bg)` + `box-shadow: inset 2px 0 0 var(--amber)`.
  * Regime-Dimming: `opacity: 0.7` für riskante Zeilen; springt bei `:hover` sofort auf `opacity: 1`.
* **Inline-GEX-Range-Bar (SVG, `136×16px`):**
  * Links vom Gamma Flip: `--rose-bg` Track mit `--rose-border` Kante (Negativ-Gamma).
  * Rechts vom Gamma Flip: `--emerald-bg` Track mit `--emerald-border` Kante (Positiv-Gamma).
  * Gamma Flip: `1.5px` vertikale Linie in `--text-muted`.
  * Aktueller Spot: `7.6px` Kreis in `--amber` mit `1.6px` Rand in `--bg-panel`.

### 4.4 4-Punkte-Signal-Leiste (`Analyze`)
* 4 gleichmäßige Level-1-Panels (`grid-cols-2 lg:grid-cols-4 gap-2.5`): `GEX Regime`, `Vol Edge`, `Key Level`, `Earnings`.
* **Niemals** vollflächig orange einfärben. Jede Kachel nutzt neutrales `--bg-panel`, kleines `10px` Uppercase-Label (`--text-muted`), einen `6px` Status-Dot rechts oben und den klar gefärbten Signalwert (`--emerald`, `--rose` oder `--text-primary`).

### 4.5 Trennung: UI-Selektion vs. Risiko-Warnung
* **UI-Selektion** (aktive Zeile, aktiver Filter): Durchgezogener `1.5px`-Rahmen (`solid`) in `--sel-border`, Füllung `--sel-bg`.
* **Risiko-Warnung** (`⚠ Wide bid/ask`, `⚠ Negative edge`): **Gestrichelter `1px`-Rahmen (`dashed`)** in `--caution-border`, Füllung `--caution-bg` + zwingendes `⚠`-Symbol.

---

## 5. Datenvisualisierung & Charts

### 5.1 Monte-Carlo-Simulation (`Trades`)
* **Wahrscheinlichkeits-Kegel (1σ / 2σ):** **Strikte Neutralität — kein Braun-Orange!**
  * Light Mode: Outer `rgba(100, 116, 139, 0.11)`, Inner `rgba(100, 116, 139, 0.18)`, Kante `rgba(100, 116, 139, 0.38)`.
  * Dark Mode: Outer `rgba(148, 163, 184, 0.09)`, Inner `rgba(148, 163, 184, 0.16)`, Kante `rgba(148, 163, 184, 0.30)`.
* **Simulierte Pfade:** Gewinn-Pfade über Breakeven in zartem `--path-win`, Verlust-Pfade in neutralem `--path-loss`.
* **Referenzlinien:**
  * Median: `1.8px` solid in `--median-line` (`#0F172A` Light / `#F1F5F9` Dark) mit Spot-Ursprungspunkt in `--amber`.
  * Breakeven: `1.5px` solid in `--rose`.
  * Short Strike: `1px` gestrichelt (`3,3`) in `--text-muted`.
* **Synchronisiertes Verfall-Histogramm darunter:** Balken $\ge$ Breakeven in `--emerald-chart`, Balken $<$ Breakeven in `--rose` (Opacity `0.92`, `rx="2"`).

### 5.2 Synchronisierter Price & GEX Chart (`75% / 25%`)
* Beide Charts sitzen in `--bg-sub`-Containern und teilen sich exakt dieselbe Y-Preisachse.
* **Candlesticks:** Bullische Kerzen in `--emerald-chart` (`#10B981` Light / `#1CE88C` Dark), bärische Kerzen in `--rose`.
* **Expected-Move-Kegel (rechts):** Neutrales Slate (`--cone-outer` + gestrichelte `--cone-stroke`-Linien).
* **GEX-Schlüsselmarken:** `MAX CALL WALL` (`--emerald`, gestrichelt), `MAX PUT WALL` (`--rose`, gestrichelt), `ZERO GAMMA / FLIP` (`--amber`, gepunktet).
* **GEX-Histogramm (rechts 25 %):** Positives Gamma nach rechts in `--emerald-chart`, negatives Gamma nach links in `--rose`.

---

## 6. Produktionsfertige CSS-Custom-Properties

Direkt in `globals.css` übernehmen (`:root` für Light · Pure White, `.dark` für Dark · Layered Anthracite):

```css
:root {
  /* Surfaces (100% Opaque Tonal Layering) */
  --bg-canvas: #F8F9FB;
  --bg-panel: #FFFFFF;
  --bg-sub: #F3F5F9;
  --border-panel: #DCE2EC;
  --border-sub: #E4E9F2;
  --top-edge: none;

  /* Typography */
  --text-primary: #0F172A;
  --text-secondary: #475569;
  --text-muted: #64748B;

  /* Primary CTA (Solid Amber) */
  --cta-bg: #D97706;
  --cta-hover: #F59E0B;
  --cta-border: #B45309;
  --cta-text: #0F172A;

  /* Secondary Controls */
  --btn-sec-bg: #FFFFFF;
  --btn-sec-hover: #F3F5F9;
  --btn-sec-border: #C8D1DF;
  --btn-sec-hover-border: #94A3B8;
  --btn-sec-text: #1E293B;

  /* Selection & Active State (Soft-Orange — NO Butter-Yellow) */
  --sel-bg: #FFF4ED;
  --sel-border: #EA580C;
  --sel-text: #9A3412;
  --amber: #D97706;

  /* Market Signals (Vivid Emerald & Stress Rose) */
  --emerald: #059669;
  --emerald-chart: #10B981;
  --emerald-bg: #D1FAE5;
  --emerald-border: #34D399;

  --rose: #BE123C;
  --rose-bg: #FFF1F2;
  --rose-border: #FECDD3;

  --caution-bg: #FFF7ED;
  --caution-border: #D97706;
  --caution-text: #9A3412;

  /* Charts (Neutral Slate Cones) */
  --chart-grid: #E2E8F0;
  --cone-outer: rgba(100, 116, 139, 0.11);
  --cone-inner: rgba(100, 116, 139, 0.18);
  --cone-stroke: rgba(100, 116, 139, 0.38);
  --path-win: rgba(16, 185, 129, 0.34);
  --path-loss: rgba(100, 116, 139, 0.34);
  --median-line: #0F172A;
}

.dark {
  /* Surfaces (Layered Anthracite — NO Pure Black) */
  --bg-canvas: #11141B;
  --bg-panel: #191E28;
  --bg-sub: #222936;
  --border-panel: #2A3242;
  --border-sub: #2D3647;
  --top-edge: inset 0 1px 0 rgba(255, 255, 255, 0.04);

  /* Typography */
  --text-primary: #F1F5F9;
  --text-secondary: #94A3B8;
  --text-muted: #64748B;

  /* Primary CTA (Solid Amber) */
  --cta-bg: #F59E0B;
  --cta-hover: #FBBF24;
  --cta-border: #D97706;
  --cta-text: #11141B;

  /* Secondary Controls */
  --btn-sec-bg: #222936;
  --btn-sec-hover: #2A3343;
  --btn-sec-border: #334155;
  --btn-sec-hover-border: #475569;
  --btn-sec-text: #E2E8F0;

  /* Selection & Active State */
  --sel-bg: rgba(245, 158, 11, 0.14);
  --sel-border: #F59E0B;
  --sel-text: #FDE68A;
  --amber: #F59E0B;

  /* Market Signals (Vivid Neon-Emerald & Stress Rose) */
  --emerald: #1CE88C;
  --emerald-chart: #1CE88C;
  --emerald-bg: rgba(28, 232, 140, 0.16);
  --emerald-border: rgba(28, 232, 140, 0.42);

  --rose: #FB7185;
  --rose-bg: rgba(251, 113, 133, 0.14);
  --rose-border: rgba(251, 113, 133, 0.32);

  --caution-bg: rgba(245, 158, 11, 0.09);
  --caution-border: #F59E0B;
  --caution-text: #FBBF24;

  /* Charts (Neutral Slate Cones) */
  --chart-grid: #252D3C;
  --cone-outer: rgba(148, 163, 184, 0.09);
  --cone-inner: rgba(148, 163, 184, 0.16);
  --cone-stroke: rgba(148, 163, 184, 0.30);
  --path-win: rgba(28, 232, 140, 0.34);
  --path-loss: rgba(148, 163, 184, 0.28);
  --median-line: #F1F5F9;
}
```

---

## 7. Guardrails für Coding-Agenten (Do's & Don'ts)

### DO
* Alle Farben konsequent über die obigen CSS-Variables referenzieren (keine hartcodierten `bg-blue-*`, `bg-gray-*` oder `bg-amber-100`-Klassen).
* Auf jedem numerischen Finanzwert `font-mono tabular-nums` setzen.
* Primäre Aktionen (`+ Add Ticker`, `+ Stage trade`, `Send to order hub`) mit Solid Amber (`--cta-bg`) auszeichnen.
* Übergänge kurz und GPU-freundlich halten (`70ms–120ms ease` nur auf `background-color`, `border-color`, `color`, `opacity`).

### DON'T
* **NIEMALS** `backdrop-filter`, `backdrop-blur-*` oder `backdrop-saturate-*` einsetzen.
* **NIEMALS** radiale Hintergrund-Orbs oder großflächige Farbverläufe hinter Panels legen.
* **NIEMALS** Buttergelb (`#FEF3C7` / `amber-100`) als Selektions- oder Pill-Hintergrund im Light Mode verwenden — immer `#FFF4ED` (`--sel-bg`).
* **NIEMALS** den Monte-Carlo-Wahrscheinlichkeitskegel orange/braun einfärben — immer neutrales Slate (`--cone-outer` / `--cone-inner`).
* **NIEMALS** reines `#000000` als Dark-Mode-Hintergrund verwenden — immer gestuftes Anthrazit (`#11141B` → `#191E28` → `#222936`).