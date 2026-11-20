# Demo script (3 December 2026)

**Length:** about 10 minutes, then questions. **Presenter:** one person drives the browser; the speaker for each part is named in the deck. **Backup:** a screen recording of the same run (section 4), to play if the live site or apss fails.

## 1. Before the demo (30 minutes before, not on screen)

- [ ] Laptop on the campus network (or GlobalProtect connected). Open <https://whva.cs.uwindsor.ca> and <https://apss.cs.uwindsor.ca/health> (should say "OK").
- [ ] Log in to apss **in this browser** (UWindsor username and password), so the dashboard links open without a login screen during the demo.
- [ ] One browser window, full screen (F11), zoom 100%, bookmarks bar hidden; notifications off (Windows: Focus assist / Do not disturb); close Teams and email.
- [ ] Tabs open in this order: (1) the website home page, (2) the Story 1 dashboard on apss, (3) the backup recording, paused at the start, in the video player.
- [ ] Charger plugged in; screen mirrored to the projector at 1920 x 1080 or 1440 x 900.
- [ ] If the projector resolution is low, zoom the browser to 90% and check that a dashboard tab still fits.

## 2. The run (click by click)

Times are cumulative. **Say** lines are cues, not a script to read.

| Time | Click / do | Say (about) |
|---|---|---|
| 0:00 | Website **Home** page, at the top | "Windsor Housing Visual Analytics: five questions about housing in Windsor, answered with official Statistics Canada and CMHC data." |
| 0:30 | Scroll to **The story in four charts**; hover the waffle | "Our headline: 6 in 10 Windsor renters cannot afford the average 2-bedroom. Every number on this site comes from the same database as the dashboards." |
| 1:15 | Sidebar **Story 1 · Affordability** | "Who is under the most pressure? Renters: 34.8% spend 30% or more of income on shelter, against 10.9% of owners." |
| 1:45 | Scroll to the key-finding chart; press **Show the numbers** | "Every chart has its numbers as a table, and works with the keyboard." |
| 2:15 | **Open the dashboard ↗** (opens Story 1 on apss) | "The dashboards are where you explore. Each tab fits one screen and answers one question." |
| 2:30 | Dashboard tab **By Income** | "Burden falls steeply with income: below $10,000, 89% of renters are over the line." |
| 3:00 | Tab **Data Validation** | "We validated our calculation against Statistics Canada's own published rates: they match exactly." |
| 3:20 | Back to the website tab; sidebar **Story 2 · Rental Market**; then its dashboard, tab **Market Trends** | "The rental market: vacancy recovered from 1.8% in 2022 to 3.7%, but the 2-bedroom rent rose 53% since 2019." |
| 4:10 | Dashboard tab **Zones Compared**, then **Explore by Zone**; click a zone row in the table | "By zone: the city centre is the cheapest and has the most vacancy. Clicking a zone filters the tab." |
| 5:00 | Website **Story 3 · Housing Supply**; its dashboard, tab **This Year So Far** | "Construction peaked in 2024; this year's starts are 21% behind last year." |
| 5:30 | Tab **Pipeline and Intended Market** | "Rental homes are being finished, 590 this year, but few new ones are starting." |
| 6:00 | Website **Story 4 · CMA Comparison**; its dashboard, tab **Since 2019, with Toronto** | "Windsor is still the cheapest of the five Ontario cities, but its rent rose fastest since 2019." |
| 6:45 | In the filter bar, **Peer CMA**: remove two cities, **Apply filters** | "Every dashboard has filters; here we narrow the comparison." |
| 7:15 | Website **Story 5 · Combined Analysis** | "Story 5 joins the four stories' data. Windsor is cheaper, not more affordable: rent takes 36% of the median renter's income, the same as Hamilton." |
| 8:00 | Its dashboard, tab **8. Windsor 2030** | "On current trends, the share of renters priced out of a 2-bedroom rises from 52% to 63% by 2030. These are scenarios, not forecasts." |
| 8:45 | Website **Methodology** | "How it works: 27 government files, checked before every load, into one database; refreshed weekly; 224 automated tests." |
| 9:30 | Website **Home** | "Thank you. Questions?" |

## 3. If something goes wrong

| Problem | Do |
|---|---|
| A dashboard shows the apss login page | Log in (it keeps your place); next time, log in before the demo |
| A dashboard is slow (spinner over 10 s) | Keep talking over the website's own chart for that story (same numbers), then try the tab again |
| apss is down, or every dashboard fails | Switch to the backup recording at the matching story (chapters in section 4) |
| The website (whva) is down | Play the backup recording from the start |
| No network at all | Play the backup recording; it is saved on the laptop, not online |
| A question you cannot answer | "Good question: the data dictionary and decision log in our repository cover that; we will follow up." |

## 4. Backup recording

`demo_backup.webm` (3 min 35 s, 20 MB), recorded on 20 November 2026 from the live site and apss, following section 2 without sound, with a caption at each step so it can be narrated live. It plays in Chrome, Edge and VLC (open it in the browser if no player is installed). Kept in the team's OneDrive folder, `Visual Analystics\demo_recording\` with `chapters.txt`, not in the repository (video files are too large for git). The apss header shows the account that recorded it. Chapters:

| Starts at | Part |
|---|---|
| 0:00 | Home |
| 0:16 | Story 1 and its dashboard |
| 1:09 | Story 2 and its dashboard |
| 1:46 | Story 3 and its dashboard |
| 2:18 | Story 4 and its dashboard |
| 2:49 | Story 5 and its dashboard |
| 3:23 | Methodology |

The recording is made by `deploy/record_demo.js` (Playwright, `node record_demo.js .env.apss <folder>`); re-run it after any change to the site or dashboards so the backup matches what is shown live.
