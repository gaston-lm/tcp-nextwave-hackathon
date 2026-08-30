# The Control Tower

A system that watches payments live, detects when conversion drops, diagnoses the root cause with evidence and explains it in human language — before the merchant finds out on Twitter.

### Key definitions
- Provider: external processor that handles the payment (Stripe, Adyen, dLocal, MercadoPago)
- Payment method: card, PSE, wallet, PIX, cash-in-store
- Conversion (approval rate): % of approved payments over attempted payments — the metric that moves the most money
- Issuing bank: the bank that issued the buyer's card; it can decline on its own
- Decline code: the reason the provider returns when a payment doesn't approve
- Dimensions of a transaction: merchant × provider × method × country × issuing bank × decline code — the diagnosis lives in those intersections
- Root cause: the real origin of the problem, not the symptom ("provider X declines bank Y's cards in Brazil since 14:03", not "conversion dropped")

## 1. The problem
Conversion drops silently and for a thousand different reasons: a degraded provider, an issuing bank over-declining, a method down in one country, a change nobody announced. Every lost point of conversion is money lost by the minute. Today detection is artisanal:
- A human looks at dashboards when they can
- Classic alerts fail at both ends: they either fire on everything (and get ignored) or on nothing
- By the time someone notices the drop, hours have passed

And detecting is the easy part. The hard part is the diagnosis: is the drop a provider's, a method's, a country's, an issuing bank's, a merchant's? The answer is scattered across thousands of transactions, and today a tired human assembles it by crossing filters at 3 a.m.

## 2. Objective
Build a monitoring and diagnosis system that:
- Watches a live transaction stream and detects conversion drops that matter, distinguishing them from normal noise (time of day, weekends, statistical variance)
- Diagnoses the root cause by navigating the dimensions (merchant × provider × method × country × issuing bank × decline code) until it isolates where the problem is
- Explains with evidence: what dropped, since when, who it affects, how much money it's costing and why the system believes that — in language an operations person understands
- Prioritizes when several things happen at once, and honestly says when the evidence isn't enough
- Recommends an action for the human — without executing it (this challenge diagnoses, it doesn't remediate)

May include (not limited to): estimating the money cost of each incident; comparison against expected historical behavior; memory of past incidents to recognize repeats.

Trial by fire. The judges will inject live an incident the team never rehearsed (a new combination of
dimensions) — the system must detect and diagnose it correctly in front of everyone.

## 3. Expected results

A demo showing:
- A (mocked) payment stream running normally, and the system not firing on noise
- A real drop injected live → detected in reasonable time
- The correct root-cause diagnosis, with the evidence visible: what, where, since when, who is affected
- The readable explanation + the estimated cost + the recommended action
- A case with two simultaneous incidents correctly separated and prioritized
- The trial by fire passed

Bonus points
- A case where the system admits the evidence isn't enough, instead of inventing a diagnosis
- Recognizing a repeated incident (&quot;this already happened on Tuesday&quot;) using memory
- An explanation consumable by two audiences: operations (detail) and an executive (one line with the money)

## 4. Minimal fictional case

- Scenario: PagoTotal, an orchestrator processing payments for 3 merchants with 3 providers in Mexico,
Colombia and Brazil (invented, extensible data and volumes).

Key moments:
1. Normal operation — the system watches and doesn't bother anyone
2. A provider starts over-declining only in Brazil → detection + diagnosis
3. At the same time, a Mexican issuing bank goes down for a single merchant → the system separates the two stories and prioritizes them
4. The judges inject their own incident (trial by fire)