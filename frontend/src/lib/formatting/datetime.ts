export const MAX_DAILY_TREND_BUCKETS = 366;
export const MAX_MONTHLY_TREND_BUCKETS = 120;

export type TrendInterval = "day" | "month";

const CIVIL_DATE_REGEX = /^(\d{4})-(\d{2})-(\d{2})$/;
const ISO_TZ_SUFFIX_REGEX = /(Z|[+-]\d{2}:\d{2})$/i;

export const COMMON_TIMEZONES = [
  "UTC",
  "Asia/Kolkata",
  "America/New_York",
  "Europe/London",
  "Asia/Singapore",
] as const;

export function isValidIanaTimeZone(timeZone: string): boolean {
  const trimmed = timeZone.trim();
  if (!trimmed) {
    return false;
  }
  try {
    new Intl.DateTimeFormat("en-US", { timeZone: trimmed });
    return true;
  } catch {
    return false;
  }
}

export function isValidCivilDate(dateStr: string): boolean {
  const match = CIVIL_DATE_REGEX.exec(dateStr.trim());
  if (!match) {
    return false;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (month < 1 || month > 12 || day < 1 || day > 31) {
    return false;
  }
  const check = new Date(Date.UTC(year, month - 1, day));
  return (
    check.getUTCFullYear() === year &&
    check.getUTCMonth() === month - 1 &&
    check.getUTCDate() === day
  );
}

export function isTimezoneAwareIso(iso: string): boolean {
  const trimmed = iso.trim();
  if (!ISO_TZ_SUFFIX_REGEX.test(trimmed)) {
    return false;
  }
  return !Number.isNaN(Date.parse(trimmed));
}

function getWallPartsInTimeZone(
  utcMs: number,
  timeZone: string
): {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
  second: number;
} {
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  });
  const parts = formatter.formatToParts(new Date(utcMs));
  const lookup = (type: Intl.DateTimeFormatPartTypes): number => {
    const found = parts.find((p) => p.type === type)?.value;
    if (found === undefined) {
      throw new Error(`Missing date part "${type}" for timezone "${timeZone}".`);
    }
    return Number.parseInt(found, 10);
  };

  const rawHour = lookup("hour");
  return {
    year: lookup("year"),
    month: lookup("month"),
    day: lookup("day"),
    hour: rawHour === 24 ? 0 : rawHour,
    minute: lookup("minute"),
    second: lookup("second"),
  };
}

function getTimeZoneOffsetMinutes(utcMs: number, timeZone: string): number {
  const wall = getWallPartsInTimeZone(utcMs, timeZone);
  const wallAsUtc = Date.UTC(
    wall.year,
    wall.month - 1,
    wall.day,
    wall.hour,
    wall.minute,
    wall.second,
    0
  );
  return Math.round((wallAsUtc - utcMs) / 60_000);
}

function formatOffsetSuffix(offsetMinutes: number): string {
  if (offsetMinutes === 0) {
    return "Z";
  }
  const sign = offsetMinutes >= 0 ? "+" : "-";
  const abs = Math.abs(offsetMinutes);
  const hours = String(Math.floor(abs / 60)).padStart(2, "0");
  const mins = String(abs % 60).padStart(2, "0");
  return `${sign}${hours}:${mins}`;
}

/**
 * Converts a civil calendar date (YYYY-MM-DD) to midnight 00:00:00 in the target
 * IANA timezone, returning a timezone-aware ISO-8601 timestamp string.
 * Handles DST transitions by refining the offset estimate around the resolved instant.
 */
export function zonedMidnightToIso(dateStr: string, timeZone: string): string {
  if (!isValidCivilDate(dateStr)) {
    throw new RangeError(`Invalid civil date: "${dateStr}"`);
  }
  if (!isValidIanaTimeZone(timeZone)) {
    throw new RangeError(`Invalid IANA timezone: "${timeZone}"`);
  }

  const [yearStr, monthStr, dayStr] = dateStr.trim().split("-");
  const year = Number(yearStr);
  const month = Number(monthStr);
  const day = Number(dayStr);

  if (timeZone.trim().toUpperCase() === "UTC") {
    return `${yearStr}-${monthStr}-${dayStr}T00:00:00Z`;
  }

  const guessUtcMs = Date.UTC(year, month - 1, day, 0, 0, 0, 0);
  const offset1 = getTimeZoneOffsetMinutes(guessUtcMs, timeZone);
  const pass1Ms = guessUtcMs - offset1 * 60_000;
  const offset2 = getTimeZoneOffsetMinutes(pass1Ms, timeZone);
  const finalMs = guessUtcMs - offset2 * 60_000;

  // Verify the resolved wall clock actually matches the target date (or stepped over DST spring-forward gap)
  const resolvedWall = getWallPartsInTimeZone(finalMs, timeZone);
  const hh = String(resolvedWall.hour).padStart(2, "0");
  const mm = String(resolvedWall.minute).padStart(2, "0");
  const ss = String(resolvedWall.second).padStart(2, "0");
  const yyyy = String(resolvedWall.year).padStart(4, "0");
  const mo = String(resolvedWall.month).padStart(2, "0");
  const dd = String(resolvedWall.day).padStart(2, "0");

  return `${yyyy}-${mo}-${dd}T${hh}:${mm}:${ss}${formatOffsetSuffix(offset2)}`;
}

export function addDaysToCivilDate(dateStr: string, days: number): string {
  if (!isValidCivilDate(dateStr)) {
    throw new RangeError(`Invalid civil date: "${dateStr}"`);
  }
  const [yearStr, monthStr, dayStr] = dateStr.trim().split("-");
  const date = new Date(Date.UTC(Number(yearStr), Number(monthStr) - 1, Number(dayStr) + days));
  const y = String(date.getUTCFullYear()).padStart(4, "0");
  const m = String(date.getUTCMonth() + 1).padStart(2, "0");
  const d = String(date.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export interface HalfOpenWindow {
  readonly fromTime: string;
  readonly toTime: string;
}

/**
 * Builds a half-open [from_time, to_time) ISO-8601 window from inclusive civil start/end dates
 * in the specified IANA timezone. An inclusive end date `2026-09-30` becomes exclusive
 * `2026-10-01T00:00:00<offset>`.
 */
export function buildHalfOpenDateRange(
  fromDate: string,
  inclusiveToDate: string,
  timeZone = "UTC"
): HalfOpenWindow {
  if (!isValidCivilDate(fromDate) || !isValidCivilDate(inclusiveToDate)) {
    throw new RangeError("Start and end dates must be valid YYYY-MM-DD dates.");
  }
  if (fromDate > inclusiveToDate) {
    throw new RangeError("Start date must be on or before end date.");
  }

  const exclusiveEndDate = addDaysToCivilDate(inclusiveToDate, 1);
  return {
    fromTime: zonedMidnightToIso(fromDate, timeZone),
    toTime: zonedMidnightToIso(exclusiveEndDate, timeZone),
  };
}

export function isoToCivilDateInTimeZone(isoString: string, timeZone = "UTC"): string {
  if (!isTimezoneAwareIso(isoString)) {
    throw new RangeError(`Timestamp must be timezone-aware ISO-8601: "${isoString}"`);
  }
  if (!isValidIanaTimeZone(timeZone)) {
    throw new RangeError(`Invalid IANA timezone: "${timeZone}"`);
  }
  const ms = Date.parse(isoString);
  const wall = getWallPartsInTimeZone(ms, timeZone);
  return `${String(wall.year).padStart(4, "0")}-${String(wall.month).padStart(2, "0")}-${String(wall.day).padStart(2, "0")}`;
}

export function validateHalfOpenIsoRange(fromTime: string, toTime: string): boolean {
  if (!isTimezoneAwareIso(fromTime) || !isTimezoneAwareIso(toTime)) {
    return false;
  }
  return Date.parse(fromTime) < Date.parse(toTime);
}

/**
 * Mirrors backend `count_calendar_buckets` in `src/finsignal/analytics/schemas.py`
 * to validate trend window sizes before dispatching `/analytics/trends`.
 */
export function countCalendarBuckets(
  fromTime: string,
  toTime: string,
  timeZone: string,
  interval: TrendInterval
): number {
  if (!validateHalfOpenIsoRange(fromTime, toTime) || !isValidIanaTimeZone(timeZone)) {
    return 0;
  }

  const fromMs = Date.parse(fromTime);
  const toMs = Date.parse(toTime);
  const startWall = getWallPartsInTimeZone(fromMs, timeZone);
  const endWall = getWallPartsInTimeZone(toMs, timeZone);

  if (interval === "day") {
    const startDateMs = Date.UTC(startWall.year, startWall.month - 1, startWall.day);
    const isExactMidnight = endWall.hour === 0 && endWall.minute === 0 && endWall.second === 0;
    const endDateMs = Date.UTC(
      endWall.year,
      endWall.month - 1,
      isExactMidnight ? endWall.day - 1 : endWall.day
    );
    return Math.max(0, Math.round((endDateMs - startDateMs) / 86_400_000) + 1);
  }

  // interval === "month"
  const isMonthBoundary =
    endWall.day === 1 && endWall.hour === 0 && endWall.minute === 0 && endWall.second === 0;
  let lastYear = endWall.year;
  let lastMonth = endWall.month;
  if (isMonthBoundary) {
    const priorWall = getWallPartsInTimeZone(toMs - 1, timeZone);
    lastYear = priorWall.year;
    lastMonth = priorWall.month;
  }

  return Math.max(0, (lastYear - startWall.year) * 12 + (lastMonth - startWall.month) + 1);
}

export function getTrendBucketLimit(interval: TrendInterval): number {
  return interval === "day" ? MAX_DAILY_TREND_BUCKETS : MAX_MONTHLY_TREND_BUCKETS;
}

export function formatTimestamp(
  isoString: string | null | undefined,
  timeZone = "UTC",
  options: { includeSeconds?: boolean | undefined } = {}
): string {
  if (!isoString || isoString.trim() === "") {
    return "—";
  }
  const ms = Date.parse(isoString);
  if (Number.isNaN(ms)) {
    return "Invalid timestamp";
  }
  const safeTz = isValidIanaTimeZone(timeZone) ? timeZone.trim() : "UTC";
  const wall = getWallPartsInTimeZone(ms, safeTz);
  const datePart = `${String(wall.year).padStart(4, "0")}-${String(wall.month).padStart(2, "0")}-${String(wall.day).padStart(2, "0")}`;
  const timePart =
    options.includeSeconds === false
      ? `${String(wall.hour).padStart(2, "0")}:${String(wall.minute).padStart(2, "0")}`
      : `${String(wall.hour).padStart(2, "0")}:${String(wall.minute).padStart(2, "0")}:${String(wall.second).padStart(2, "0")}`;

  return `${datePart} ${timePart} ${safeTz}`;
}

export function formatShortDate(isoString: string, timeZone = "UTC"): string {
  const ms = Date.parse(isoString);
  if (Number.isNaN(ms)) {
    return isoString;
  }
  const safeTz = isValidIanaTimeZone(timeZone) ? timeZone.trim() : "UTC";
  const wall = getWallPartsInTimeZone(ms, safeTz);
  return `${String(wall.year).padStart(4, "0")}-${String(wall.month).padStart(2, "0")}-${String(wall.day).padStart(2, "0")}`;
}

export function getDefaultCivilWindow(referenceNow = new Date()): {
  fromDate: string;
  toDate: string;
} {
  const endUtc = new Date(
    Date.UTC(referenceNow.getUTCFullYear(), referenceNow.getUTCMonth(), referenceNow.getUTCDate())
  );
  const startUtc = new Date(endUtc.getTime() - 29 * 86_400_000);
  const fmt = (d: Date) =>
    `${String(d.getUTCFullYear()).padStart(4, "0")}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;

  return {
    fromDate: fmt(startUtc),
    toDate: fmt(endUtc),
  };
}
