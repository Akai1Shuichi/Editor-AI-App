from decimal import Decimal, ROUND_CEILING
from typing import Optional


def _credit_rate(provider: str, model: str) -> Decimal:
    provider_key = provider.strip().lower()
    model_key = model.strip().lower()

    if provider_key == "elevenlabs":
        return Decimal("0.5") if any(
            keyword in model_key for keyword in ("turbo", "flash")
        ) else Decimal("1")
    if provider_key == "minimax":
        return Decimal("0.6") if "turbo" in model_key else Decimal("1")
    if provider_key == "capcut":
        return Decimal("0.01")
    return Decimal("1")


def estimate_tts_credits(text: str, provider: str, model: str) -> int:
    """Return the estimated credits needed to synthesize ``text``."""
    exact_cost = Decimal(len(text)) * _credit_rate(provider, model)
    return int(exact_cost.to_integral_value(rounding=ROUND_CEILING))


def format_credit_summary(
    text: str,
    provider: str,
    model: str,
    balance: Optional[int],
) -> str:
    """Format the live TTS character, estimate, and balance summary."""
    estimated = estimate_tts_credits(text, provider, model)
    balance_text = "--" if balance is None else f"{balance:,}"
    return f"{len(text):,} chars · {estimated:,}/{balance_text} credits"
