def round_money(value: float) -> float:
    """Deliberately flawed fixture: binary-float round is not HALF_UP money rounding."""
    return round(value, 2)
