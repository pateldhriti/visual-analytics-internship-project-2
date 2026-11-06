# Accessibility and Mobile Check

**Date:** 2026-11-06
**Scope:** the React site's eight pages (Home, Stories 1–5, Methodology, Sources) and the four
embedded Superset dashboards.
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

## Not covered

- **Inside the dashboards.** Charts are drawn by Superset, so their colours, keyboard support and
  screen-reader output are Superset's. Every chart's figures are also given in the page's text
  (narrative and KPI tiles), so no number is available only as a picture.
- **Screen readers.** Roles and labels were checked in the page code; the site was not tested with
  NVDA or VoiceOver.
- **Real devices.** Phone widths were checked in Chrome's mobile emulation, not on handsets.
