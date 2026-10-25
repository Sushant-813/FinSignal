"""Constants and configuration thresholds for FinSignal Phase 6 Feature Engineering."""

from typing import Final

# Feature Contract Version
FEATURE_VERSION: Final[str] = "v1.0"

# Provisional Minimum Baseline Observations
# Pragmatic initial policy enabling sample variance calculation (N - 1 = 2 degrees of freedom)
# without indefinitely locking new accounts into cold-start status.
MIN_BASELINE_OBSERVATIONS: Final[int] = 3

# Velocity Window Durations (in seconds)
VELOCITY_WINDOW_5M_SECONDS: Final[int] = 300
VELOCITY_WINDOW_1H_SECONDS: Final[int] = 3600
VELOCITY_WINDOW_24H_SECONDS: Final[int] = 86400

# Category Spending Window Duration (in seconds)
CATEGORY_WINDOW_30D_SECONDS: Final[int] = 30 * 86400

# Unusual Hour Set (UTC hours calibrated to nocturnal fraud pattern F004: 01:00 to 05:59 UTC)
UNUSUAL_HOURS: Final[frozenset[int]] = frozenset({1, 2, 3, 4, 5})

# Weekend Days (ISO weekday: 5=Saturday, 6=Sunday; Monday=0)
WEEKEND_DAYS: Final[frozenset[int]] = frozenset({5, 6})
