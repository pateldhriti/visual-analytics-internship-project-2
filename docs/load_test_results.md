# Load test: https://whva.cs.uwindsor.ca

Run 2026-11-20 09:11 with `deploy/load_test.py`: each simulated visitor loads a page and its JavaScript and CSS, waits 1 s, and moves to the next story page, for 30 s per row. A page load is the time to fetch all of a page's files; p50 is the median, p95 the time 95% of page loads beat.

| Visitors at once | Page views | Page views/s | Errors | Page load p50 (ms) | p95 (ms) | max (ms) | HTML p50 (ms) | HTML p95 (ms) | Data (MB, before compression) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 26 | 0.8 | 0 | 55 | 285 | 729 | 9 | 72 | 12.9 |
| 5 | 124 | 4.0 | 0 | 65 | 205 | 3487 | 14 | 87 | 61.6 |
| 10 | 190 | 6.2 | 0 | 73 | 407 | 8841 | 12 | 194 | 94.4 |
| 25 | 305 | 9.8 | 0 | 84 | 6440 | 16347 | 17 | 6169 | 151.5 |
| 50 | 38 | 0.9 | 0 | 25893 | 39757 | 41061 | 24894 | 38489 | 18.9 |

## Reading the results

*Run 20 November 2026 from one laptop over the university VPN (GlobalProtect), against the public site on whva (nginx, HTTPS, gzip). The data column counts the files before compression; nginx compresses them in transfer (the 430 KB script arrives as 164 KB).*

- **No errors at any load.** Every page and file was served.
- **Up to 10 visitors at once** (about 6 page views a second), the median page, with all its files, loaded in **under 0.1 s** and 95% of page loads took under 0.5 s. That is far above the site's expected traffic, and well inside goal G4 (pages in under 3 s).
- **At 25 visitors at once** (about 10 page views a second, or 35,000 an hour), the median stayed under 0.1 s, but 5% of page loads took over 6 s.
- **At 50 visitors at once,** response times collapsed (median 26 s): the limit was reached.

The test cannot say whether that limit is whva itself or the single laptop's connections through the VPN: one download over the same VPN ran at about 6 MB/s, more than the test used at 25 visitors, so bandwidth alone does not explain it. To separate the two, repeat the 25 and 50 runs from a computer on the campus network, or from two machines at once, and watch whva's CPU (`top`) during the run.
