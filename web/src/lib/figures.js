// Every figure the story pages and home page quote, exported from the
// warehouse views by etl/export_site_highlights.py (etl/site_figures.py),
// so a data refresh updates the site's numbers. Format with the helpers
// below rather than typing numbers into page text.
import figures from "../data/figures.json";

export const F = figures;

const formatters = {};
const fmt = (digits) =>
  (formatters[digits] ??= new Intl.NumberFormat("en-CA", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }));

/** 28745 -> "28,745"; num(13.02, 1) -> "13.0" */
export const num = (n, digits = 0) => fmt(digits).format(n);
/** 1451 -> "$1,451"; money(199.5, 2) -> "$199.50" */
export const money = (n, digits = 0) => `$${num(n, digits)}`;
/** 34.8 -> "34.8%"; pct(55, 0) -> "55%" */
export const pct = (n, digits = 1) => `${num(n, digits)}%`;
/** 2 -> "second": for "the second-lowest of the five cities" */
export const nth = (n) => ["", "", "second", "third", "fourth", "fifth"][n] ?? `${n}th`;
/** 2 -> "2nd": for short labels such as "2nd-tightest" */
export const ordinal = (n) =>
  `${n}${["th", "st", "nd", "rd"][n % 100 > 10 && n % 100 < 14 ? 0 : n % 10] ?? "th"}`;
/** ["A"] -> "A"; ["A", "B"] -> "A and B" */
export const list = (items) =>
  items.length < 2 ? (items[0] ?? "") : `${items.slice(0, -1).join(", ")} and ${items.at(-1)}`;
