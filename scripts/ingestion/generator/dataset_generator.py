import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from generation_config import (
    BANK_DECLINE_OFFSETS,
    BANK_LINKED_METHODS,
    BANK_METHOD_DECLINE_OFFSETS,
    COLUMNS,
    COUNTRIES,
    COUNTRY_DECLINE_OFFSETS,
    DECLINE_CODES,
    DEFAULT_PROVIDER_DECLINE_RATES,
    END_DATE,
    HOUR_WEIGHTS,
    MERCHANT_DECLINE_OFFSETS,
    MERCHANTS,
    METHOD_DECLINE_OFFSETS,
    METHOD_IDS,
    N_TRANSACTIONS,
    OUTPUT_FILENAME,
    PROVIDER_IDS,
    RULE_DIMENSIONS,
    SEED,
    START_DATE,
    WEEKDAY_WEIGHTS,
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / OUTPUT_FILENAME
RULE_FIELDS = {"provider", "decline_increase", "decline_code", *RULE_DIMENSIONS}


def default_provider_rates():
    return DEFAULT_PROVIDER_DECLINE_RATES.copy()


def validate_provider_rates(provider_rates):
    validated = default_provider_rates()
    if provider_rates is None:
        return validated
    if not isinstance(provider_rates, dict):
        raise ValueError("Las tasas de proveedor deben ser un objeto")

    for provider, rate in provider_rates.items():
        if provider not in PROVIDER_IDS:
            raise ValueError(f"Proveedor inválido: {provider}")
        if isinstance(rate, bool):
            raise ValueError("Cada probabilidad debe estar entre 0 y 1")
        rate = float(rate)
        if not 0 <= rate <= 1:
            raise ValueError("Cada probabilidad debe estar entre 0 y 1")
        validated[provider] = rate
    return validated


def _matching_combinations(rule):
    provider = rule["provider"]
    for country, country_data in COUNTRIES.items():
        if rule["country"] is not None and rule["country"] != country:
            continue
        if provider not in country_data["providers"]:
            continue
        for merchant_data in MERCHANTS.values():
            merchant = merchant_data["name"]
            if country not in merchant_data["country_weights"]:
                continue
            if rule["merchant"] is not None and rule["merchant"] != merchant:
                continue
            for method in country_data["providers"][provider]:
                if rule["method"] is not None and rule["method"] != method:
                    continue
                issuing_banks = (
                    country_data["banks"] if method in BANK_LINKED_METHODS else ["N/A"]
                )
                for issuing_bank in issuing_banks:
                    if (
                        rule["issuing_bank"] is not None
                        and rule["issuing_bank"] != issuing_bank
                    ):
                        continue
                    yield provider, merchant, country, method, issuing_bank


def validate_decline_rules(rules, provider_rates=None):
    if rules is None:
        return []
    if not isinstance(rules, list):
        raise ValueError("Las reglas deben ser una lista")

    rates = validate_provider_rates(provider_rates)
    merchant_names = {data["name"] for data in MERCHANTS.values()}
    bank_names = {"N/A", *BANK_DECLINE_OFFSETS}
    validated = []
    for index, raw_rule in enumerate(rules, start=1):
        if not isinstance(raw_rule, dict):
            raise ValueError(f"Regla {index}: debe ser un objeto")
        unknown_fields = set(raw_rule) - RULE_FIELDS
        if unknown_fields:
            raise ValueError(
                f"Regla {index}: campos inválidos {sorted(unknown_fields)}"
            )
        provider = raw_rule.get("provider")
        if provider not in PROVIDER_IDS:
            raise ValueError(f"Regla {index}: proveedor inválido")
        increase = raw_rule.get("decline_increase")
        if isinstance(increase, bool) or increase is None:
            raise ValueError(f"Regla {index}: incremento inválido")
        increase = float(increase)
        if not 0 < increase <= 1:
            raise ValueError(
                f"Regla {index}: el incremento debe ser mayor que 0 y hasta 100%"
            )
        decline_code = raw_rule.get("decline_code")
        if isinstance(decline_code, bool) or not isinstance(decline_code, int):
            raise ValueError(f"Regla {index}: código de rechazo inválido")
        if decline_code not in DECLINE_CODES:
            raise ValueError(f"Regla {index}: código de rechazo inválido")

        rule = {
            "provider": provider,
            "decline_increase": increase,
            "decline_code": decline_code,
        }
        for dimension in RULE_DIMENSIONS:
            value = raw_rule.get(dimension)
            rule[dimension] = None if value in (None, "", "Any") else value

        if rule["merchant"] is not None and rule["merchant"] not in merchant_names:
            raise ValueError(f"Regla {index}: comercio inválido")
        if rule["country"] is not None and rule["country"] not in COUNTRIES:
            raise ValueError(f"Regla {index}: país inválido")
        if rule["method"] is not None and rule["method"] not in METHOD_IDS:
            raise ValueError(f"Regla {index}: método inválido")
        if rule["issuing_bank"] is not None and rule["issuing_bank"] not in bank_names:
            raise ValueError(f"Regla {index}: banco emisor inválido")
        combinations = list(_matching_combinations(rule))
        if not combinations:
            raise ValueError(f"Regla {index}: no coincide con una combinación válida")
        maximum_baseline = max(
            baseline_decline_probability(*combination, rates)
            for combination in combinations
        )
        if maximum_baseline + increase > 1 + 1e-12:
            raise ValueError(
                f"Regla {index}: el incremento supera 100% para una combinación "
                f"con baseline de {maximum_baseline * 100:.2f}%"
            )
        validated.append(rule)
    return validated


def baseline_decline_probability(
    provider, merchant, country, method, issuing_bank, provider_rates=None
):
    rates = provider_rates or DEFAULT_PROVIDER_DECLINE_RATES
    bank_offset = BANK_METHOD_DECLINE_OFFSETS.get(
        (issuing_bank, method), BANK_DECLINE_OFFSETS.get(issuing_bank, 0.0)
    )
    probability = (
        rates[provider]
        + MERCHANT_DECLINE_OFFSETS[merchant]
        + COUNTRY_DECLINE_OFFSETS[country]
        + METHOD_DECLINE_OFFSETS[method]
        + bank_offset
    )
    return min(1.0, max(0.0, probability))


def _rule_matches(rule, provider, merchant, country, method, issuing_bank):
    if rule["provider"] != provider:
        return False
    values = {
        "merchant": merchant,
        "country": country,
        "method": method,
        "issuing_bank": issuing_bank,
    }
    return all(
        rule[dimension] in (None, values[dimension]) for dimension in RULE_DIMENSIONS
    )


def resolve_decline_rule(
    provider,
    merchant,
    country,
    method,
    issuing_bank,
    rules,
):
    winner = None
    winner_key = None
    for index, rule in enumerate(rules):
        if not _rule_matches(rule, provider, merchant, country, method, issuing_bank):
            continue
        specificity = sum(rule[dimension] is not None for dimension in RULE_DIMENSIONS)
        key = (specificity, index)
        if winner_key is None or key > winner_key:
            winner = rule
            winner_key = key
    return winner


def resolve_decline_probability(
    provider,
    merchant,
    country,
    method,
    issuing_bank,
    provider_rates,
    rules,
):
    winner = resolve_decline_rule(
        provider, merchant, country, method, issuing_bank, rules
    )
    baseline_rate = baseline_decline_probability(
        provider, merchant, country, method, issuing_bank, provider_rates
    )
    if winner is not None:
        return min(1.0, baseline_rate + winner["decline_increase"])
    return baseline_rate


def normal_spend(rng, parameters, multiplier):
    while True:
        value = rng.gauss(
            parameters["mean"] * multiplier,
            parameters["std"] * multiplier,
        )
        if parameters["min"] <= value <= parameters["max"]:
            return round(value, 2)


def generate_timestamps(rng, n, start_date=START_DATE, end_date=END_DATE):
    first_day = datetime.combine(start_date.date(), datetime.min.time())
    days = [
        first_day + timedelta(days=offset)
        for offset in range((end_date.date() - start_date.date()).days + 1)
    ]
    buckets = []
    weights = []
    for day in days:
        for hour in range(24):
            hour_start = day.replace(hour=hour)
            hour_end = hour_start + timedelta(hours=1, seconds=-1)
            bucket_start = max(hour_start, start_date)
            bucket_end = min(hour_end, end_date)
            if bucket_start > bucket_end:
                continue
            available_seconds = int((bucket_end - bucket_start).total_seconds()) + 1
            buckets.append((bucket_start, bucket_end))
            weights.append(
                WEEKDAY_WEIGHTS[day.weekday()]
                * HOUR_WEIGHTS[hour]
                * available_seconds
                / 3600
            )

    timestamps = []
    for _ in range(n):
        bucket_start, bucket_end = rng.choices(buckets, weights=weights, k=1)[0]
        available_seconds = int((bucket_end - bucket_start).total_seconds())
        timestamps.append(
            bucket_start + timedelta(seconds=rng.randint(0, available_seconds))
        )
    return sorted(timestamps)


def generate_transactions(
    n=N_TRANSACTIONS,
    seed=SEED,
    provider_rates=None,
    decline_rules=None,
    start_date=START_DATE,
    end_date=END_DATE,
):
    rates = validate_provider_rates(provider_rates)
    rules = validate_decline_rules(decline_rules, rates)
    rng = random.Random(seed)
    if start_date > end_date:
        raise ValueError("La fecha inicial debe ser anterior a la fecha final")
    timestamps = generate_timestamps(rng, n, start_date, end_date)
    merchant_ids = list(MERCHANTS)

    for transaction_id, timestamp in enumerate(timestamps, start=1):
        merchant_id = rng.choices(
            merchant_ids,
            weights=[MERCHANTS[item]["weight"] for item in merchant_ids],
            k=1,
        )[0]
        country_weights = MERCHANTS[merchant_id]["country_weights"]
        country = rng.choices(
            list(country_weights), weights=list(country_weights.values()), k=1
        )[0]
        country_data = COUNTRIES[country]
        provider = rng.choice(list(country_data["providers"]))
        method = rng.choice(country_data["providers"][provider])
        merchant = MERCHANTS[merchant_id]["name"]
        uses_bank = method in BANK_LINKED_METHODS
        if uses_bank:
            bank_weights = country_data.get("issuing_bank_weights", {}).get(method)
            issuing_bank = (
                rng.choices(country_data["banks"], weights=bank_weights, k=1)[0]
                if bank_weights is not None
                else rng.choice(country_data["banks"])
            )
        else:
            issuing_bank = "N/A"
        baseline_rate = baseline_decline_probability(
            provider,
            merchant,
            country,
            method,
            issuing_bank,
            rates,
        )
        matching_rule = resolve_decline_rule(
            provider,
            merchant,
            country,
            method,
            issuing_bank,
            rules,
        )
        target_rate = baseline_rate
        if matching_rule is not None:
            target_rate = min(1.0, baseline_rate + matching_rule["decline_increase"])
        decline_roll = rng.random()
        if decline_roll < baseline_rate:
            is_declined = True
            decline_code = rng.choices(
                list(DECLINE_CODES), weights=list(DECLINE_CODES.values()), k=1
            )[0]
        elif matching_rule is not None and decline_roll < target_rate:
            is_declined = True
            decline_code = matching_rule["decline_code"]
        else:
            is_declined = False
            decline_code = 0
        receiving_bank = rng.choice(country_data["banks"])
        value = normal_spend(
            rng,
            country_data["usd_spend"],
            MERCHANTS[merchant_id]["spend_multiplier"],
        )
        local_value = round(value * country_data["local_per_usd"], 2)

        yield {
            "country": country,
            "provider_name": provider,
            "provider_id": PROVIDER_IDS[provider],
            "method_name": method,
            "method_id": METHOD_IDS[method],
            "merchant_name": merchant,
            "merchant_id": merchant_id,
            "issuing_bank": issuing_bank,
            "receiving_bank": receiving_bank,
            "transaction_id": transaction_id,
            "issued_timestamp": timestamp.isoformat(sep=" "),
            "is_declined": is_declined,
            "decline_code": decline_code,
            "currency": country_data["currency"],
            "value_transaction_currency": local_value,
            "value": value,
        }


def generate_csv(
    output_path=OUTPUT_PATH,
    n=N_TRANSACTIONS,
    seed=SEED,
    provider_rates=None,
    decline_rules=None,
    start_date=START_DATE,
    end_date=END_DATE,
):
    output_path = Path(output_path)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    rows_written = 0

    with temporary_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        for transaction in generate_transactions(
            n,
            seed,
            provider_rates,
            decline_rules,
            start_date,
            end_date,
        ):
            writer.writerow(transaction)
            rows_written += 1

    temporary_path.replace(output_path)
    return rows_written


def audit_csv(
    path=OUTPUT_PATH,
    expected_rows=N_TRANSACTIONS,
    start_date=None,
    end_date=None,
):
    path = Path(path)
    rows_read = 0
    sample = []
    previous_timestamp = None
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != COLUMNS:
            raise ValueError("Columnas inválidas")
        for row in reader:
            rows_read += 1
            if len(sample) < 3:
                sample.append(row)
            if int(row["transaction_id"]) != rows_read:
                raise ValueError("transaction_id inválido")
            timestamp = datetime.fromisoformat(row["issued_timestamp"])
            if previous_timestamp is not None and timestamp < previous_timestamp:
                raise ValueError("issued_timestamp no está ordenado")
            if start_date is not None and timestamp < start_date:
                raise ValueError("issued_timestamp anterior al período")
            if end_date is not None and timestamp > end_date:
                raise ValueError("issued_timestamp posterior al período")
            previous_timestamp = timestamp
            if int(row["provider_id"]) != PROVIDER_IDS[row["provider_name"]]:
                raise ValueError("provider_id inválido")
            if int(row["method_id"]) != METHOD_IDS[row["method_name"]]:
                raise ValueError("method_id inválido")
            merchant = MERCHANTS[int(row["merchant_id"])]
            if row["merchant_name"] != merchant["name"]:
                raise ValueError("merchant_id inválido")
            allowed_methods = COUNTRIES[row["country"]]["providers"][
                row["provider_name"]
            ]
            if row["method_name"] not in allowed_methods:
                raise ValueError("Combinación país/proveedor/método inválida")
            declined = row["is_declined"] == "True"
            if (int(row["decline_code"]) != 0) != declined:
                raise ValueError("decline_code inválido")
            if declined and int(row["decline_code"]) not in DECLINE_CODES:
                raise ValueError("decline_code inválido")

    if rows_read != expected_rows:
        raise ValueError(
            f"Se esperaban {expected_rows} filas y se encontraron {rows_read}"
        )
    return {"rows": rows_read, "sample": sample}


if __name__ == "__main__":
    total = generate_csv()
    audit_csv(expected_rows=total)
    print(f"{total:,} rows -> {OUTPUT_PATH}")
