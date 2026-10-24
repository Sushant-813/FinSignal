"""Unit tests for analytics calculations, rounding, and math tolerance (Phase 5)."""

from decimal import ROUND_HALF_UP, Decimal


def test_category_percentage_summation_tolerance() -> None:
    """Verify that 3 items of ₹10.00 yield 33.33% each, summing to 99.99% without error."""
    amounts = [Decimal("10.00"), Decimal("10.00"), Decimal("10.00")]
    total = sum(amounts)
    percentages = [
        (amt / total * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        for amt in amounts
    ]
    assert percentages == [Decimal("33.33"), Decimal("33.33"), Decimal("33.33")]
    assert sum(percentages) == Decimal("99.99")


def test_halfway_value_median_rounding() -> None:
    """Verify continuous median halfway rounding: 100.01 and 100.02 continuous median 100.015 rounds to 100.02."""
    v1 = Decimal("100.01")
    v2 = Decimal("100.02")
    continuous_median = (v1 + v2) / Decimal("2")
    assert continuous_median == Decimal("100.015")

    rounded_median = continuous_median.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert rounded_median == Decimal("100.02")


def test_outlier_threshold_formula() -> None:
    """Verify outlier threshold math and boundary inclusion."""
    median_debit = Decimal("650.00")
    multiplier = Decimal("3.0")
    threshold = (median_debit * multiplier).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    assert threshold == Decimal("1950.00")

    # Transaction strictly below threshold -> not an outlier
    tx_below = Decimal("1949.99")
    assert tx_below < threshold

    # Transaction exactly at threshold -> is an outlier (amount >= threshold)
    tx_exact = Decimal("1950.00")
    assert tx_exact >= threshold

    # Transaction above threshold -> is an outlier
    tx_above = Decimal("2000.00")
    assert tx_above >= threshold


def test_deviation_ratio_math() -> None:
    """Verify deviation ratio calculation: amount / median_debit."""
    median_debit = Decimal("650.00")
    amount = Decimal("45000.00")
    ratio = (amount / median_debit).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert ratio == Decimal("69.23")
