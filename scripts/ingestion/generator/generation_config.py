"""Editable parameters for the synthetic transaction generator.

Probabilities and probability offsets use decimal values: 0.17 means 17%, and
0.01 means one percentage point. Values named ``weight`` are relative sampling
weights and do not need to add up to 100.
"""

from datetime import datetime

# Default generation and output settings.
SEED = 42
N_TRANSACTIONS = 10_000
START_DATE = datetime(2026, 8, 22, 0, 0, 0)
END_DATE = datetime(2026, 8, 29, 23, 59, 59)
OUTPUT_FILENAME = "transactions.csv"
MAX_GENERATION_ROWS = 1_000_000

# Reproducible one-million-row baseline settings.
BASELINE_FILENAME = "baseline.csv"
BASELINE_ROWS = 1_000_000
BASELINE_SEED = 42
BASELINE_START_DATE = START_DATE
BASELINE_END_DATE = END_DATE

COLUMNS = [
    "country",
    "provider_name",
    "provider_id",
    "method_name",
    "method_id",
    "merchant_name",
    "merchant_id",
    "issuing_bank",
    "receiving_bank",
    "transaction_id",
    "issued_timestamp",
    "is_declined",
    "decline_code",
    "currency",
    "value_transaction_currency",
    "value",
]

# Merchant sampling, geographic coverage, and spending multipliers.
MERCHANTS = {
    1: {
        "name": "Walmart",
        "weight": 60,
        "spend_multiplier": 0.90,
        "country_weights": {"Mexico": 70, "Chile": 30},
    },
    2: {
        "name": "Cencosud",
        "weight": 40,
        "spend_multiplier": 1.15,
        "country_weights": {"Chile": 40, "Argentina": 35, "Brasil": 25},
    },
}

# Country currencies, USD spending distributions, providers, methods, and banks.
COUNTRIES = {
    "Chile": {
        "currency": "CLP",
        "local_per_usd": 950.0,
        "usd_spend": {"mean": 60, "std": 30, "min": 4, "max": 250},
        "providers": {
            "MercadoPago": ["credit_card", "debit_card", "wallet"],
            "dLocal": ["credit_card", "debit_card"],
            "PayU": ["credit_card", "debit_card"],
        },
        "banks": [
            "Banco de Chile",
            "Santander Chile",
            "BancoEstado",
            "BCI",
            "Scotiabank Chile",
        ],
    },
    "Argentina": {
        "currency": "ARS",
        "local_per_usd": 1300.0,
        "usd_spend": {"mean": 25, "std": 12, "min": 2, "max": 100},
        "providers": {
            "MercadoPago": [
                "credit_card",
                "debit_card",
                "wallet",
                "cash_in_store",
            ],
            "dLocal": ["credit_card", "debit_card", "cash_in_store"],
            "PayU": ["credit_card", "debit_card", "cash_in_store"],
        },
        "banks": [
            "Banco Nación",
            "Banco Galicia",
            "Santander Argentina",
            "BBVA Argentina",
            "Banco Macro",
        ],
    },
    "Mexico": {
        "currency": "MXN",
        "local_per_usd": 19.0,
        "usd_spend": {"mean": 70, "std": 35, "min": 5, "max": 300},
        "providers": {
            "MercadoPago": [
                "credit_card",
                "debit_card",
                "wallet",
                "bank_transfer",
                "cash_in_store",
            ],
            "dLocal": [
                "credit_card",
                "debit_card",
                "bank_transfer",
                "cash_in_store",
            ],
            "PayU": [
                "credit_card",
                "debit_card",
                "bank_transfer",
                "cash_in_store",
            ],
            "Stripe": [
                "credit_card",
                "debit_card",
                "bank_transfer",
                "cash_in_store",
            ],
        },
        "banks": [
            "BBVA México",
            "Banorte",
            "Santander México",
            "Citibanamex",
            "HSBC México",
        ],
        "issuing_bank_weights": {
            "credit_card": [88_730_465, 12_250_892, 9_198_210, 28_498_552, 5_289_768],
            "debit_card": [215_321_557, 26_467_845, 30_742_509, 44_399_197, 12_332_695],
        },
    },
    "Brasil": {
        "currency": "BRL",
        "local_per_usd": 5.5,
        "usd_spend": {"mean": 45, "std": 22, "min": 3, "max": 180},
        "providers": {
            "MercadoPago": [
                "credit_card",
                "debit_card",
                "wallet",
                "pix",
                "boleto",
            ],
            "dLocal": ["credit_card", "debit_card", "pix", "boleto"],
            "PayU": ["credit_card", "debit_card", "boleto"],
            "Adyen": ["credit_card", "debit_card", "pix", "boleto"],
            "Stripe": ["credit_card", "debit_card", "pix", "boleto"],
        },
        "banks": [
            "Itaú Unibanco",
            "Bradesco",
            "Banco do Brasil",
            "Caixa Econômica Federal",
            "Nubank",
        ],
    },
}

PROVIDER_IDS = {
    "MercadoPago": 1,
    "dLocal": 2,
    "PayU": 3,
    "Stripe": 4,
    "Adyen": 5,
}

METHOD_IDS = {
    "credit_card": 1,
    "debit_card": 2,
    "wallet": 3,
    "bank_transfer": 4,
    "cash_in_store": 5,
    "pix": 6,
    "boleto": 7,
}

# Synthetic neutral provider baselines. These are not published provider KPIs.
DEFAULT_PROVIDER_DECLINE_RATES = {
    "MercadoPago": 0.17,
    "dLocal": 0.15,
    "PayU": 0.18,
    "Stripe": 0.18,
    "Adyen": 0.16,
}

# Additive decline-rate offsets for each generated dimension.
MERCHANT_DECLINE_OFFSETS = {"Walmart": -0.002, "Cencosud": 0.002}
COUNTRY_DECLINE_OFFSETS = {
    "Chile": -0.02,
    "Argentina": 0.04,
    "Mexico": 0.12,
    "Brasil": 0.05,
}
METHOD_DECLINE_OFFSETS = {
    "credit_card": -0.03,
    "debit_card": 0.01,
    "wallet": -0.08,
    "bank_transfer": -0.07,
    "cash_in_store": 0.03,
    "pix": -0.13,
    "boleto": 0.05,
}
BANK_DECLINE_OFFSETS = {
    "Banco de Chile": -0.01,
    "Santander Chile": -0.005,
    "BancoEstado": 0.01,
    "BCI": 0.0,
    "Scotiabank Chile": 0.005,
    "Banco Nación": 0.01,
    "Banco Galicia": -0.005,
    "Santander Argentina": 0.0,
    "BBVA Argentina": -0.01,
    "Banco Macro": 0.005,
    "BBVA México": -0.01,
    "Banorte": 0.01,
    "Santander México": 0.005,
    "Citibanamex": -0.005,
    "HSBC México": 0.0,
    "Itaú Unibanco": -0.01,
    "Bradesco": 0.0,
    "Banco do Brasil": 0.005,
    "Caixa Econômica Federal": 0.01,
    "Nubank": -0.005,
}

# Mexico card adjustments use CONDUSEF/Banco de México Q4-2025 issuer data.
# These replace, rather than add to, the general bank offset for that bank/method.
BANK_METHOD_DECLINE_OFFSETS = {
    ("BBVA México", "credit_card"): -0.0722,
    ("Banorte", "credit_card"): 0.2808,
    ("Santander México", "credit_card"): 0.1015,
    ("Citibanamex", "credit_card"): -0.0600,
    ("HSBC México", "credit_card"): 0.1663,
    ("BBVA México", "debit_card"): -0.0369,
    ("Banorte", "debit_card"): 0.0648,
    ("Santander México", "debit_card"): 0.0338,
    ("Citibanamex", "debit_card"): -0.0874,
    ("HSBC México", "debit_card"): 0.0984,
}

BANK_LINKED_METHODS = {"credit_card", "debit_card", "bank_transfer", "pix"}

# ISO-8583 decline-code mix used for natural baseline declines.
DECLINE_CODE_DETAILS = {
    5: {"label": "Do not honor", "weight": 15},
    14: {"label": "Invalid card/account number", "weight": 3},
    51: {"label": "Insufficient funds", "weight": 40},
    54: {"label": "Expired card", "weight": 5},
    57: {"label": "Transaction not permitted", "weight": 7},
    59: {"label": "Suspected fraud", "weight": 15},
    61: {"label": "Exceeds approval amount limit", "weight": 10},
    91: {"label": "Issuer or switch unavailable", "weight": 3},
    96: {"label": "System malfunction", "weight": 2},
}
DECLINE_CODES = {
    code: details["weight"] for code, details in DECLINE_CODE_DETAILS.items()
}

# Relative transaction-volume weights by weekday (Monday=0) and hour (0-23).
WEEKDAY_WEIGHTS = {
    0: 0.85,
    1: 0.90,
    2: 0.95,
    3: 1.00,
    4: 1.20,
    5: 1.35,
    6: 1.10,
}
HOUR_WEIGHTS = [
    0.25,
    0.15,
    0.10,
    0.08,
    0.07,
    0.08,
    0.15,
    0.30,
    0.55,
    0.80,
    1.00,
    1.15,
    1.25,
    1.20,
    1.05,
    1.00,
    1.10,
    1.25,
    1.45,
    1.60,
    1.70,
    1.45,
    0.90,
    0.50,
]

# Optional fields that can narrow a provider incident rule.
RULE_DIMENSIONS = ("merchant", "country", "method", "issuing_bank")
