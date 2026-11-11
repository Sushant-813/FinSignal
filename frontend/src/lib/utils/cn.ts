/**
 * Simple conditional class-name joiner.
 *
 * Limitation: This helper concatenates truthy class strings in order and does NOT
 * resolve or deduplicate conflicting Tailwind CSS utilities (e.g. passing "px-8"
 * alongside "px-4" emits both classes, where CSS stylesheet order wins).
 * Keep component variant APIs explicit so callers do not need conflicting overrides.
 */
export function cn(...inputs: Array<string | false | null | undefined>): string {
  return inputs.filter((value): value is string => Boolean(value && value.trim())).join(" ");
}
