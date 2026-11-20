# User-testing sessions: guide and notes template

**Purpose.** Check goal G1 of the design document (*a visitor can follow each story from question to evidence to conclusion; 4 of 5 testers can state each story's main finding in one sentence*) and find what to fix before the demo, Story 1 first.
**Format.** About 45 minutes, one tester at a time, think-aloud. 3 sessions per facilitator (6 across the two halves of the task). **Where:** the live site, <https://whva.cs.uwindsor.ca> (on campus or the VPN), Chrome, full screen. The tester needs a UWindsor login for the dashboards.
**Testers.** People who have not worked on the project: ideally one student who rents in Windsor, one who has never used a dashboard tool, and one with some data background. No names in the notes: use T1, T2, T3.

## Before each session (5 min, not with the tester)

- Open the site's home page in a fresh browser window; clear the dashboard filters (Superset: **Clear all**).
- Have the notes sheet below open, one copy per tester; start the timer and, with permission, the screen recording.

## Script

**Introduction (3 min).** Read out:
> "Thank you for helping. We're testing the website, not you, so nothing you do is wrong. Please think aloud: say what you're looking at, what you expect and what surprises you. I'll mostly stay quiet. We'll take about 45 minutes. May I record the screen? Only the team will see it."

**First impression (3 min).** Home page, no clicks: *"What do you think this site is for? Who is it for?"*

**Tasks (30 min).** Read each task, then only watch. Note where they click, where they hesitate (more than 10 seconds), what they say, and whether they succeed. Do not help unless they are stuck for 2 minutes; if you help, mark the task "assisted".

| # | Task (read aloud) | Success looks like | Story |
|---|---|---|---|
| 1 | "Who in Windsor has the hardest time paying for housing? Find out and tell me in one sentence." | Renters (34.8% spend 30%+ vs 10.9% of owners) and low-income households | 1 |
| 2 | "Among households earning under $10,000, how many renters spend 30% or more on housing?" | Finds the income chart (Story 1 dashboard, By Income tab): 89.34% | 1 |
| 3 | "Is the problem bigger for families or for people living alone?" | Household Type tab: non-family renters (43%) | 1 |
| 4 | "Does the website's number match Statistics Canada's own figure?" | Data Validation tab: 34.8 and 34.8, difference 0 | 1 |
| 5 | "Is it getting easier or harder to find an apartment to rent in Windsor? Since when?" | Story 2: vacancy 1.8% (2022) up to 3.7% (2025) | 2 |
| 6 | "Which part of Windsor has the cheapest rents?" | Zone 1 - Centre, $1,157 (Explore by Zone) | 2 |
| 7 | "Is Windsor building more or less than last year?" | Story 3: starts behind 2025 by about 21% so far this year | 3 |
| 8 | "Is Windsor cheaper than London, Ontario? Is it cheaper to live in, for a renter?" | Story 4 rents; Story 5: cheaper rent but similar share of income | 4, 5 |
| 9 | "Find one finding that surprised you, and tell me where it comes from." | Names the source line or dashboard | any |

**Debrief (6 min).**
1. *"In one sentence each, what did you learn from Stories 1, 2, 3, 4 and 5?"* (write their words; this is the G1 measure)
2. *"What was the most confusing moment?"*
3. *"Was anything hard to read: text, colours, charts?"*
4. *"On a scale of 1 to 5, how easy was it to find answers? Why that number?"*
5. *"Would you use this? For what?"*

**Close.** Thank them; stop the recording.

## Notes sheet (one per tester)

```
Tester: T_   Date/time: ________   Facilitator: ________   Device/browser: ________
Background: renter? / dashboard experience? / data background?

First impression (what is it for, who for):

| Task | Success / assisted / failed | Time (min) | Where they hesitated | What they said (quotes) |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |
| 6 |  |  |  |  |
| 7 |  |  |  |  |
| 8 |  |  |  |  |
| 9 |  |  |  |  |

One-sentence findings in their words:
  Story 1:            correct? Y/N
  Story 2:            correct? Y/N
  Story 3:            correct? Y/N
  Story 4:            correct? Y/N
  Story 5:            correct? Y/N
Most confusing moment:
Hard to read:
Ease of finding answers (1-5) and why:
Would they use it, for what:
```

## After the sessions: write-up

Put the results in `docs/user_testing_results.md`:

1. **Who took part** (T1-T3: background only) and when.
2. **Task results:** a table of tasks x testers (success / assisted / failed) and the median time per task.
3. **G1 result:** for each story, how many testers stated the main finding correctly (target: 4 of 5 across all sessions).
4. **Issues found,** each with: what happened, how many testers, severity (**high**: blocked the task; **medium**: slowed or confused; **low**: cosmetic), the page or dashboard tab, and a proposed fix.
5. **Story 1 fix list:** the Story 1 issues in order of severity. This list is the input for the task "Fix Story 1 issues from testing".
