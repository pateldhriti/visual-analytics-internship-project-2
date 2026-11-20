r"""
Load test of the public website: simulated visitors load pages the way a
browser does (the HTML, then the JavaScript and CSS it references) over and
over for a fixed time, with a short pause between page views. Reports page
load times (all files of a page) and request times, as percentiles, and
writes a Markdown summary for the report.

    .venv\Scripts\python.exe deploy\load_test.py https://whva.cs.uwindsor.ca --users 10 --duration 60
    .venv\Scripts\python.exe deploy\load_test.py http://localhost:4173 --steps 1,5,10,25,50 --duration 30 --out docs\load_test_results.md

--steps runs one test per number of simultaneous visitors, one after the
other, to show where response times start to rise. The site is a static
React build served by nginx, so every page view fetches the same files; the
story pages are client-side routes of the same index.html.

Only test servers we run (our own whva site). Do not point this at apss or
any other shared university service without the admin's agreement.
"""

import argparse
import asyncio
import re
import time
from datetime import datetime
from urllib.parse import urljoin

import httpx

PAGES = ["/", "/stories/affordability", "/stories/rental-market", "/stories/supply",
         "/stories/comparison", "/stories/integrated-analysis"]


def pct(values: list[float], p: float) -> float:
    """The p-th percentile of values (linear interpolation); NaN when there are none."""
    if not values:
        return float("nan")
    values = sorted(values)
    k = (len(values) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


async def page_view(client: httpx.AsyncClient, base: str, path: str, stats: dict) -> None:
    """Load one page and the JavaScript and CSS it references, adding the timings and errors to stats."""
    start = time.perf_counter()
    try:
        r = await client.get(urljoin(base, path))
        stats["requests"].append(time.perf_counter() - start)
        if r.status_code >= 400:
            stats["errors"] += 1
            return
        assets = sorted(set(re.findall(r'(?:src|href)="(/assets/[^"]+)"', r.text)))
        results = await asyncio.gather(*(client.get(urljoin(base, a)) for a in assets), return_exceptions=True)
        for res in results:
            if isinstance(res, Exception) or res.status_code >= 400:
                stats["errors"] += 1
            stats["bytes"] += 0 if isinstance(res, Exception) else len(res.content)
        stats["bytes"] += len(r.content)
        stats["pages"].append(time.perf_counter() - start)
    except httpx.HTTPError:
        stats["errors"] += 1


async def visitor(base: str, until: float, stats: dict, think: float, i: int) -> None:
    # Each visitor has its own connection pool, like a separate browser.
    """One simulated visitor: page views across the story pages until the time is up, with a pause between them."""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, http2=False) as client:
        n = i
        while time.perf_counter() < until:
            await page_view(client, base, PAGES[n % len(PAGES)], stats)
            n += 1
            await asyncio.sleep(think)


async def run(base: str, users: int, duration: float, think: float) -> dict:
    """users visitors at once for duration seconds; returns the collected timings."""
    stats = {"requests": [], "pages": [], "errors": 0, "bytes": 0}
    start = time.perf_counter()
    await asyncio.gather(*(visitor(base, start + duration, stats, think, i) for i in range(users)))
    stats["elapsed"] = time.perf_counter() - start
    return stats


def summary(users: int, s: dict) -> dict:
    """Page-view counts, throughput, errors and percentiles in milliseconds for one test."""
    ms = 1000
    return {
        "users": users,
        "page_views": len(s["pages"]),
        "pages_per_s": len(s["pages"]) / s["elapsed"],
        "errors": s["errors"],
        "page_p50": pct(s["pages"], 50) * ms, "page_p95": pct(s["pages"], 95) * ms,
        "page_max": max(s["pages"], default=float("nan")) * ms,
        "html_p50": pct(s["requests"], 50) * ms, "html_p95": pct(s["requests"], 95) * ms,
        "mb": s["bytes"] / 1e6,
    }


def main() -> None:
    """Command-line entry point: one test, or one per --steps value, and an optional Markdown summary."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--users", type=int, default=10, help="simultaneous visitors (ignored with --steps)")
    ap.add_argument("--steps", help="comma-separated numbers of visitors, one test each, e.g. 1,5,10,25")
    ap.add_argument("--duration", type=float, default=60, help="seconds per test")
    ap.add_argument("--think", type=float, default=1.0, help="seconds a visitor waits between page views")
    ap.add_argument("--out", help="write a Markdown summary here")
    a = ap.parse_args()

    steps = [int(x) for x in a.steps.split(",")] if a.steps else [a.users]
    rows = []
    for users in steps:
        print(f"{users} visitor(s) for {a.duration:.0f} s ...", flush=True)
        rows.append(summary(users, asyncio.run(run(a.url, users, a.duration, a.think))))
        r = rows[-1]
        print(f"  {r['page_views']} page views ({r['pages_per_s']:.1f}/s), {r['errors']} errors; "
              f"page load p50 {r['page_p50']:.0f} ms, p95 {r['page_p95']:.0f} ms, max {r['page_max']:.0f} ms",
              flush=True)

    head = ("| Visitors at once | Page views | Page views/s | Errors | Page load p50 (ms) | p95 (ms) | max (ms) "
            "| HTML p50 (ms) | HTML p95 (ms) | Data (MB) |\n|---|---|---|---|---|---|---|---|---|---|\n")
    table = head + "".join(
        f"| {r['users']} | {r['page_views']} | {r['pages_per_s']:.1f} | {r['errors']} | {r['page_p50']:.0f} | "
        f"{r['page_p95']:.0f} | {r['page_max']:.0f} | {r['html_p50']:.0f} | {r['html_p95']:.0f} | {r['mb']:.1f} |\n"
        for r in rows)
    print("\n" + table)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(f"# Load test: {a.url}\n\n"
                     f"Run {datetime.now():%Y-%m-%d %H:%M} with `deploy/load_test.py`: each simulated visitor loads a page "
                     f"and its JavaScript and CSS, waits {a.think:g} s, and moves to the next story page, for "
                     f"{a.duration:.0f} s per row. A page load is the time to fetch all of a page's files; "
                     f"p50 is the median, p95 the time 95% of page loads beat.\n\n{table}")
        print(f"Wrote {a.out}")


if __name__ == "__main__":
    main()
