const DECIMAL_STRING_REGEX = /^-?\d+(?:\.\d+)?$/;
const CURRENCY_CODE_REGEX = /^[A-Z]{3}$/;

export function isValidDecimalString(value: unknown): value is string {
  return typeof value === "string" && DECIMAL_STRING_REGEX.test(value.trim());
}

export function isValidCurrencyCode(value: unknown): value is string {
  return typeof value === "string" && CURRENCY_CODE_REGEX.test(value.trim());
}

/**
 * Formats a backend decimal string with thousand separators while preserving
 * exact integer digits, negative sign, and trailing fractional zeros without
 * converting to JavaScript IEEE-754 floating-point numbers.
 */
export function formatDecimalString(value: string): string {
  const trimmed = value.trim();
  if (!DECIMAL_STRING_REGEX.test(trimmed)) {
    throw new RangeError(`Invalid monetary decimal string: "${value}"`);
  }

  const isNegative = trimmed.startsWith("-");
  const unsigned = isNegative ? trimmed.slice(1) : trimmed;
  const dotIndex = unsigned.indexOf(".");
  const rawInt = dotIndex === -1 ? unsigned : unsigned.slice(0, dotIndex);
  const rawFrac = dotIndex === -1 ? "" : unsigned.slice(dotIndex + 1);

  // Strip redundant leading zeros on integer part only while keeping at least "0"
  const normalizedInt = rawInt.replace(/^0+(?=\d)/, "");
  const groupedInt = normalizedInt.replace(/\B(?=(\d{3})+(?!\d))/g, ",");

  const isZero = /^0+$/.test(normalizedInt) && (rawFrac === "" || /^0+$/.test(rawFrac));
  const sign = isNegative && !isZero ? "-" : "";

  return rawFrac.length > 0 ? `${sign}${groupedInt}.${rawFrac}` : `${sign}${groupedInt}`;
}

export interface FormattedMoneyParts {
  readonly amount: string;
  readonly currency: string | null;
  readonly isNegative: boolean;
}

export function formatMoneyParts(
  amount: string | null | undefined,
  currency?: string | null
): FormattedMoneyParts | null {
  if (amount === null || amount === undefined || amount.trim() === "") {
    return null;
  }

  const formatted = formatDecimalString(amount);
  const normalizedCurrency =
    typeof currency === "string" && currency.trim() !== "" ? currency.trim().toUpperCase() : null;

  if (normalizedCurrency !== null && !CURRENCY_CODE_REGEX.test(normalizedCurrency)) {
    throw new RangeError(`Invalid ISO-4217 currency code: "${currency}"`);
  }

  return {
    amount: formatted,
    currency: normalizedCurrency,
    isNegative: formatted.startsWith("-"),
  };
}

export function formatMoney(amount: string | null | undefined, currency?: string | null): string {
  const parts = formatMoneyParts(amount, currency);
  if (parts === null) {
    return "—";
  }
  return parts.currency !== null ? `${parts.amount} ${parts.currency}` : parts.amount;
}

export function formatPercentage(value: string | null | undefined): string {
  if (value === null || value === undefined || value.trim() === "") {
    return "—";
  }
  return `${formatDecimalString(value)}%`;
}

/**
 * Converts a decimal string to a finite JavaScript number strictly for
 * visual chart coordinate plotting (e.g., Apache ECharts axes/bars).
 * Never use the returned number for authoritative financial calculations or text display.
 */
export function toChartPlotNumber(value: string): number {
  const trimmed = value.trim();
  if (!DECIMAL_STRING_REGEX.test(trimmed)) {
    throw new RangeError(`Invalid numeric plot string: "${value}"`);
  }
  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed)) {
    throw new RangeError(`Non-finite numeric plot value: "${value}"`);
  }
  return parsed;
}

/**
 * Compares two non-negative or signed decimal strings without float coercion.
 * Returns -1 if a < b, 0 if a == b, 1 if a > b.
 */
export function compareDecimalStrings(a: string, b: string): -1 | 0 | 1 {
  const normA = a.trim();
  const normB = b.trim();
  if (!DECIMAL_STRING_REGEX.test(normA) || !DECIMAL_STRING_REGEX.test(normB)) {
    throw new RangeError(`Cannot compare invalid decimal strings: "${a}", "${b}"`);
  }

  const negA = normA.startsWith("-");
  const negB = normB.startsWith("-");
  const splitParts = (val: string): [string, string] => {
    const unsigned = val.startsWith("-") ? val.slice(1) : val;
    const dot = unsigned.indexOf(".");
    const intRaw = dot === -1 ? unsigned : unsigned.slice(0, dot);
    const fracRaw = dot === -1 ? "" : unsigned.slice(dot + 1);
    const intTrimmed = intRaw.replace(/^0+(?=\d)/, "");
    const fracTrimmed = fracRaw.replace(/0+$/, "");
    return [intTrimmed, fracTrimmed];
  };

  const [intA, fracA] = splitParts(normA);
  const [intB, fracB] = splitParts(normB);
  const isZeroA = intA === "0" && fracA === "";
  const isZeroB = intB === "0" && fracB === "";

  if (isZeroA && isZeroB) {
    return 0;
  }
  const effNegA = negA && !isZeroA;
  const effNegB = negB && !isZeroB;
  if (effNegA !== effNegB) {
    return effNegA ? -1 : 1;
  }

  const maxFrac = Math.max(fracA.length, fracB.length);
  const paddedFracA = fracA.padEnd(maxFrac, "0");
  const paddedFracB = fracB.padEnd(maxFrac, "0");

  let cmp: -1 | 0 | 1 = 0;
  if (intA.length !== intB.length) {
    cmp = intA.length < intB.length ? -1 : 1;
  } else if (intA !== intB) {
    cmp = intA < intB ? -1 : 1;
  } else if (paddedFracA !== paddedFracB) {
    cmp = paddedFracA < paddedFracB ? -1 : 1;
  }

  if (cmp === 0) {
    return 0;
  }
  return effNegA ? (cmp === 1 ? -1 : 1) : cmp;
}
