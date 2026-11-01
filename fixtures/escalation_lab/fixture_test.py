from decimal import Decimal, ROUND_HALF_UP

from fixtures.escalation_lab.billing import round_money


def test_discount_rounding_boundary():
    expected = float(Decimal("2.675").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    assert round_money(2.675) == expected
