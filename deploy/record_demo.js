// Backup recording of the demo (docs/demo_script.md, section 2): the live website and the
// dashboards on apss, without sound, with a caption at each step so it can be narrated live.
//
//   node record_demo.js <.env.apss> <output folder>
//
// Needs Node with playwright-core (npm install playwright-core) and Chrome; on campus or the
// VPN. It logs in to apss first in a separate, unrecorded browser (credentials from the
// .env.apss file: SUPERSET_LOGIN_USER / SUPERSET_LOGIN_PASSWORD), so no login appears in the
// video. Writes demo_backup.webm and chapters.txt (the time each part starts).
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright-core");

const env = Object.fromEntries(fs.readFileSync(process.argv[2], "utf8").split(/\r?\n/).filter((l) => l.includes("="))
  .map((l) => { const i = l.indexOf("="); return [l.slice(0, i), l.slice(i + 1).replace(/^'(.*)'$/, "$1")]; }));
const OUT = process.argv[3];
const SITE = "https://whva.cs.uwindsor.ca";
const APSS = (env.SUPERSET_URL || "https://apss.cs.uwindsor.ca").replace(/\/$/, "");
const SIZE = { width: 1440, height: 900 };
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";

const chapters = [];
let t0;

async function caption(p, text) {
  await p.evaluate((t) => {
    let el = document.getElementById("demo-caption");
    if (!el) {
      el = document.createElement("div");
      el.id = "demo-caption";
      el.style.cssText = "position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:2147483647;" +
        "background:rgba(17,24,39,.88);color:#fff;font:600 20px/1.4 system-ui,sans-serif;padding:12px 22px;" +
        "border-radius:10px;max-width:80%;text-align:center;box-shadow:0 6px 24px rgba(0,0,0,.25)";
      document.body.appendChild(el);
    }
    el.textContent = t;
  }, text).catch(() => {});
}

async function step(p, text, action, holdMs = 4000) {
  try {
    if (action) await action();
  } catch (e) {
    console.log(`  (skipped part of "${text}": ${e.message.split("\n")[0]})`);
  }
  await caption(p, text);
  await p.waitForTimeout(holdMs);
}

function chapter(name) {
  const s = (Date.now() - t0) / 1000;
  chapters.push(`${String(Math.floor(s / 60))}:${String(Math.round(s % 60)).padStart(2, "0")}  ${name}`);
  console.log("chapter", chapters[chapters.length - 1]);
}

async function scroll(p, px, times = 1) {
  for (let i = 0; i < times; i++) { await p.mouse.wheel(0, px); await p.waitForTimeout(700); }
}

async function openDashboard(p, slug, tab) {
  await p.goto(`${APSS}/superset/dashboard/${slug}/`, { waitUntil: "domcontentloaded" });
  await p.waitForSelector(".dashboard-component-tabs [role=tab]", { timeout: 60000 });
  await p.waitForTimeout(6000);
  if (tab) await clickTab(p, tab);
}

async function clickTab(p, tab) {
  await p.locator(".dashboard-component-tabs [role=tab]").filter({ hasText: tab }).first().click({ force: true });
  await p.waitForTimeout(6000);
}

async function site(p, route) {
  await p.goto(SITE + route, { waitUntil: "networkidle" });
  await p.waitForTimeout(1500);
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ executablePath: CHROME });

  // 1. Log in to apss, unrecorded.
  const login = await browser.newContext({ viewport: SIZE });
  const lp = await login.newPage();
  await lp.goto(`${APSS}/login/`, { waitUntil: "networkidle" });
  await lp.locator("input:not([type=hidden]):not([type=password])").first().fill(env.SUPERSET_LOGIN_USER);
  await lp.locator("input[type=password]").first().fill(env.SUPERSET_LOGIN_PASSWORD);
  await lp.keyboard.press("Enter");
  await lp.waitForTimeout(6000);
  const state = await login.storageState();
  await login.close();

  // 2. Record the run.
  const ctx = await browser.newContext({ viewport: SIZE, storageState: state,
    recordVideo: { dir: OUT, size: SIZE } });
  const p = await ctx.newPage();
  t0 = Date.now();

  chapter("Home");
  await step(p, "Windsor Housing Visual Analytics: five questions about housing in Windsor, from official data",
    () => site(p, "/"), 5000);
  await step(p, "The story in four charts: 6 in 10 Windsor renters cannot afford the average 2-bedroom",
    () => scroll(p, 700, 2), 6000);

  chapter("Story 1: Who faces the greatest affordability pressure?");
  await step(p, "Story 1: renters face the most pressure (34.8% spend 30%+ of income on shelter, owners 10.9%)",
    () => site(p, "/stories/affordability"), 5000);
  await step(p, "Every chart on the site has its numbers as a table, and works with the keyboard",
    async () => { await scroll(p, 600, 2); await p.getByText("Show the numbers").first().click(); }, 5000);
  await step(p, "The dashboard (on the university's Superset): each tab answers one question and fits one screen",
    () => openDashboard(p, "windsor-story-1", "Affordability Gap"), 4000);
  await step(p, "By income: below $10,000, 89% of renters spend 30% or more on shelter",
    () => clickTab(p, "By Income"), 5000);
  await step(p, "Validated: our rates match Statistics Canada's published figures exactly",
    () => clickTab(p, "Data Validation"), 4000);

  chapter("Story 2: Windsor's rental market");
  await step(p, "Story 2: vacancy recovered to 3.7%, but the 2-bedroom rent rose 53% since 2019",
    () => site(p, "/stories/rental-market"), 4000);
  await step(p, "Market trends: vacancy and rent, 2019-2025 (apartments)",
    () => openDashboard(p, "windsor-story-2", "Market Trends"), 6000);
  await step(p, "By zone: the city centre is the cheapest and has the most vacancy",
    () => clickTab(p, "Zones Compared"), 5000);

  chapter("Story 3: Is Windsor building enough housing?");
  await step(p, "Story 3: construction peaked in 2024; this year's starts are 21% behind last year",
    () => openDashboard(p, "windsor-story-3", "This Year So Far"), 6000);
  await step(p, "Rental homes are being finished (590 this year), but few new ones are starting",
    () => clickTab(p, "Pipeline and Intended Market"), 6000);

  chapter("Story 4: Windsor compared with similar cities");
  await step(p, "Story 4: still the cheapest of five Ontario cities, but its rent rose fastest since 2019",
    () => openDashboard(p, "windsor-story-4", "Since 2019"), 6000);
  await step(p, "Windsor against every Canadian city, 2021: rent and renter cost burden",
    () => clickTab(p, "All Canadian Cities"), 5000);

  chapter("Story 5: Combined Analysis");
  await step(p, "Story 5, Combined Analysis: Windsor is cheaper, not more affordable",
    () => site(p, "/stories/integrated-analysis"), 5000);
  await step(p, "Rent takes 36% of the median renter's income in Windsor, the same as in Hamilton",
    () => scroll(p, 700, 2), 5000);
  await step(p, "Windsor 2030: renters priced out of a 2-bedroom, 52% now, 63% by 2030 (central scenario)",
    () => openDashboard(p, "windsor-story-5", "Windsor 2030"), 7000);

  chapter("Methodology");
  await step(p, "How it works: 27 government files, checked before every load, refreshed weekly, 224 automated tests",
    () => site(p, "/methodology"), 6000);
  await step(p, "Thank you", () => site(p, "/"), 4000);

  const video = p.video();
  await ctx.close();
  const file = path.join(OUT, "demo_backup.webm");
  await video.saveAs(file);
  await video.delete();
  fs.writeFileSync(path.join(OUT, "chapters.txt"), chapters.join("\n") + "\n");
  await browser.close();
  console.log("saved", file);
})();
