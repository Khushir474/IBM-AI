# E-commerce Intelligence Platform — Requirements

> Unified ML platform combining **churn prediction**, **dynamic pricing**, and **customer LTV prediction** to drive retention and revenue optimization.

## Personas

### Persona 1: Marketing Manager
- **Name:** Alex
- **Goal:** Identify at-risk customers and run targeted retention campaigns
- **Pain Point:** Currently reacting to churn after it happens; wants to act before customers leave
- **Frequency:** Checks platform daily, exports lists of at-risk customers weekly

### Persona 2: Pricing / Revenue Manager
- **Name:** Jordan
- **Goal:** Optimize product prices to maximize revenue without leaving money on the table or pricing customers out
- **Pain Point:** Prices are static; missing opportunities when demand spikes or inventory is low
- **Frequency:** Reviews price recommendations weekly, adjusts high-impact products daily

### Persona 3: Data Analyst
- **Name:** Sam
- **Goal:** Explore customer segments, validate model predictions, understand drivers of churn/LTV
- **Pain Point:** Models are black boxes; needs visibility into what features matter and why predictions differ
- **Frequency:** Deep-dive analysis ad-hoc (2–3 times per week)

### Persona 4: Finance / CFO
- **Name:** Pat
- **Goal:** Measure business impact: revenue lift, churn reduction, LTV growth from interventions
- **Pain Point:** Wants proof that ML efforts actually move the needle; needs ROI calculations
- **Frequency:** Monthly/quarterly reviews of dashboard KPIs

---

## User Flows

### Flow 1: Marketing Manager Identifies At-Risk Customers
1. Manager logs in and goes to **Churn Risk Dashboard**
2. Manager sees a list of customers, ranked by churn risk (high → low)
3. Each customer shows:
   - Customer ID, name, LTV
   - Churn risk score (0–100, color-coded: green/yellow/red)
   - Reason for high risk (e.g., "No purchase in 45 days", "Last 3 orders returned")
   - Recommended intervention (e.g., "Send discount email", "VIP reactivation call")
4. Manager filters by risk level: show top 500 high-risk customers
5. Manager exports the list (CSV) with customer IDs, contact info, churn scores, recommended actions
6. (Offline: marketing team runs email campaign, tracks conversions)
7. Manager returns a week later to see: "Of 500 at-risk customers, 150 made a purchase within 7 days" → lift is measured

### Flow 2: Revenue Manager Reviews Price Recommendations
1. Manager logs in and goes to **Dynamic Pricing Dashboard**
2. Manager sees a table of products with:
   - Current price
   - Recommended price
   - Expected revenue impact (e.g., "+$5,000/day" or "-2% margin")
   - Reason (e.g., "Low inventory, high demand", "Competitor price dropped 10%", "Seasonality spike")
3. Manager reviews top 20 products by revenue impact
4. Manager can:
   - Accept a recommendation (system applies new price)
   - Reject a recommendation (system learns; won't suggest again soon)
   - Set a price cap (e.g., "never go below $X or above $Y")
5. Manager sees a chart: "Price change → demand response over time" to validate the elasticity model
6. Weekly recap: "Recommended prices generated +$250K revenue this week vs. static baseline"

### Flow 3: Data Analyst Explores Churn Drivers
1. Analyst logs in and goes to **Model Insights / Explainability**
2. Analyst can drill into a specific customer's churn prediction:
   - Churn score: 78/100
   - Top 5 factors driving this score:
     - "No purchase in 50 days" (contribution: +25 points)
     - "Last order returned" (contribution: +18 points)
     - "Below-average customer in cohort" (contribution: +15 points)
     - "High price sensitivity (low basket value)" (contribution: +12 points)
     - "Competitor has lower prices" (contribution: +8 points)
3. Analyst can see cohort-level trends:
   - "Customers acquired in Q3 2024 have 15% higher churn" (find why?)
   - "Product category A has 2x churn vs. category B" (investigate supply/quality issues?)
4. Analyst can compare: "Churn prediction accuracy on recent data" (check for model drift)
5. Analyst exports a report: feature importance, cohort comparisons, model performance metrics

### Flow 4: CFO Reviews Monthly Impact Dashboard
1. CFO logs in and sees a **Business Impact Dashboard** with KPIs:
   - **Retention:** "Churn rate: 8.2% this month (was 9.1% last month, -0.9 pp)" 
   - **Revenue:** "Dynamic pricing contributed +$1.2M incremental revenue YTD"
   - **Customer Value:** "Average new customer LTV: $450 (up 5% YoY)"
   - **ROI:** "Retention campaigns cost $50K, saved $400K in LTV" (8x ROI)
2. CFO sees trend charts: how these metrics have changed over 12 months
3. CFO can drill into: "Which interventions worked best?" (email vs. discount vs. call)
4. CFO exports quarterly report with findings and recommendations

---

## Requirements

### **CHURN PREDICTION MODULE**

### REQ-001: Score Customers by Churn Risk
**Description:** System predicts which customers are likely to churn in the next 30 days and assigns a risk score (0–100).

**Acceptance Criteria:**
- Every customer in the system receives a churn risk score
- Score ranges from 0 (very low risk) to 100 (very high risk)
- Scores are updated daily with fresh data
- Score reflects customer's likelihood of NOT making a purchase in the next 30 days
- Prediction is based on customer's historical behavior (purchase history, recency, frequency, product affinity, cohort patterns)
- Model performance is measurable: precision, recall, AUC reported on holdout test set

---

### REQ-002: Explain Churn Risk with Interpretable Factors
**Description:** For each customer, system shows top factors driving their churn risk so analysts/marketers understand "why" the model flagged them.

**Acceptance Criteria:**
- Each high-risk customer shows 3–5 key factors explaining their score
- Factors are human-readable (e.g., "No purchase in 60 days", "Last order returned", "Low lifetime value for cohort")
- Factors include a contribution score showing impact on overall churn prediction
- Analyst can drill into a factor to see supporting data (e.g., last purchase date, return rate, cohort average)
- Factor importance aligns with model internals (not a guess post-hoc explanation)

---

### REQ-003: Segment Customers by Churn Risk Tier
**Description:** Customers are grouped into actionable tiers (Low / Medium / High) so marketing can target interventions efficiently.

**Acceptance Criteria:**
- System defines three tiers: Low (0–33), Medium (34–66), High (67–100)
- Each tier has a target intervention:
  - Low: no action needed
  - Medium: nurture campaigns (email, exclusive offers)
  - High: high-touch intervention (phone call, VIP reactivation offer)
- Tier definitions can be adjusted (e.g., change threshold from 67 to 75)
- Count of customers in each tier is visible and updated daily

---

### REQ-004: Recommend Interventions per Customer
**Description:** For at-risk customers, system recommends which retention action is most likely to work.

**Acceptance Criteria:**
- Each high/medium-risk customer shows a recommended intervention:
  - Email offer (specific discount %, product category, or free shipping)
  - Phone reactivation call
  - VIP/loyalty tier upgrade
  - Product recommendation (cross-sell based on historical interests)
- Recommendation is personalized (e.g., "Send 20% off discount on shoes" if customer has shoe purchase history)
- Recommendation is based on what worked for similar customers (cohort analysis)
- Analyst can override recommendation if they know better

---

### REQ-005: Measure Churn Intervention Effectiveness
**Description:** System tracks whether at-risk customers who received interventions actually stay or leave, measuring campaign lift.

**Acceptance Criteria:**
- System can link a customer's intervention (e.g., email sent on 2024-01-15) to outcome (purchase within 7/14/30 days: yes/no)
- Dashboard shows:
  - % of at-risk customers who made a purchase after intervention
  - % without intervention (control baseline, if available)
  - Lift = (intervention rate - control rate) / control rate
- Report is available by intervention type (email vs. phone vs. offer type)
- Data supports A/B testing: "Customers sent email offer converted at 18%, phone call at 25%" → phone is more effective

---

### **CUSTOMER LTV PREDICTION MODULE**

### REQ-006: Predict Customer Lifetime Value at Multiple Time Horizons
**Description:** For each customer, system predicts their total lifetime spending at 7-day, 30-day, 90-day, and 1-year horizons.

**Acceptance Criteria:**
- Every customer has four LTV predictions: 7-day, 30-day, 90-day, 1-year
- Prediction is the expected total spend (in USD) over that time window
- Prediction is based on customer's purchase history, product affinity, cohort patterns, seasonality
- New customers (no history) receive a cohort-average prediction
- Prediction updates daily as new purchase data arrives

---

### REQ-007: Identify High-Value Customer Cohorts
**Description:** System segments customers by their predicted LTV and highlights cohorts with different value profiles.

**Acceptance Criteria:**
- System shows customer segments ranked by predicted LTV (high → low)
- Each segment includes:
  - Segment name (e.g., "Luxury buyers", "Budget bargain hunters", "Seasonal spenders")
  - Size (count of customers)
  - Average predicted LTV
  - Key characteristics (e.g., average order value, category preferences, purchase frequency)
- Analyst can drill into a segment to see the cohort of customers
- Segments refresh daily

---

### REQ-008: Flag Early Indicators of High-Value Customers
**Description:** System identifies newly acquired customers who show signals of becoming high-LTV customers within the first 7–30 days.

**Acceptance Criteria:**
- For new customers (first purchase within last 7 days), system flags high-potential prospects
- Signals include:
  - High first-purchase value (e.g., >$200)
  - Repeat purchase within 3 days
  - High customer in cohort (e.g., top 20% by spend for their acquisition source)
  - Strong product affinity (bought from category with high repeat rate)
- Flagged customers can be prioritized for email nurture, loyalty programs, VIP onboarding
- Prediction accuracy is tracked: % of flagged customers who actually become high-LTV within 90 days

---

### REQ-009: Compare Predicted vs. Actual LTV
**Description:** For historical customers, system shows how well LTV predictions matched reality, tracking model accuracy over time.

**Acceptance Criteria:**
- For customers with complete 90-day/1-year windows in the past, show:
  - Predicted LTV (made at day 0)
  - Actual LTV (measured at day 90 / day 365)
  - Accuracy metrics: MAE (mean absolute error), RMSE (root mean squared error)
  - Calibration: are predictions on average too high or too low?
- Accuracy is tracked over time to detect model drift
- Analyst can export a report: "Model accuracy by cohort" (was prediction better for some groups?)

---

### **DYNAMIC PRICING MODULE**

### REQ-010: Recommend Optimal Prices by Product
**Description:** System analyzes demand, inventory, competition, and seasonality to recommend prices that maximize revenue.

**Acceptance Criteria:**
- Every product receives a price recommendation
- Recommendation accounts for:
  - Current demand (historical daily sales, seasonality, trends)
  - Inventory level (low stock → higher price to reduce demand; overstock → lower to clear)
  - Competitor prices (match/beat/premium strategy based on product positioning)
  - Price elasticity (how sensitive this product's demand is to price changes)
  - Margin targets (never go below cost + minimum margin %)
- Recommendation includes a confidence level (high/medium/low) based on data quality and model uncertainty
- Recommendation is updated daily

---

### REQ-011: Quantify Revenue Impact of Price Changes
**Description:** For each price recommendation, system estimates the expected change in revenue (positive or negative) if the price is adopted.

**Acceptance Criteria:**
- Each recommendation shows:
  - Current price
  - Recommended price
  - Expected revenue change: "$X more per day" or "−$X less per day"
  - Reason: e.g., "Low inventory (hold price)", "High demand (increase)", "Competitor undercut (decrease)"
  - Assumptions: expected demand, elasticity, time horizon
- Marketing manager can see top 20 products by revenue impact (easiest wins)
- Revenue impact is measured ex-post (actual vs. baseline) to validate model

---

### REQ-012: Track Price Changes and Demand Response
**Description:** System monitors what happens when prices are changed, measuring actual demand response and building a feedback loop for the model.

**Acceptance Criteria:**
- When a price is changed (recommended or manual), system logs:
  - Product, old price, new price, date changed
  - Sales volume before change (baseline, last 7 days)
  - Sales volume after change (measured over next 7/14 days)
  - Calculated elasticity: % change in sales / % change in price
- Analyst can visualize: "Price history + sales volume over time" to see the correlation
- Model learns from actual elasticity observed, improving future recommendations
- Report available: "Price changes this month, elasticity observed, revenue impact"

---

### REQ-013: Set Price Boundaries and Policy Constraints
**Description:** Manager can define guardrails (min/max prices, margin floors) so pricing stays compliant and sensible.

**Acceptance Criteria:**
- Manager can set per-product constraints:
  - Min price: never go below $X (cost floor, competitive constraint)
  - Max price: never go above $Y (customer perception, psychological pricing)
  - Margin floor: never let margin drop below Z%
- Recommendations always respect these constraints
- Constraints can be updated in bulk (e.g., "all shoes must have >30% margin")
- Constraint violations are logged for audit

---

### REQ-014: Handle Inventory-Driven Pricing
**Description:** System adjusts prices dynamically based on inventory levels, with high inventory prompting discounts and low inventory allowing price increases.

**Acceptance Criteria:**
- Current inventory is factored into price recommendations
- High inventory (>60 days supply):
  - Recommendation skews toward lower prices to accelerate sales
  - Discount suggestions show inventory level as justification
- Low inventory (<14 days supply):
  - Recommendation can go higher (capture margin before stockout)
  - Warning: "Limited stock, consider price increase"
- Out of stock:
  - Price is muted (can't sell anyway)
  - Analyst sees "Restock needed" alert

---

### **UNIFIED PLATFORM FEATURES**

### REQ-015: Unified Dashboard with Cross-Module Insights
**Description:** A single dashboard shows churn, LTV, and pricing insights together, with connections between them.

**Acceptance Criteria:**
- Dashboard shows three panels side-by-side:
  - Left: Churn risk summary (count by tier, top 10 at-risk customers)
  - Center: LTV summary (average LTV, high-value cohort size, new high-potential customers)
  - Right: Pricing summary (price recommendations pending, revenue impact this week)
- Cross-module insight example: "High-churn customers typically have low LTV; recommend VIP nurture program"
- Manager can navigate to detailed view for any panel

---

### REQ-016: A/B Testing Support
**Description:** System enables controlled experiments to measure which interventions (pricing, retention) actually drive results.

**Acceptance Criteria:**
- Manager can define an experiment:
  - Treatment: e.g., "send 20% discount email to at-risk customers"
  - Control: e.g., no email
  - Metric: purchase within 7 days
  - Duration: 2 weeks
- System randomly assigns customers to treatment/control
- After experiment, system reports:
  - Treatment conversion rate
  - Control conversion rate
  - Lift and statistical significance (p-value)
  - Confidence interval on the lift
- Experiment results inform recommendations: "This discount works; increase offer to 25%"

---

### REQ-017: Model Performance Monitoring
**Description:** Analyst can track whether models are accurate and alert if performance degrades (drift detection).

**Acceptance Criteria:**
- Dashboard shows model accuracy metrics (AUC, precision, recall, RMSE) updated weekly
- Accuracy is broken down by cohort (new customers, high-value, etc.) to spot segment-specific drift
- Alert triggers if accuracy drops below threshold (e.g., AUC < 0.75)
- Analyst can see: "Model was trained on data from 2024-01-01 to 2024-03-31. Accuracy on recent week: 0.82 (good)"
- Root cause analysis hints: "Accuracy down in new-customer segment; may need retraining on recent data"

---

### REQ-018: Data Freshness and Latency Transparency
**Description:** Users understand how recent the data is and when each prediction was last updated.

**Acceptance Criteria:**
- Dashboard shows timestamps for:
  - Last data refresh from Cassandra (operational data): e.g., "2 minutes ago"
  - Last data refresh from Iceberg (historical analytics): e.g., "updated daily at 2 AM UTC"
  - Last model update (churn/LTV/pricing): e.g., "trained yesterday, scoring runs daily at 3 AM"
- Latency is acceptable for each use case:
  - Churn scores: updated daily (manager can accept yesterday's scores)
  - Price recommendations: updated daily (manager doesn't need real-time)
  - LTV: updated daily (acceptable lag)
- Alert if latency exceeds SLA (e.g., "Price recommendations stale for >24 hours")

---

### REQ-019: Export and Integration
**Description:** Users can export insights and integrate with downstream systems (CRM, email platform, pricing engine).

**Acceptance Criteria:**
- Manager can export from any dashboard:
  - CSV: at-risk customers + churn scores + recommended interventions
  - CSV: price recommendations + inventory levels + revenue impact
  - CSV: high-value customer cohorts + LTV predictions + characteristics
- Exports are timestamped and include data freshness metadata
- Exports can be scheduled (e.g., "email me the churn list every Monday morning")
- API endpoints exist for programmatic access (third-party systems can pull data)

---

### REQ-020: Authentication and Multi-Tenancy
**Description:** Each company/account sees only its own data; no cross-contamination.

**Acceptance Criteria:**
- Users log in with credentials tied to their company
- Dashboards show only that company's customers, products, transactions
- Data is isolated at the database level (not just UI filtering)
- Audit log tracks who accessed what and when

---

## Out of Scope

The following are explicitly **NOT** part of this platform:

- **Trade execution:** System does not execute price changes or send emails; recommendations only. Humans decide and implement.
- **Inventory management:** No stock replenishment, purchase orders, or supply chain tools.
- **Customer service / support tickets:** No ticketing system or customer support workflow.
- **Product categorization:** Assumes product catalog is pre-loaded and categorized; no product taxonomy management.
- **Fraud detection:** Does not flag fraudulent transactions or customers.
- **International / multi-currency:** All pricing and LTV in USD; no forex or regional pricing strategies.
- **Subscription / recurring revenue:** Focused on transaction-based e-commerce; not subscriptions or SaaS billing.
- **Personalized recommendations:** No product recommendation engine (out of scope for this phase; REQ-004 mentions cross-sell but doesn't build a full recommender).
- **Email/SMS sending:** No email/SMS platform integration; exports lists that marketers send via their own email tool.
- **Custom ML models:** Uses pre-trained, standard models; no model training/tuning by end users.
- **Real-time bidding / dynamic ad pricing:** Focused on owned-channel pricing; not ad spend optimization.
- **Returns / refunds:** Does not model return likelihood or refund dynamics (assumes return data exists, uses as churn signal).

---

## Success Criteria (End-to-End)

The platform is successful when:

1. **Churn:** Marketing can identify top 1,000 at-risk customers in <2 minutes; intervention lift is ≥5% (control baseline)
2. **LTV:** New customers are segmented by predicted value; high-potential customers identified in first 7 days with >70% accuracy
3. **Pricing:** Revenue manager sees price recommendations within 1 minute; implementing recommendations yields ≥2% revenue lift vs. static pricing
4. **Data freshness:** All dashboards are updated within 24 hours of data arrival; no stale predictions
5. **Explainability:** Analyst can drill into any prediction and understand top factors in <30 seconds
6. **ROI measurable:** CFO can report: churn interventions saved $X in LTV; pricing changes added $Y revenue; new-customer LTV up Z%
7. **Model accuracy:** Churn AUC >0.80, LTV MAE <10% of average, price elasticity captures real demand response
8. **Integration:** Exports work without friction; data flows into CRM and email tools seamlessly
