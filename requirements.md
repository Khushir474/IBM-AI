# Portfolio Health Dashboard — Requirements

## Personas

### Persona 1: Retail Investor
- **Name:** Alex
- **Goal:** Monitor investment portfolio performance and understand if current holdings match their intended allocation
- **Pain Point:** Doesn't have time to manually check all accounts and compare against targets; wants a quick snapshot
- **Frequency:** Checks dashboard 1–2 times per week

### Persona 2: Financial Advisor
- **Name:** Jordan
- **Goal:** Monitor client portfolios for drift and proactively flag when rebalancing might be needed
- **Pain Point:** Managing many clients; needs efficient way to spot anomalies across portfolios
- **Frequency:** Checks dashboard daily, especially after market close

### Persona 3: Risk Analyst
- **Name:** Sam
- **Goal:** Understand portfolio-level risk exposure and identify concentrations or imbalances
- **Pain Point:** Needs historical context (how did this portfolio perform over time?) to assess risk
- **Frequency:** Checks dashboard weekly or when investigating risk events

---

## User Flows

### Flow 1: Retail Investor Reviews Portfolio
1. User logs in with their account credentials
2. User lands on a dashboard showing their portfolio at a glance
3. User sees:
   - Current account balances (across all accounts they own)
   - Current asset allocation (e.g., 60% stocks, 30% bonds, 10% cash)
   - Target allocation (what they said it should be)
   - Allocation drift (how far they are from target, in % terms)
4. User can click on an asset class to see more detail (which holdings, performance)
5. User sees a recommendation: "Consider rebalancing if drift > 5%" (or similar)

### Flow 2: Financial Advisor Monitors Multiple Clients
1. Advisor logs in
2. Advisor sees a list of their client portfolios
3. For each client, advisor sees a summary card:
   - Client name
   - Total portfolio value
   - % drift from target allocation
   - Risk tier (Low / Medium / High)
4. Advisor can click on a client to drill into that client's detailed portfolio view
5. Advisor sees alerts: "Portfolio XX has drifted >10% from target" or "Market events affect portfolio YY"

### Flow 3: Risk Analyst Investigates Historical Performance
1. Analyst logs in
2. Analyst searches for a specific portfolio or customer
3. Analyst sees:
   - Current holdings and balances
   - Portfolio metrics over the last 90 days (return, volatility, Sharpe ratio, etc.)
   - Market data over the same period (S&P 500, bond indices, etc.)
   - A chart comparing portfolio performance to benchmark
4. Analyst can export a summary for reporting or further analysis

---

## Requirements

### REQ-001: Display Current Portfolio Holdings
**Description:** User can see all accounts they own and the current balance in each account.

**Acceptance Criteria:**
- Dashboard displays a list of all customer accounts (from Cassandra `accounts` table)
- Each account shows: account ID, account type (checking, savings, investment, etc.), current balance
- Balances are sorted by account type or value (user preference)
- Balances update when user refreshes the page

---

### REQ-002: Calculate and Display Asset Allocation
**Description:** User can see what percentage of their portfolio is in each asset class (stocks, bonds, cash, etc.).

**Acceptance Criteria:**
- Dashboard calculates allocation across all accounts based on current holdings
- Allocation is displayed as:
  - A pie chart or similar visualization showing % in each asset class
  - A table with asset class name, dollar amount, and % of total
- Allocation totals 100%
- Calculation is based on real data (not mock data)

---

### REQ-003: Display Target Allocation
**Description:** User has set a target allocation (e.g., "I want 60% stocks, 30% bonds, 10% cash") and the dashboard shows it.

**Acceptance Criteria:**
- Dashboard shows the user's target allocation alongside actual allocation
- Target allocation is presented in the same format as actual allocation (% and dollars)
- User can see both side-by-side for easy comparison
- If no target is set, a sensible default is shown (e.g., standard age-based allocation)

---

### REQ-004: Calculate and Highlight Allocation Drift
**Description:** User can see how far their current allocation has drifted from their target.

**Acceptance Criteria:**
- Dashboard calculates the difference between actual and target allocation for each asset class
- Drift is shown as:
  - Absolute difference (e.g., "Stocks: target 60%, actual 65%, drift +5%")
  - A visual indicator (color, icon) to highlight concerning drift
- Drift > 5% is flagged as minor (yellow/warning)
- Drift > 10% is flagged as major (red/critical)
- An overall portfolio drift score is shown (e.g., "Portfolio is 8% out of balance")

---

### REQ-005: Display Historical Portfolio Metrics
**Description:** User can see how their portfolio has performed over time (last 30/90/365 days).

**Acceptance Criteria:**
- Dashboard shows a time-series chart of:
  - Portfolio total value over time
  - Portfolio return (%) over the period
  - Volatility (standard deviation of daily returns)
- User can select the time period (30 days, 90 days, 1 year)
- Chart is interactive (hover for details, zoom if needed)
- Metrics are calculated from real historical data (Iceberg `portfolio_metrics_daily` table)

---

### REQ-006: Display Market Data and Benchmarks
**Description:** User can see how market indices (S&P 500, bond indices) performed over the same period as their portfolio.

**Acceptance Criteria:**
- Dashboard displays benchmark indices (S&P 500, aggregate bond index, etc.) on the same chart as portfolio performance
- User can toggle benchmark lines on/off to reduce clutter
- Benchmarks are labeled clearly
- Market data is current (as of the most recent market close)

---

### REQ-007: Highlight Risk Tier and Risk Alerts
**Description:** User sees their risk tier and any active risk events or alerts.

**Acceptance Criteria:**
- Dashboard displays customer's current risk tier (Low / Medium / High) prominently
- If there are open fraud alerts or risk escalations, they are shown
- Each alert includes: alert type, date triggered, brief description
- Alerts link to more detail (if user wants to investigate)

---

### REQ-008: Rebalancing Recommendation
**Description:** System suggests when the user should rebalance their portfolio.

**Acceptance Criteria:**
- Dashboard shows a recommendation when drift exceeds a threshold (e.g., >5%)
- Recommendation explains why rebalancing is suggested (e.g., "Stocks have grown to 70% of your portfolio; consider moving 10% to bonds to match your 60% target")
- Recommendation is non-prescriptive and educational (not a directive to buy/sell)

---

### REQ-009: Authentication and Authorization
**Description:** User can only see their own portfolio; they cannot see other customers' portfolios.

**Acceptance Criteria:**
- User logs in with username and password
- Dashboard only displays data for the logged-in user
- If user tries to access another customer's data via URL or API, they get an access-denied error
- Session expires after inactivity (user must log in again)

---

### REQ-010: Responsive and Accessible UI
**Description:** Dashboard is usable on desktop, tablet, and mobile devices.

**Acceptance Criteria:**
- Dashboard layouts adapt to screen size (responsive design)
- Text is readable at default zoom level (no need to pinch-zoom on mobile)
- Colors are distinguishable for colorblind users (not relying solely on red/green)
- Navigation is clear and intuitive on all devices

---

### REQ-011: Data Freshness
**Description:** User understands how recent the data is and when it was last updated.

**Acceptance Criteria:**
- Dashboard shows a timestamp of when data was last refreshed
- Cassandra balances are "live" (as of the last refresh)
- Iceberg portfolio metrics are "daily" (updated once per day, timestamp shown)
- Market data is "end-of-day" (updated after market close, timestamp shown)

---

## Out of Scope

The following are explicitly **NOT** part of this dashboard:

- **Trade execution:** User cannot buy/sell securities from this dashboard. This is view-only.
- **Advisor tools:** Advisors cannot edit client allocations or set targets on behalf of clients (that requires a separate admin interface).
- **Tax reporting:** No tax-loss harvesting analysis, capital gains tracking, or tax forms.
- **Bill pay or transfers:** No money movement functionality.
- **Margin or leverage:** Dashboard assumes cash accounts; does not display margin debt or leveraged positions.
- **Options or derivatives:** Only equity and fixed-income positions (stocks, bonds, cash).
- **Real-time quotes:** Market data is end-of-day only; not intraday ticks or live bid-ask spreads.
- **Alerts/notifications:** No email or SMS alerts (view-only for now).
- **Multi-user portfolios:** Assumes single owner per account; no joint accounts or delegation.
- **Custom benchmarks:** Only standard indices (S&P 500, bond indices, etc.); no user-defined custom benchmarks.
- **International markets:** Portfolio assumed to be USD-denominated; no forex or non-US holdings.
- **Cryptocurrency:** No digital assets.

---

## Success Criteria (End-to-End)

The dashboard is successful when:

1. A user can log in and see their current portfolio balance within 2 seconds
2. A user can identify if their portfolio is drift > 5% from target in under 10 seconds
3. A user can see a 90-day performance chart with benchmark overlay in under 5 seconds
4. An advisor can spot a client portfolio with >10% drift from a list of 10 clients in under 30 seconds
5. A risk analyst can export portfolio metrics and historical performance for further analysis
