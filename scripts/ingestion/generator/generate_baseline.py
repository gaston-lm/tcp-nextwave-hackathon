from pathlib import Path

from dataset_generator import audit_csv, generate_csv
from generation_config import (
    BASELINE_END_DATE,
    BASELINE_FILENAME,
    BASELINE_ROWS,
    BASELINE_SEED,
    BASELINE_START_DATE,
)

BASE_DIR = Path(__file__).resolve().parent
BASELINE_OUTPUT = BASE_DIR / BASELINE_FILENAME


def generate_baseline():
    rows = generate_csv(
        output_path=BASELINE_OUTPUT,
        n=BASELINE_ROWS,
        seed=BASELINE_SEED,
        start_date=BASELINE_START_DATE,
        end_date=BASELINE_END_DATE,
    )
    audit_csv(
        BASELINE_OUTPUT,
        expected_rows=BASELINE_ROWS,
        start_date=BASELINE_START_DATE,
        end_date=BASELINE_END_DATE,
    )
    return rows


if __name__ == "__main__":
    total = generate_baseline()
    print(f"{total:,} baseline rows -> {BASELINE_OUTPUT}")
