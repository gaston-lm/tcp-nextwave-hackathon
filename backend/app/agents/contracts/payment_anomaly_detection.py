"""Output contract for the payment anomaly detection stage."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentAnomalyDetectionResult:
    """The raw model conclusion and bounded tool-loop usage for one detection run."""

    result: str
    steps_used: int
