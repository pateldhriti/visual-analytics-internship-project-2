import StoryPage from "../components/StoryPage.jsx";
import StoryHighlights from "../components/StoryHighlights.jsx";
import SupersetGuestEmbed from "../components/SupersetGuestEmbed.jsx";
import { F, nth, num, pct } from "../lib/figures.js";

// Text condensed from docs/story3_narrative_final.md. Every figure comes
// from warehouse.v_story3_windsor_supply_annual and
// v_story3_windsor_supply_per_1000_households, the views behind the Story 3
// dashboard, through web/src/data/figures.json (etl/site_figures.py).
const S = F.s3;

const INTRO =
  "Rents and affordability depend partly on how many new homes are built. CMHC counts every " +
  "home whose construction starts and finishes in the Windsor area each month. This story " +
  `follows those counts from ${S.firstYear} to ${S.latestYear}: how much Windsor is building, ` +
  "and what kind of housing.";

const NARRATIVE = [
  `Building rose, then fell back. Windsor started about ${num(S.startsEarlyAvg)} homes a year ` +
    `from ${S.firstYear} to ${S.earlyLastYear}. In ${S.peakYear} starts jumped to ` +
    `${num(S.startsPeak)}, the most in ten years (${num(S.startsPeakPer1000, 1)} per 1,000 ` +
    `households), but ${S.latestYear} fell back to ${num(S.startsLatest)}, ` +
    `${pct(S.startsDropPct, 0)} fewer and about the level of ${S.firstYear}.`,
  `The mix has turned to apartments. Only ${pct(S.aptShareFirst, 0)} of the homes started in ` +
    `${S.firstYear} were apartments; in ${S.latestYear} it was ${pct(S.aptShareLatest, 0)} ` +
    `(${num(S.aptStartsLatest)} of ${num(S.startsLatest)}), while single-detached starts fell from ` +
    `${num(S.singlesFirst)} to ${num(S.singlesLatest)}. That is the housing type most renters use, ` +
    "although the apartment count also includes condos.",
  `More homes are being finished than started. In 2023 and ${S.latestYear} completions outpaced ` +
    `starts (${num(S.completions2023)} against ${num(S.starts2023)}, and ` +
    `${num(S.completionsLatest)} against ${num(S.startsLatest)}) as earlier projects reached the ` +
    `end. Homes under construction fell to ${num(S.underConstructionLatest)} at the end of ` +
    `${S.latestYear}, so the pipeline is getting smaller.`,
  "What this means: Windsor is building more apartments, not more homes overall. Story 2 found " +
    `vacancy rising since ${F.s2.vacancyLowYear}, consistent with these completions; with starts ` +
    "down again, that flow of new homes is likely to slow unless building picks up.",
];

const DEFINITIONS = [
  {
    term: "Housing starts",
    text: "Homes whose construction began during the period (CMHC counts a start when the foundation is in place).",
  },
  {
    term: "Completions",
    text: "Homes finished during the period, usually one to three years after they started.",
  },
  {
    term: "Under construction",
    text: "Homes started but not yet finished at the end of the period: the pipeline of future completions.",
  },
  {
    term: "Apartment and other",
    text: "CMHC's category for apartment buildings of every kind, rental and condominium, plus a few other structure types.",
  },
];

const LIMITATIONS = [
  "Counts cover the whole Windsor area; they are not split by rental zone or by whether a home is for rent or for sale.",
  "“Per 1,000 households” uses the 2021 Census household count for every year, so it shows the trend rather than an exact rate.",
  "2026 is partial (January to September) and is not used for yearly comparisons.",
];

const FILTERS = [
  { label: "Geography", value: "Windsor CMA" },
  { label: "Period", value: `${S.firstYear} to ${S.latestYear}` },
  { label: "Dwelling type", value: "All types" },
];

// Windsor CMA, latest full year -- the same figures as the Story 3 dashboard's cards.
const KPIS = [
  {
    label: `Homes started in Windsor, ${S.latestYear}`,
    value: num(S.startsLatest),
    accent: "teal",
    trend: "down",
  },
  {
    label: `Homes completed, ${S.latestYear}`,
    value: num(S.completionsLatest),
    accent: "blue",
    trend: "flat",
  },
  {
    label: "Under construction at year end",
    value: num(S.underConstructionLatest),
    accent: "violet",
    trend: "flat",
  },
  {
    label: `Apartment share of ${S.latestYear} starts`,
    value: pct(S.aptShareLatest, 0),
    accent: "rose",
    trend: "up",
  },
];

// Story 5 findings that combine this story's data with another story's
// (docs/story5_combined_analysis.md).
const C = F.s5;
const CONNECTIONS = [
  {
    with: "With Story 2's vacancy",
    text: `The 2023 completion surge lines up with the rental market loosening: vacancy rose from ${pct(F.s2.vacancyLow)} in ${F.s2.vacancyLowYear} to ${pct(F.s2.vacancyLatest)} in ${F.s2.latestYear}.`,
  },
  {
    with: "With Story 4's comparison cities",
    text: `Since ${S.firstYear} Windsor has started ${num(C.startsPer1000, 1)} homes a year per 1,000 households, ${C.startsPer1000Rank === 1 ? "the fewest" : `the ${nth(C.startsPer1000Rank)}-fewest`} of the five cities; ${C.topBuilder} started ${num(C.topBuilderPer1000, 1)}.`,
  },
  {
    with: "With Census population growth",
    text: `Windsor gained ${num(C.populationGrowth)} people from 2016 to 2021, about ${num(C.homesNeeded)} homes' worth, but completed ${num(C.homesCompleted)} homes: ${pct(C.builtPerNeeded * 100, 0)} of what was needed, the lowest of the five cities.`,
  },
];

export default function StoryHousingSupply() {
  return (
    <StoryPage
      storyLabel="Story 3"
      title="Is Windsor building enough housing?"
      intro={INTRO}
      questions={[
        "How many housing units are being started and completed, and which dwelling types contribute most?",
        "How can supply activity be interpreted alongside Windsor population and household context?",
      ]}
      filters={FILTERS}
      kpis={KPIS}
      variant="blueprint"
      theme="neighbourhood"
      narrative={NARRATIVE}
      definitions={DEFINITIONS}
      highlights={<StoryHighlights only={["mix", "supply"]} here="/stories/housing-supply" />}
      dashboard={
        <SupersetGuestEmbed
          dashboard="story3"
          fallbackDashboardId="windsor-story-3"
          title="Story 3: Is Windsor building enough housing? (Superset dashboard)"
        />
      }
      limitations={LIMITATIONS}
      connections={CONNECTIONS}
      source={`CMHC Starts and Completions Survey, Windsor CMA, Statistics Canada Table 34-10-0154-01, January ${S.firstYear} onward`}
    />
  );
}
