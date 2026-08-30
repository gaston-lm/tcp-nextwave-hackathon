# Transaction generator

All files needed to run the generator live under `scripts/ingestion/`, alongside the
ingestion flow that they feed.

Editable parameters are centralized in [`generation_config.py`](generation_config.py): decline
rates and offsets, ISO-8583 code distribution, merchants, countries, providers, payment methods,
banks, spend, hourly volume, dates, seed, and row count. Probabilities use decimals (`0.17` means
`17%`), while `weight` values are relative weights.

## Generator files

- [`generation_config.py`](generation_config.py): contains every editable dataset parameter.
  Configure default dates and row count, currencies and exchange rates, spend distribution,
  merchants, countries, providers, payment methods, banks, volume weights by day and hour,
  decline probabilities, offsets, and ISO-8583 code distribution here.
- [`dataset_generator.py`](dataset_generator.py): the generation engine. It combines parameters,
  calculates the natural decline probability, applies the winning incident rule, generates
  timestamps and monetary values, writes the CSV, and audits its schema and consistency.
- [`app.py`](app.py): starts the local HTTP server. It serves the HTML and configuration,
  generation, and download endpoints. It also validates rows, filenames, dates, hours, provider
  rates, and rules before calling the engine.
- [`index.html`](index.html): contains the Control Tower interface, styling, and browser logic.
  It lets users choose row count, output file, dates, hours, base rates, and ISO-8583-code-specific
  increments.
- [`generate_baseline.py`](generate_baseline.py): runs a reproducible generation of one million
  transactions using the configured seed and time period, then audits the result.
- [`generate_dataset.ipynb`](generate_dataset.ipynb): provides an interactive Jupyter alternative
  for configuring rules, generating the dataset, and reviewing an audit sample.
- [`decisiones_dataset.md`](decisiones_dataset.md): documents the modeling decisions, sources,
  assumptions, probability formulas, code distribution, and rule behavior.
- [`README.md`](README.md): explains the generator structure and how to run its two main flows.

From the project root, generate the 1,000,000-row baseline:

```bash
python scripts/ingestion/generator/generate_baseline.py
```

Start the UI to control live ingestion:

```bash
make ingestion-generator
```

Open [http://127.0.0.1:8002](http://127.0.0.1:8002), start or stop the stream, and enable one of
the two preselected simulations: a global failure spike or a MercadoPago-specific one.

## Accelerated live ingestion

With PostgreSQL running and configured in `data/.env`, the same UI controls ingestion directly
into the database. Choose the **average transactions per minute** and press **Start live ingestion**.
The server starts one second after the latest persisted `issued_timestamp`, or at the current second
when the database is empty. Each real second inserts a batch for one second of timestamps while
preserving the configured transaction average across the minute. This lets a restarted stream
continue the existing timeline without overlaps. Each hour receives its own normal volume profile
with a 35% standard deviation, and each second varies by 15% around that profile. The rates and
rules visible at startup are frozen for that run. **Stop** stops the stream after the current batch.

The **Global failure spike** toggle sets an 85% base decline rate for every provider. **Break
MercadoPago** does the same for MercadoPago only. **Break BancoEstado in Chile** adds 80 percentage
points of decline probability to BancoEstado transactions in Chile, using ISO-8583 code `51`.
Scenarios are mutually exclusive and take effect from the next second. Turning one off returns the
stream to the default normal profile.

The generator server uses port `8002` by default so it does not compete with the Dashboard API
(`8000`). Install the required dependencies with:

```bash
pip install -r scripts/ingestion/requirements.txt
```

Both `baseline.csv` and CSVs generated from the UI are saved to
`scripts/ingestion/generator/`, regardless of the directory from which the command is run.
