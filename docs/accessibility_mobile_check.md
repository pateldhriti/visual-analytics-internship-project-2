# Accessibility and Mobile Check

**Date:** 2026-11-06
**Scope:** the React site's eight pages (Home, Stories 1–5, Methodology, Sources) and the
embedded Superset dashboards (four at first; all five since Story 5 was embedded).
**Standard:** WCAG 2.1 AA.

## How it was checked

| Check | Tool or method |
|---|---|
| Automated | axe-core 4.10.2 (WCAG 2.0/2.1 A and AA rules) on every page, run in Chrome through Playwright |
| Contrast | axe's colour-contrast rule plus a manual look at text on coloured surfaces (buttons, KPI tiles, badges) |
| Keyboard | Tab through every page; check the focus outline is visible at each stop and the order follows the page; operate the phone menu, embed buttons and skip link with the keyboard only |
| Alt text | every `<img>` checked for an `alt` attribute; decorative icons checked for `aria-hidden` |
| Phone width | each page at 320, 375 and 414 px wide (touch, mobile viewport): page width, the embedded dashboard, and screenshots |

## Results

### Automated (axe)

| Page | Before | After |
|---|---|---|
| Home | 1 serious: "Explore the Data" button contrast 4.47:1 (needs 4.5:1) | none |
| Story 1–5, Methodology, Sources | none | none |

### Manual pass

| Item | Before | After |
|---|---|---|
| Focus outline visible at every tab stop | Yes | Yes |
| Skip link to the main content | Missing: keyboard users tabbed through 9 sidebar links on every page | Added; it is the first tab stop, appears at the top-left when focused, and moves focus to `<main>` |
| Phone menu | Opened with Enter; Escape did nothing | Escape closes it and returns focus to the menu button |
| Embedded dashboards | Iframes reachable by keyboard | Same; each iframe has a descriptive `title` ("Story 3: Is Windsor building enough housing? (Superset dashboard)") |
| Loading and error messages | None (blank box while loading) | Spinner announced as `role="status"`; failure message as `role="alert"` with a **Try again** button and a link to open the dashboard |
| Images without alt text | None: the Home banner and the Story 5 chart images had descriptive `alt` text (the images were later replaced by the embedded dashboard) | Same; sidebar icons are inline SVG with `aria-hidden="true"` |
| Reduced motion | The KPI ticker, smooth scrolling and Home's animations respected `prefers-reduced-motion` | The new loading spinner stops too |

### Phone width

| Item | Before | After |
|---|---|---|
| Page wider than the screen | Story 4 by 4 px (rungs that had not yet slid in sat 28 px to the right) | No page scrolls sideways at 320, 375 or 414 px |
| Embedded dashboards | Squeezed to 327 px; the open filter bar took most of the width and charts were unreadable | Dashboard keeps a 760 px layout in a frame that scrolls sideways, the filter bar starts collapsed, and a note offers "open it full screen" |

Superset 3.1's dashboard grid does not reflow for narrow screens, so a sideways-scrolling frame is
the most usable option without changing Superset itself (decision D31).

## Changes made

| Fix | File |
|---|---|
| Hero button background `#c65335` → `#b84c30` (white text now 5.1:1) | `web/src/index.css` |
| Skip link and focusable `<main id="main-content">` | `web/src/App.jsx`, `web/src/index.css` |
| Escape closes the phone menu | `web/src/components/Sidebar.jsx` |
| Loading and error states for every embed | `web/src/components/EmbedStatus.jsx`, `SupersetGuestEmbed.jsx`, `SupersetEmbed.jsx` |
| Collapsed filter bar and sideways-scrolling frame on phones | `web/src/lib/useNarrowScreen.js`, the two embed components, `web/src/index.css` |
| Story 4 slide-in offset clipped | `web/src/index.css` |

## Follow-up check (2026-11-06)

The first check ran axe on each page as it loaded. Several sections only fade in when they are scrolled into view, so the follow-up scrolled through every page first, at 1,440 px and at 375 px. That found four more problems, all now fixed. Every page now has 0 axe violations at both widths.

| Problem | Where | Fix |
|---|---|---|
| Text in the theme's accent colour (#c65335) at 4.23–4.47:1 | Home: the selected metric button and the "full methodology page" link | Accent darkened to #b84c30 (5.1:1 on white, 4.8:1 on the page background), so every use is fixed |
| White numbers on coloured tiles, 3.6–4.2:1 | Story 3's definition cards ("01" to "04") | White badge with dark text; the tile colour is now its border |
| Sideways-scrolling dashboard frame not reachable by keyboard | Every embedded dashboard, on phones | On phones the frame can be focused (labelled "…, scrolls sideways") and scrolled with the arrow keys |
| New "How this connects" link at 4.47:1 | Stories 1–4 | Link text in dark ink, with the accent as a thick underline |

## Re-check (2026-11-13)

Since the first check, the site gained its own charts: "The story in four charts" on Home (a waffle, a rent-vs-income bar, a ten-year line and a homes-built chart) and key-finding charts on every story page, including Story 3's slope chart. Their figures now come from `web/src/data/figures.json`, and the embeds follow the height of the dashboard tab shown. The same checks were run again on all eight pages.

| Check | Result |
|---|---|
| axe-core 4.10.2, WCAG 2.0/2.1 A and AA, after scrolling through each page | **0 violations** on all 8 pages at 1,440 px and at 375 px |
| Page wider than the screen at 320, 375 and 414 px | None: no page scrolls sideways |
| Text alternative for each chart | All 13 charts drawn by the site have a label (`role="img"` with `aria-label`), and each has a **Show the numbers** table |
| Keyboard | Every chart's marks can be reached with Tab, and each announces its value (for example "Cannot afford it: 27,664 households"). Every tab stop on the site shows a focus outline; the only stops without one are inside the embedded Superset dashboards (see *Not covered*) |
| Charts at 375 px | Readable: the ten-year line chart shortens city names and labels every other year, and the slope chart drops its long dwelling-type names |

**One fix:** at phone width, the arrow at the end of long chart links ("Explore affordability by unit size (Story 5) →") wrapped onto a line of its own. The arrow is now joined to the last word with a non-breaking space (`web/src/components/StoryHighlights.jsx`, `StoryPage.jsx`).

## Not covered

- **Inside the dashboards.** Charts are drawn by Superset, so their colours, keyboard support and
  screen-reader output are Superset's. Every chart's figures are also given in the page's text
  (narrative and KPI tiles), so no number is available only as a picture.
- **Screen readers.** Roles and labels were checked in the page code; the site was not tested with
  NVDA or VoiceOver.
- **Real devices.** Phone widths were checked in Chrome's mobile emulation, not on handsets.
