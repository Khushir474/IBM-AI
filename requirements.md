# E-commerce Intelligence Platform — Requirements

> Unified ML platform combining **churn prediction**, **customer LTV prediction**, **cart abandonment recovery**, and **dynamic pricing** to drive retention, lifetime value growth, and revenue optimization.

## Personas

### Persona 1: Marketing Manager
- **Name:** Alex
- **Goal:** Identify at-risk customers, recover abandoned carts, and nurture high-value customer segments
- **Pain Point:** Doesn't know which customers are leaving, which will be valuable, or how to win back those with abandoned carts
- **Frequency:** Checks platform daily, exports campaign lists 2–3 times per week

### Persona 2: Pricing / Revenue Manager
- **Name:** Jordan
- **Goal:** Optimize prices and targeted discounts to maximize revenue without eroding margins
- **Pain Point:** Prices are static; missing opportunities when demand spikes, inventory changes, or customers abandon carts
- **Frequency:** Reviews recommendations daily, tests strategies weekly

### Persona 3: Data Analyst
- **Name:** Sam
- **Goal:** Explore customer segments, validate model predictions, understand drivers of churn/LTV/abandonment
- **Pain Point:** Models are black boxes; needs visibility into what factors matter and why predictions differ across cohorts
- **Frequency:** Deep-dive analysis ad-hoc (2–3 times per week)

### Persona 4: Finance / CFO
- **Name:** Pat
- **Goal:** Measure business impact: revenue lift, churn reduction, LTV growth, and ROI on interventions
- **Pain Point:** Wants proof that ML efforts move the needle; needs consolidated ROI calculations
- **Frequency:** Monthly/quarterly reviews of KPI dashboard

---

## User Flows

### Flow 1: Marketing Manager Identifies At-Risk Customers & Designs Retention
1. Manager logs in and goes to **Churn Risk Dashboard**
2. Sees list of customers ranked by churn risk (0–100 score)
3. Each customer shows:
   - Customer ID, name, LTV (predicted 90-day value)
   - Churn risk score (color-coded: green/yellow/red)
   - Top 3 risk factors (e.g., "No purchase in 50 days", "Last order returned", "Below-cohort value")
   - Recommended intervention (email offer, VIP reactivation, product recommendation)
4. Manager filters by tier: show top 500 high-risk customers
5. Manager exports list with customer IDs, contact info, churn scores, LTV, recommended actions
6. (Offline: marketing sends personalized retention campaign)
7. One week later, manager checks: "Of 500 at-risk, 120 made purchase (24% recovery)" → measures lift

### Flow 2: Manager Reviews Cart Abandonment & Recovery Opportunities
1. Manager goes to **Cart Abandonment Dashboard**
2. Sees abandoned carts ranked by recovery likelihood
3. For each cart shows:
   - Customer profile (repeat buyer? high-value?)
   - Cart contents and value
   - Reason for abandonment (price sensitive? shipping shock? stock issue?)
   - Recommended recovery offer (discount %, free shipping, product swap)
   - Conversion probability with offer
4. Manager exports top 300 carts and sends recovery emails with offer codes
5. Returns 48 hours later: "Of 300 sent, 60 converted (20% recovery rate), $8K incremental revenue"

### Flow 3: Pricing Manager Optimizes Prices & Discount Strategy
1. Manager goes to **Dynamic Pricing & Discount Dashboard**
2. Sees products ranked by recovery opportunity
3. For each product:
   - Abandonment rate (% of carts with this product that abandon)
   - Current price, recommended price
   - Expected revenue impact (e.g., "−$2/unit, +40 units sold, +$80/day")
   - Recovery offer recommendation (discount level that maximizes ROI)
4. Reviews discount strategy table: by discount level (5%, 10%, 15%, 20%), what's the recovery rate?
5. Sets constraints: max discount, min margin, inventory-driven pricing
6. Implements strategy
7. One week later: "Strategy generated +$50K incremental revenue, net of discount cost"

### Flow 4: Data Analyst Investigates Customer Segments & Model Drivers
1. Analyst goes to **Customer Intelligence / Explainability**
2. Drills into a high-churn, high-LTV customer:
   - Churn risk: 72/100 (high)
   - Predicted 90-day LTV: $280 (high-value)
   - Churn drivers: "No purchase in 60 days", "Price-sensitive (low avg order value)"
   - LTV drivers: "Previously purchased 8 times", "High-margin categories", "Strong in Q4"
   - Cart abandonment history: 2 abandoned carts in last month
3. Analyst sees cohort trends:
   - "Q3 acquisition cohort has 18% churn vs. 12% overall" (investigate supply/quality?)
   - "Customers in shoes category have 40% higher LTV than fashion" (inventory strategy?)
   - "Mobile checkout has 3x cart abandonment vs. desktop" (UX issue?)
4. Analyst compares: model accuracy on recent data, checks for drift by segment
5. Exports report: cohort analysis, feature importance, model diagnostics

### Flow 5: CFO Reviews Unified Impact Dashboard
1. CFO logs in and sees **Revenue & Retention Impact Dashboard** with KPIs:
   - **Churn:** "Customer retention: 91.8% (was 90.9% last month, +0.9 pp gain)"
   - **LTV:** "Average customer LTV: $520 (up 3% YoY)"
   - **Cart Recovery:** "Recovery campaigns: $250K incremental revenue, 18% conversion rate"
   - **Pricing Optimization:** "Dynamic pricing added $120K revenue this month"
   - **ROI:** "Total interventions cost $80K (discounts + email), generated $370K incremental, 4.6x ROI"
2. Sees 12-month trend charts: retention, LTV, recovery rate, pricing lift
3. Drills into: "Which churn interventions worked best?" (by segment, offer type)
4. Exports quarterly report with findings and recommendations

---

## Requirements

### **CHURN PREDICTION MODULE**

### REQ-001: Score Customers by Churn Risk
**Description:** System predicts which customers are likely to churn in the next 30 days and assigns a risk score (0–100).

**Acceptance Criteria:**
- Every customer receives a churn risk score
- Score ranges 0 (very low risk) to 100 (very high risk)
- Reflects likelihood of NOT making a purchase in next 30 days
- Based on customer's purchase history, recency, frequency, product affinity, cohort patterns
- Updated daily with fresh data
- Model performance measurable: AUC, precision, recall on holdout test set

---

### REQ-002: Explain Churn Risk with Interpretable Factors
**Description:** For each customer, system shows top factors driving churn risk.

**Acceptance Criteria:**
- High-risk customers show 3–5 key factors (e.g., "No purchase in 60 days", "Last order returned", "Low LTV for cohort")
- Factors are human-readable with contribution scores
- Analyst can drill into factors to see supporting data
- Factor importance aligns with model internals

---

### REQ-003: Segment Customers by Churn Risk Tier
**Description:** Customers grouped into actionable tiers (Low / Medium / High) for efficient targeting.

**Acceptance Criteria:**
- Three tiers: Low (0–33), Medium (34–66), High (67–100)
- Each tier has target intervention strategy
  - Low: no action
  - Medium: nurture campaigns (email, offers)
  - High: high-touch intervention (phone, VIP reactivation)
- Tier counts visible and updated daily
- Thresholds adjustable by manager

---

### REQ-004: Recommend Churn Interventions per Customer
**Description:** For at-risk customers, system recommends personalized retention actions.

**Acceptance Criteria:**
- Each at-risk customer shows recommended intervention:
  - Email offer (specific discount %, product category)
  - Phone reactivation call
  - VIP/loyalty tier upgrade
  - Product recommendation (based on purchase history)
- Recommendations personalized by cohort and behavior
- Based on what worked for similar customers
- Manager can override if preferred

---

### REQ-005: Measure Churn Intervention Effectiveness
**Description:** System tracks whether at-risk customers who received interventions actually stay or leave.

**Acceptance Criteria:**
- Links intervention (e.g., email sent 2024-01-15) to outcome (purchase within 7/14/30 days: yes/no)
- Reports: % making purchase after intervention, % without intervention (control), lift
- Breakdown by intervention type (email vs. phone vs. offer type)
- Supports A/B testing: "Phone reactivation converted at 25%, email at 18%"

---

### **CUSTOMER LTV PREDICTION MODULE**

### REQ-006: Predict Customer Lifetime Value at Multiple Time Horizons
**Description:** For each customer, system predicts total lifetime spending at 7-day, 30-day, 90-day, and 1-year horizons.

**Acceptance Criteria:**
- Four LTV predictions per customer: 7-day, 30-day, 90-day, 1-year
- Prediction is expected total spend (USD) over time window
- Based on purchase history, product affinity, cohort patterns, seasonality
- New customers receive cohort-average prediction
- Updated daily as new purchase data arrives

---

### REQ-007: Identify High-Value Customer Cohorts
**Description:** System segments customers by predicted LTV and highlights value profiles.

**Acceptance Criteria:**
- Segments ranked by predicted LTV (high → low)
- Each segment includes: name, size, average LTV, key characteristics (order value, category preference, frequency)
- Analyst can drill into segments to see customers
- Segments refresh daily

---

### REQ-008: Flag Early Indicators of High-Value Customers
**Description:** System identifies newly acquired customers showing signals of becoming high-LTV.

**Acceptance Criteria:**
- For new customers (first purchase <7 days), flags high-potential prospects
- Signals: high first-purchase value (>$200), repeat purchase within 3 days, strong product affinity
- Flagged customers prioritized for email nurture, loyalty programs, VIP onboarding
- Prediction accuracy tracked: % of flagged customers becoming high-LTV within 90 days

---

### REQ-009: Compare Predicted vs. Actual LTV
**Description:** For historical customers, system shows prediction accuracy, tracking model drift.

**Acceptance Criteria:**
- For customers with complete 90-day / 1-year windows in past: predicted LTV vs. actual LTV
- Accuracy metrics: MAE, RMSE, calibration (are 50% predictions actually ~50% accurate?)
- Accuracy tracked over time to detect drift
- Analyst can export report: "Model accuracy by cohort" to spot segment-specific issues

---

### **CART ABANDONMENT & RECOVERY MODULE**

### REQ-010: Detect Abandoned Carts in Real-Time
**Description:** System identifies carts idle for configurable threshold (e.g., 1 hour) and flags as abandoned.

**Acceptance Criteria:**
- Every active cart monitored for idle time
- Cart marked abandoned if no updates for threshold (default: 1 hour, adjustable)
- Abandoned cart includes: abandon time, contents, cart value, customer ID, metadata
- Status updated in real-time (at least daily refresh)
- Filterable by time-to-abandon cohorts (1h, 6h, 24h, 7d)

---

### REQ-011: Score Carts by Recovery Likelihood
**Description:** System predicts which abandoned carts will convert if sent recovery offer.

**Acceptance Criteria:**
- Every abandoned cart receives recovery score (0–100)
- Score reflects probability of purchase if intervention sent
- Based on customer purchase history, cart composition, cart value, time-to-abandon, previous abandonment behavior
- Model performance measurable: AUC, precision, recall
- Score updates as new data arrives

---

### REQ-012: Explain Cart Abandonment with Interpretable Factors
**Description:** For each abandoned cart, system shows likely reasons WHY customer abandoned.

**Acceptance Criteria:**
- Shows 3–5 key abandonment factors:
  - "Shipping cost ($25) is 17% of cart value" (price sensitivity)
  - "Product out of stock for 5 days" (availability)
  - "Customer is price-sensitive (previous carts <$50)" (behavior)
  - "Mobile checkout (higher abandon rate)" (channel)
  - "Cart value $150+ (customers abandon expensive carts 2x more)" (composition)
- Factors include contribution scores
- Analyst can drill into factors to see supporting data
- Factors align with model internals

---

### REQ-013: Recommend Targeted Recovery Offers
**Description:** For each abandoned cart, system recommends specific intervention most likely to convert.

**Acceptance Criteria:**
- Recommends offer: discount %, free shipping, product substitution, or bundle incentive
- Personalized by abandonment reason, customer price sensitivity, product category
- Based on what worked for similar customers
- Includes expected conversion probability with offer
- Manager can override recommendation

---

### REQ-014: Segment Abandoned Carts by Recovery Potential
**Description:** Carts grouped into actionable tiers so marketing prioritizes high-impact recoveries.

**Acceptance Criteria:**
- Three tiers by recovery potential: High (60–100), Medium (30–59), Low (0–29)
- Each tier has recommended intervention intensity:
  - High: aggressive (15% discount, free shipping)
  - Medium: moderate (10% discount, free shipping)
  - Low: light-touch (5% discount via email)
- Tier counts visible and updated daily
- Thresholds adjustable by manager

---

### REQ-015: Measure Cart Recovery Effectiveness
**Description:** System tracks whether abandoned carts that received offers convert, measuring campaign lift and ROI.

**Acceptance Criteria:**
- Links abandonment event + recovery offer to conversion outcome (purchase: yes/no)
- For recovered carts: final purchase value, discount used, time-to-recovery
- Reports: recovery rate by offer type (10% discount → 18%, 15% → 22%, free shipping → 14%)
- Recovery rate by cohort (new vs. repeat, high-value vs. budget)
- Lift = (intervention rate − control rate) / control rate
- Weekly report: offers sent, converted, incremental revenue

---

### REQ-016: Track Lost Carts & Churn Risk
**Description:** System flags customers with repeated abandonment or high-value losses.

**Acceptance Criteria:**
- Flags customers with 3+ abandoned carts in 30 days (repeat abandoners)
- Flags carts totaling >$X in value (high-value losses)
- Flags customers not responding to offers (non-responders)
- Different strategies per type: investigate UX friction, offer VIP service, try different offer channels
- Analyst can export list of at-risk customers with abandonment patterns

---

### **DYNAMIC PRICING & DISCOUNT OPTIMIZATION MODULE**

### REQ-017: Recommend Optimal Discounts by Product & Cohort
**Description:** System analyzes abandonment patterns and price sensitivity to recommend discount strategies maximizing revenue.

**Acceptance Criteria:**
- Recommends discount levels based on:
  - Abandonment rate for product (products frequently abandoned)
  - Price elasticity (demand sensitivity to discount)
  - Historical recovery rate by discount level (10% recovers X%, 15% recovers Y%)
  - Inventory level (low stock → no discount; overstock → aggressive discount)
  - Margin targets (never drop below X%)
- Recommendations personalized by customer segment (new vs. repeat, high-value vs. budget)
- Includes confidence level (high/medium/low)
- Updated daily as new abandonment data arrives

---

### REQ-018: Quantify Revenue Impact of Discount Strategies
**Description:** For each discount recommendation, system estimates impact on revenue, margin, and volume.

**Acceptance Criteria:**
- Shows: product, current price, recommended discount, expected recovery lift (%)
- Expected volume change (e.g., "+50 units/day")
- Revenue impact: "$X more/day" or "−$X less/day"
- Margin impact: "Keep 28%" or "Drop to 22%"
- Net ROI: discount cost vs. incremental revenue captured
- Top 20 products by revenue impact visible
- Revenue impact measured ex-post to validate model

---

### REQ-019: Test Discount Strategies via A/B Testing
**Description:** Manager can run controlled experiments measuring which discount levels drive best results.

**Acceptance Criteria:**
- Manager defines experiment: treatments (10% discount, 15% discount, free shipping, control), metric (recovery rate), duration (1 week)
- System randomly assigns carts to treatment/control
- Reports: recovery rate per treatment, lift vs. control, statistical significance (p-value), confidence interval
- Revenue and margin impact per treatment
- Results inform broad discount rollout: "15% works best; scale it up"

---

### REQ-020: Set Price & Discount Guardrails
**Description:** Manager defines business rules (min/max discounts, margin floors) keeping recommendations sensible and compliant.

**Acceptance Criteria:**
- Sets constraints: min/max discount per product, margin floor, max discounts per customer per month, bundle rules
- Recommendations always respect constraints
- Bulk updates (e.g., "clearance items: max 40% off")
- Constraint violations logged for audit
- Warns if constraints too tight and prevent good recovery opportunities

---

### REQ-021: Handle Inventory-Driven Discounting
**Description:** System adjusts discount recommendations based on inventory (clear overstock, protect low-stock).

**Acceptance Criteria:**
- Inventory level factored into recommendation
- Overstock (>60 days supply): aggressive discounts to accelerate clearance
- Understocked (<7 days supply): reduced discount or non-monetary incentive (free shipping)
- Out of stock: recommends product substitution
- System alerts on inventory-driven pricing decisions

---

### REQ-022: Prevent Discount Abuse & Margin Erosion
**Description:** System monitors discount usage preventing gaming and margin degradation.

**Acceptance Criteria:**
- Tracks per-customer discount usage in last 30/90 days
- Alerts if: customer receives >3 offers in 30 days (training for discounts?), discount usage >40% for product (recurring dependency?), average margin trending down
- Manager can set caps: "Customer max 2 discounts per quarter", "Product >30% discounted sales → delist or raise baseline price"

---

### **UNIFIED PLATFORM FEATURES**

### REQ-023: Unified Dashboard with Cross-Module Insights
**Description:** Single dashboard shows churn, LTV, cart abandonment, and pricing insights together highlighting connections.

**Acceptance Criteria:**
- Three panels: churn summary (count by tier, top at-risk), LTV summary (avg LTV, high-value cohort, new high-potential), recovery summary (carts abandoned, recovery rate, recommendations pending)
- Cross-module insight: "High-churn customers typically low-LTV; recommend VIP nurture"
- Can navigate to detailed view for any panel
- All metrics update daily

---

### REQ-024: Coordinated Campaign Management
**Description:** Manager can create campaigns coordinating churn interventions, cart recoveries, and pricing strategies.

**Acceptance Criteria:**
- Manager defines campaign: e.g., "Q1 retention: high-churn + abandoned-cart customers, 15% discount + free shipping"
- Auto-selects audience by criteria (churn score >70, recovery score >60)
- Sets offer details, scheduling, channels
- System exports campaign file (CSV, API) with customer IDs, emails, offer codes
- Integrates with email/SMS platform
- Tracks: sent, converted, revenue, margin, ROI

---

### REQ-025: Price Elasticity Learning
**Description:** System learns actual price elasticity from experiments and recovery outcomes, improving future recommendations.

**Acceptance Criteria:**
- Maintains elasticity estimate per product: "10% discount → 15% recovery, 15% discount → 22% recovery"
- Elasticity = (% change in recovery rate) / (% change in discount)
- Updates as new experiment data arrives
- Broken down by cohort (new vs. repeat may differ)
- Analyst can visualize "discount % vs. recovery rate" curve
- Model learns from actuals, improving future recommendations

---

### REQ-026: Unified Customer Intelligence & Explainability
**Description:** Analyst can drill into any customer and see churn, LTV, abandonment history, and pricing response together.

**Acceptance Criteria:**
- Customer detail view shows:
  - Churn risk score + top 3 drivers
  - LTV prediction (7/30/90/365-day) + top value drivers
  - Recent abandoned carts + reasons
  - Pricing history (discounts received, response to price changes)
  - Intervention history (campaigns sent, responses)
- Cross-module insight: "High-value, high-churn → recommend VIP service, not discount"
- Analyst can export customer profile for CRM

---

### REQ-027: Model Performance Monitoring
**Description:** Analyst tracks whether models are accurate and alerts if performance degrades.

**Acceptance Criteria:**
- Dashboard shows metrics (updated weekly):
  - Churn prediction: AUC, precision, recall
  - LTV prediction: MAE, RMSE, calibration
  - Cart recovery prediction: AUC, calibration
  - Elasticity accuracy: do predicted recovery rates match actuals?
- Broken down by cohort (new customers, high-value, etc.) to spot segment-specific drift
- Alerts if accuracy drops below threshold (e.g., AUC < 0.75)
- Root cause hints: "Accuracy down for mobile; retrain on recent mobile data"

---

### REQ-028: Data Freshness and Latency Transparency
**Description:** Users understand how recent data is and when predictions were last updated.

**Acceptance Criteria:**
- Timestamps shown for: Cassandra refresh ("2 min ago"), Iceberg refresh ("daily 2 AM UTC"), model scoring ("daily 3 AM")
- Latency acceptable for use case: churn/LTV/abandonment within 24h, pricing daily
- Alerts if SLA exceeded (e.g., "Recommendations stale >24h")
- Campaign send timestamps tracked

---

### REQ-029: Export and Integration
**Description:** Users export insights and integrate with downstream systems (email, CRM, pricing engine).

**Acceptance Criteria:**
- Manager can export: churn lists (CSV), LTV cohorts (CSV), recovery carts (CSV), pricing recommendations (CSV), campaign results (CSV)
- Exports timestamped with freshness metadata
- Can schedule exports (e.g., "churn list every Monday morning")
- API endpoints for programmatic access (third-party systems can pull)
- Integration example: "Platform pushes recovery email list to Klaviyo every 6 hours"

---

### REQ-030: Authentication and Multi-Tenancy
**Description:** Each company sees only its own data; no cross-contamination.

**Acceptance Criteria:**
- Users log in with credentials tied to company
- Dashboards show only that company's customers, products, carts, transactions
- Data isolated at database level, not just UI
- Audit log tracks who accessed what and when
- Fine-grained access control: e.g., "Marketing sees carts/offers, Pricing sees recommendations"

---

## Out of Scope

The following are explicitly **NOT** part of this platform:

- **Trade execution:** System does not send emails, apply discounts, or execute campaigns; recommendations only.
- **Inventory management:** No stock replenishment, purchase orders, or supply chain tools.
- **Customer service / support tickets:** No ticketing or support workflows.
- **Product categorization:** Assumes catalog pre-loaded and categorized.
- **Fraud detection:** Does not flag fraudulent transactions or customers.
- **International / multi-currency:** All pricing and LTV in USD; no forex or regional strategies.
- **Subscription / recurring revenue:** Transaction-based e-commerce only; not subscriptions.
- **Product recommendations:** No "you may also like" system (cart context only for recovery).
- **Email/SMS sending:** No email/SMS platform; exports lists for manager's own tool.
- **Custom ML models:** Uses pre-trained standard models; no end-user model training/tuning.
- **Real-time bidding / ad pricing:** Owned-channel recovery focus; not ad spend optimization.
- **Checkout redesign:** Does not redesign checkout flow.
- **Returns / refunds:** Does not model return likelihood (assumes data exists, used as signal).
- **Loyalty program management:** Does not manage loyalty points, tiers, or rewards.
- **Mobile app integration:** Web checkout focus; does not cover in-app purchases.

---

## Success Criteria (End-to-End)

The platform is successful when:

1. **Churn:** Marketing identifies top 1,000 at-risk customers in <2 min; intervention lift ≥5% (vs. control)
2. **LTV:** New customers segmented by value; high-potential customers flagged in first 7 days with >70% accuracy
3. **Cart Recovery:** Manager identifies top 500 recoverable carts in <2 min; recovery lift ≥5% (vs. baseline)
4. **Pricing:** Pricing manager sees recommendations in <1 min; implementing top 20 yields ≥3% incremental revenue
5. **Data Freshness:** All dashboards updated within 24h; no stale predictions
6. **Explainability:** Analyst drills into any prediction (customer, cart, price) and understands top factors in <1 min
7. **ROI Measurable:** CFO reports churn interventions saved $X in LTV, cart recovery added $Y, pricing generated $Z; net 4x+ ROI
8. **Model Accuracy:** Churn AUC >0.80, LTV MAE <10% of avg, cart recovery AUC >0.75, elasticity captures real demand response
9. **A/B Testing:** Manager runs experiment, measures significance with confidence intervals, applies winning strategy
10. **Integration:** Exports work seamlessly; data flows to email/CRM/pricing tools without manual work
