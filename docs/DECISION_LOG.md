# Decision Log — TCP

NextWave Hackathon 2026 · Buenos Aires

## 1. Initial data generation `T+01:30`

**Options considered**

- Which countries should we include? Mix of high-population and smaller markets?
- Which merchants and banks?
- Which payment providers?

**Chosen:** 4 countries (Argentina, Mexico, Brazil, Chile) with 2 merchants (Walmart and Cencosud) and major banks/providers

**Why:** We wanted 3 large Latin American markets plus one smaller one to test different scenarios. Walmart is in Chile and Mexico (big and small markets), while Cencosud is everywhere except Mexico. This mix lets us see patterns across different market sizes and merchant reach (while still having a big enough realistic stream of data to test).

---

## 2. Transaction schema design `T+02:35`

**Options considered**

- Keep all transaction data flat and simple, or organize it with relationships between merchants, providers, and payment methods?
- Use separate lookup tables, or cram everything into one big transactions table?
- Pros and cons: separate tables mean cleaner data but more complex queries.

**Chosen:** Normalized schema with three tables: transactions, methods_by_provider, and providers_by_merchant

**Why:** Separating the data lets us look at decline patterns from different angles (by merchant, by provider, etc.) without storing the same info over and over. It's cleaner and makes queries faster.

---

## 3. Database host `T+03:10`

**Options considered**

- We wanted a database that was familiar to the team and well-suited to an MVP application.
- We considered BigQuery because we were more familiar with its SQL dialect, but we also evaluated PostgreSQL.

**Chosen:** PostgreSQL

**Why:** It's solid for what we're doing, handles all the relationships between our tables, and the team knows how to work with it. No need to overcomplicate things.

---

## 4. Transaction window `T+03:40`

**Options considered**

- Check every X amount of time, or count transactions instead?
- With low traffic, a time window might not have enough data
- But counting transactions could take forever to fill up

**Chosen:** Time window evaluated every 5 minutes

**Why:** The data being checked every 5 minutes gives us a good view of what's happening without making the system slow. It's a nice middle ground for an MVP.

---

## 5. Ingestion pipeline architecture `T+03:45`

**Options considered**

- Do we load data from history and stream live transactions in one go, or separate them?
- Running both at once could mess things up and make debugging hard
- Separating lets each one scale and run on its own schedule

**Chosen:** Unified pipeline with streaming data ingestion and historical data loading capability

**Why:** We can watch new transactions as they come in, and also go back and load old data when we need to test things. Keeps them separate so they don't get in each other's way.

---

## 6. Decline probabilities `T+04:00`

**Options considered**

- How detailed should our decline predictions be?
- Could look at merchant, provider, country, payment method, time of day, day of week, etc.
- More detail = slower and more complicated, but more accurate

**Chosen:** Merchant-based baseline with a day of the week historical window, refreshed every five minutes.

**Why:** Looking at each merchant separately keeps things fast and simple for now. Later we can add more details if we need to, like breaking it down by country or time of day. For the data generation, we used Codex to help pick the probabilities, but we reviewed them ourselves to make sure they made sense. For example, wallet payments have an offset that makes declines less likely.

---

## 7. Go back in time `T+04:15`

**Options considered**

- Search specific incidents, or look at lots of history and take duplicates?
- Being specific means we might miss related issues or slow down searches
- Broader searches are faster but might show us the same problem twice

**Chosen:** Low granularity with human review

**Why:** Keeping things simple means searches are fast. We're okay with maybe seeing some duplicate alerts—a human can spot if it's the same issue coming back or something totally new. Plus we can see if what we tried last time actually worked.

---

## 8. Control tower interface and API `T+06:30`

**Options considered**

- Command line, web interface, or both?
- What should people see and be able to do with it?

**Chosen:** RESTful API with a web-based dashboard frontend for real-time monitoring

**Why:** A web dashboard is friendly for people who don't code, so they can see what's going on in real time. The API lets us build different frontends later or plug it into other tools.

---

## 9. Separate history loading from live streaming `T+06:40`

**Options considered**

- Keep loading old data and processing new data together, or handle them separately?
- Both at once could cause conflicts and race conditions
- Separate lets us load history without interrupting the live feed

**Chosen:** Split into `load_history.py` and `stream_ingest.py` with independent execution

**Why:** Keeping them separate makes the code cleaner and easier to test. We can load old data whenever we want without messing with the live transaction feed.

---

## 10. Provider decline simulator `T+07:00`

**Options considered**

- How can we show the system working in a live demo?
- Simulate failures at the transaction level, merchant level, or provider level?
- What should people be able to tweak—country, merchant, payment method, provider, all of them?

**Chosen:** Provider-level simulator with configurable dimensions (country, merchant, method)

**Why:** It's impactful for the demo without being too complicated to build. People can play with country, merchant, and payment method to see how the system reacts in different situations.

---

## 11. Frontend-API connectivity and deployment `T+07:30`

**Options considered**

- Frontend and API on the same server, or separate?
- How does the frontend find the API in different environments?

**Chosen:** Environment-based configuration with `.env.example` documentation for different deployment scenarios

**Why:** Using a config file means the dashboard can talk to different servers depending on where it's running—dev, staging, production—without changing code. Easy to point it wherever it needs to go.

---

## 12. Pitch first draft `T+07:40`

**Options considered**

- Formal and technical, or relaxed and conversational?
- Formal sounds professional but might not click with engineers
- Casual might seem less serious but easier to remember

**Chosen:** Relaxed, conversational tone with metaphors and engineering-focused examples

**Why:** We're engineers talking to engineers, so we kept it real. Using examples people get—like not waking up at 3am to fix stuff, or normal glitches vs. sketchy activity—makes it stick without sounding like marketing.

---

## 13. UI for incident generator `T+08:00`

**Options considered**

- How do we show the system working in a live demo?
- Should we be able to simulate just single factors, or mix multiple failures?
- What dimensions should we be able to tweak?

**Chosen:** Simple UI to generate failures by provider + single factors (country, merchant, or payment method combinations)

**Why:** We built a program to create problems in the data stream to show it working. We thought about making it more complex—simulating errors by merchant first or breaking code changes in the product, but decided to keep it simple since this isn't part of the final product, just a demo tool. 

---

## 14. Estimation from historic decline `T+08:30`

**Options considered**

- Compare against all historical data, or just the last 5 minutes?
- Do we even have enough transactions in 5 minutes to make a good call?
- Too much history slows things down without helping much

**Chosen:** One baseline per day of the week for each combination of dimensions

**Why:** One baseline per day keeps things simple and doesn't slow us down. We have enough data to spot anomalies without bogging down the system with too much history.

---


## 15. Test of V0 `T+09:00`

**Options considered**

- How fast should demo data move compared to real time?
- Real speed would be boring to watch—detection would take forever to kick in

**Chosen:** 1 minute of ingested data = 1 second in real-time demonstration

**Why:** If we ran at real speed, nothing would happen for ages during the demo. Speeding it up 60x lets people see the system catch problems in real time. V0 testing worked great with this, and it's actually more impressive than waiting around.

---

## 16. Scoping of agent architecture `T+10:00`

**Options considered**

- How do we organize the different tasks the system needs to do?
- One big agent that does everything, or break it into smaller pieces?
- What actions are even possible to take? What counts as normal noise vs the beginning of an incident?

**Chosen:** Three chained agents: anomaly detector → incident reviewer → action taker

**Why:** Breaking it into three agents lets each one focus on what it's good at. The first detects, the second figures out what's actually going on, and the third decides what to do about it.

---

## 17. Anomaly detector `T+10:30`

**Options considered**

- How do we find what actually went wrong in all this transaction data?
- Do we look at one thing at a time, or try to see the full picture?
- What if multiple things break at the same time?

**Chosen:** 5-minute window with a funnel that finds the most relevant dimensions

**Why:** We run the data through a funnel to pick out which dimensions matter most for each failure. It can spot multiple failures happening at the same time and tag them with a signature so we remember them.

---

## 18. Incident reviewer `T+11:00`

**Options considered**

- What context do we need to understand an incident?
- Are there past issues we should know about?
- Could a recent deploy be related?
- What if we could pull in external status reports from providers?

**Chosen:** Check past incidents, look for related deploys, and optionally include external status data

**Why:** The reviewer agent needs the full picture. It checks if this is a duplicate issue we already know about, or if it's connected to a past problem or a code change. This agent gives us the real diagnosis.

---

## 19. Action taker `T+12:00`

**Options considered**

- What should this agent actually do?
- How much can it figure out on its own?
- Are there different types of issues that need different responses?

**Chosen:** Scope actions by type, internal (things we can fix) vs external (things we notify about)

**Why:** Different problems need different fixes. Some we can solve inside our product, others we need to tell the provider or merchant about. Knowing which is which helps us pick the right action.

---

## 20. Harness discussion `T+13:00`

**Options considered**

- Let the agent do whatever it thinks is right?
- Keep tight control over what actions it can take?
- How do we make this fast enough for real-time without losing safety?

**Chosen:** Agents chained with a scoped set of actions instead of the total free will that harness provides

**Why:** Real-time means we need fast, predictable responses. With predefined agents with their playbooks keeps things safe and controlled. This way we can watch what's happening and step in if needed. Plus, the design is flexible, we can add new agents later at any point of the chain to make the analysis even better.


---

## 21. Agent scope expansion `T+13:30`

**Options considered**

- What other information could help the agents make better decisions?
- Should we integrate external data like provider status reports?
- Could merchants have preferences for which providers to use?
- Should merchants be able to set custom alert preferences and traffic control?

**Chosen:** Framework to allow future expansion of agent capabilities

**Why:** We see possibilities for adding more layers—external data like provider downtimes, merchant preferences for provider failover, custom alerts, and traffic control. We're building the architecture now to support these features, so we can add them later without breaking what's already working.

---

## 22. Definition of test cases and fine tuning `T+14:00`

**Options considered**

- How do we know our system actually works?
- Does the agent chain handle different types of failures correctly?
- What scenarios should we test?

**Chosen:** Multiple test cases covering real-world scenarios

**Why:** We built test cases to break our system on purpose. We want to make sure everything works together. We test things like a provider going down everywhere, a spike in fraud in Argentina, and scenarios where past issues or recent code changes might break everything. This way we know what we're working with before we show it to people.

---

## 23. Change of Transaction Window  `T+22:00`

**Options considered**

- Maintain the 5 minutes window or change it into 1 minute.

**Chosen:** Change it into 1 minute

**Why:** After some discussion, we think that the 1 minute window is a lot more realistic and it lets us inject data every 10 seconds.
