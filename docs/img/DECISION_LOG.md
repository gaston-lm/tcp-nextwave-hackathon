# Decision Log — TCP

NextWave Hackathon 2026 · Buenos Aires

## 1. Transaction schema design `T+02:35`

**Options considered**

- Keep all transaction data flat and simple, or organize it with relationships between merchants, providers, and payment methods?
- Use separate lookup tables, or cram everything into one big transactions table?
- Pros and cons: separate tables mean cleaner data but more complex queries.

**Chosen:** Normalized schema with three tables: transactions, methods_by_provider, and providers_by_merchant

**Why:** Separating the data lets us look at decline patterns from different angles (by merchant, by provider, etc.) without storing the same info over and over. It's cleaner and makes queries faster.

---

## 2. Database host `T+03:10`

**Options considered**

- We wanted a database that was familiar to the team and well-suited to an MVP application.
- We considered BigQuery because we were more familiar with its SQL dialect, but we also evaluated PostgreSQL.

**Chosen:** PostgreSQL

**Why:** It's solid for what we're doing, handles all the relationships between our tables, and the team knows how to work with it. No need to overcomplicate things.

---

## 3. Transaction window `T+03:40`

**Options considered**

- Check one day's worth of data, or count transactions instead?
- With low traffic, a time window might not have enough data
- But counting transactions could take forever to fill up

**Chosen:** Time window (1 day, evaluated every 5 minutes)

**Why:** One day of data checked every 5 minutes gives us a good view of what's happening without making the system slow. It's a nice middle ground for an MVP.

---

## 4. Ingestion pipeline architecture `T+03:45`

**Options considered**

- Do we load data from history and stream live transactions in one go, or separate them?
- Running both at once could mess things up and make debugging hard
- Separating lets each one scale and run on its own schedule

**Chosen:** Unified pipeline with streaming data ingestion and historical data loading capability

**Why:** We can watch new transactions as they come in, and also go back and load old data when we need to test things. Keeps them separate so they don't get in each other's way.

---

## 5. Decline probabilities `T+04:00`

**Options considered**

- How detailed should our decline predictions be?
- Could look at merchant, provider, country, payment method, time of day, day of week, etc.
- More detail = slower and more complicated, but more accurate

**Chosen:** Merchant-based baseline with a one-day historical window, refreshed every five minutes.

**Why:** Looking at each merchant separately keeps things fast and simple for now. Later we can add more details if we need to, like breaking it down by country or time of day.

---

## 6. Go back in time `T+04:15`

**Options considered**

- Search specific incidents, or look at lots of history and take duplicates?
- Being specific means we might miss related issues or slow down searches
- Broader searches are faster but might show us the same problem twice

**Chosen:** Low granularity with human review

**Why:** Keeping things simple means searches are fast. We're okay with maybe seeing some duplicate alerts—a human can spot if it's the same issue coming back or something totally new. Plus we can see if what we tried last time actually worked.

---

## 7. Control tower interface and API `T+06:30`

**Options considered**

- Command line, web interface, or both?
- What should people see and be able to do with it?

**Chosen:** RESTful API with a web-based dashboard frontend for real-time monitoring

**Why:** A web dashboard is friendly for people who don't code, so they can see what's going on in real time. The API lets us build different frontends later or plug it into other tools.

---

## 8. Separate history loading from live streaming `T+06:40`

**Options considered**

- Keep loading old data and processing new data together, or handle them separately?
- Both at once could cause conflicts and race conditions
- Separate lets us load history without interrupting the live feed

**Chosen:** Split into `load_history.py` and `stream_ingest.py` with independent execution

**Why:** Keeping them separate makes the code cleaner and easier to test. We can load old data whenever we want without messing with the live transaction feed.

---

## 9. Provider decline simulator `T+07:00`

**Options considered**

- How can we show the system working in a live demo?
- Simulate failures at the transaction level, merchant level, or provider level?
- What should people be able to tweak—country, merchant, payment method, provider, all of them?

**Chosen:** Provider-level simulator with configurable dimensions (country, merchant, method)

**Why:** It's impactful for the demo without being too complicated to build. People can play with country, merchant, and payment method to see how the system reacts in different situations.

---

## 10. Frontend-API connectivity and deployment `T+07:30`

**Options considered**

- Frontend and API on the same server, or separate?
- How does the frontend find the API in different environments?

**Chosen:** Environment-based configuration with `.env.example` documentation for different deployment scenarios

**Why:** Using a config file means the dashboard can talk to different servers depending on where it's running—dev, staging, production—without changing code. Easy to point it wherever it needs to go.

---

## 11. Pitch first draft `T+07:40`

**Options considered**

- Formal and technical, or relaxed and conversational?
- Formal sounds professional but might not click with engineers
- Casual might seem less serious but easier to remember

**Chosen:** Relaxed, conversational tone with metaphors and engineering-focused examples

**Why:** We're engineers talking to engineers, so we kept it real. Using examples people get—like not waking up at 3am to fix stuff, or normal glitches vs. sketchy activity—makes it stick without sounding like marketing.

---

## 12. Estimation from historic decline `T+08:30`

**Options considered**

- Compare against all historical data, or just the last 5 minutes?
- Do we even have enough transactions in 5 minutes to make a good call?
- Too much history slows things down without helping much

**Chosen:** One baseline per day of the week for each combination of dimensions

**Why:** One baseline per day keeps things simple and doesn't slow us down. We have enough data to spot anomalies without bogging down the system with too much history.

---

## 13. Test of V0 `T+9:00`

**Options considered**

- How fast should demo data move compared to real time?
- Real speed would be boring to watch—detection would take forever to kick in

**Chosen:** 1 minute of ingested data = 1 second in real-time demonstration

**Why:** If we ran at real speed, nothing would happen for ages during the demo. Speeding it up 60x lets people see the system catch problems in real time. V0 testing worked great with this, and it's actually more impressive than waiting around. 