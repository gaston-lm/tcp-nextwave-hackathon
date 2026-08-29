# Issue analysis output contract

Each analysis must create or update one incident with the following dashboard-ready information.

## 1. Issue identity

- `incident_key`: Human-readable identifier, such as `URG-3159`.
- `title`: Short statement of the detected payment problem.
- `severity`: `urgent`, `high`, `medium`, or `low`.
- `status`: `open`, `monitoring`, or `resolved`.
- `started_at` and `last_seen_at`: When the pattern began and was last observed.

## 2. Scope

- `country`: Country affected by the pattern.
- `provider_name`: Provider involved, when applicable.
- `affected_transaction_count`: Number of affected transactions.

## 3. Overview

Provide a short, evidence-based explanation of the issue. It should state what changed, the affected payment flow, and the likely source or concentration of the problem. This is displayed in the Overview card.

## 4. Impact metrics

- `estimated_impact`: Estimated monetary impact in USD.
- `approval_rate_drop`: Approval-rate decrease, expressed as a percentage-point value.
- `affected_transaction_count`: Number of impacted transactions.

## 5. Agent action taken

Add one concise, past-tense `agent_action` summary directly to the incident. This is the action headline shown in the frontend. Set `agent_action_at` to the time the action occurred.

Example: “Rerouted eligible Argentine transfers to the secondary provider and notified merchant operations.”
