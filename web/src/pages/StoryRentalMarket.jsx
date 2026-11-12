import StoryPage from "../components/StoryPage.jsx";
import StoryHighlights from "../components/StoryHighlights.jsx";
import SupersetGuestEmbed from "../components/SupersetGuestEmbed.jsx";
import { F, money, num, pct } from "../lib/figures.js";

// Text condensed from docs/story2_narrative_final.md. Every figure comes
// from the warehouse.v_story2_* views behind the Story 2 dashboard, through
// web/src/data/figures.json (etl/site_figures.py).
const S = F.s2;
const YEARS = S.latestYear - S.firstYear;

const INTRO =
  `Windsor has ${num(S.units)} purpose-built rental units. Each October, CMHC surveys them for ` +
  `rent, vacancy and how often tenants move. This story follows those measures from ` +
  `${S.firstYear} to ${S.latestYear} and across the area's seven rental zones. In the dashboard ` +
  "below, click any zone to filter the zone charts and see that zone explained in plain language.";

const NARRATIVE = [
  "Rents rose every year. The average rent across all unit sizes went from " +
    `${money(S.rentFirst)} a month in ${S.firstYear} to ${money(S.rentLatest)} in ${S.latestYear}, ` +
    `up ${pct(S.rentChangePct)} in ${YEARS} years. Two-bedroom units rose the most, by ` +
    `${money(S.twoBedRise)} (${pct(S.twoBedRisePct)}) to ${money(S.twoBedLatest)}. Three-bedroom ` +
    "units are the exception, but their figures rest on a small sample and CMHC publishes no " +
    `${S.latestYear} value for them.`,
  `Vacancy dipped, then recovered. It fell from ${pct(S.vacancyFirst)} in ${S.firstYear} to a low ` +
    `of ${pct(S.vacancyLow)} in ${S.vacancyLowYear}, when very few units were free, and climbed ` +
    `back to ${pct(S.vacancyLatest)} in ${S.latestYear}, around the level usually seen as ` +
    `balanced. Rents kept rising through the recovery, by ${pct(S.rentGrowthPrev)} in ` +
    `${S.prevYear} and ${pct(S.rentGrowthLatest)} in ${S.latestYear}, so more vacancy has not yet ` +
    "meant lower rents.",
  "Most rentals are in the city, and the city is cheaper. The four Windsor city zones hold " +
    `${pct(S.cityZoneShare, 0)} of units; the ${S.cheapestZone} is the cheapest zone at ` +
    `${money(S.cheapestRent)} a month, with the highest vacancy (${pct(S.cheapestVacancy)}). The ` +
    `county zones are smaller, pricier and tighter: ${S.priciestZone} averages ` +
    `${money(S.priciestRent)}, ${money(S.zoneRentGap)} more than the ${S.cheapestZone}, and county ` +
    `vacancy is ${pct(S.countyVacancyMin)} to ${pct(S.countyVacancyMax)}.`,
  `Small units turn over most. About 1 in ${S.turnoverOneIn} units changed tenants in the past ` +
    `year: ${pct(S.turnoverStudio)} of studios but only ${pct(S.turnoverThreeBed)} of three-bedroom ` +
    "units, where households, often families, stay longer. At 30% of income, Story 1's median " +
    `renter income of ${money(F.s5.medianIncome)} affords about ${money(F.s5.affordableRent)} a ` +
    `month, already below the ${S.latestYear} average rent.`,
];

const DEFINITIONS = [
  {
    term: "Vacancy rate",
    text: "Share of surveyed rental units that were empty and available for rent at the October survey.",
  },
  {
    term: "Turnover rate",
    text: "Share of occupied units where the tenant changed in the past 12 months.",
  },
  {
    term: "Average rent",
    text: "Average monthly rent of all surveyed units, occupied and vacant. Not the asking rent for a vacant unit, which is usually higher.",
  },
  {
    term: "Zone",
    text: "CMHC's division of the Windsor area into 7 rental zones: 4 in the City of Windsor and 3 in Essex County.",
  },
  {
    term: "Reliability letter",
    text: "CMHC's grade for each figure: a excellent, b very good, c good, d fair (use with caution). Suppressed values are shown as gaps.",
  },
];

const LIMITATIONS = [
  "Purpose-built rentals only: rented condos, basements and houses are not part of the survey.",
  "Average rent includes long-time tenants, so it is lower than what a new tenant pays today.",
  "Some zone and unit-size figures are suppressed by CMHC; three-bedroom and row-house figures are the least reliable.",
  "Rents are not adjusted for inflation.",
];

const FILTERS = [
  { label: "Geography", value: "Windsor CMA, 7 zones" },
  { label: "Period", value: `October ${S.firstYear} to October ${S.latestYear}` },
  { label: "Unit scope", value: "Apartments and row houses" },
];

const KPIS = [
  {
    label: "Average monthly rent, all units",
    value: money(S.rentLatest),
    accent: "violet",
    trend: "up",
  },
  { label: "Vacancy rate", value: pct(S.vacancyLatest), accent: "blue", trend: "up" },
  {
    label: `Rent increase since ${S.firstYear}`,
    value: pct(S.rentChangePct),
    accent: "rose",
    trend: "up",
  },
  { label: "Rental units", value: num(S.units), accent: "teal", trend: "flat" },
];

// Story 5 findings that combine this story's data with another story's
// (docs/story5_combined_analysis.md).
const CONNECTIONS = [
  {
    with: "With Story 1's renter incomes",
    text: `About ${pct(F.s5.cannotAffordPct, 0)} of Windsor renter households earn less than the roughly ${money(F.s5.incomeNeeded)} an average 2-bedroom needs under the 30% rule, and about half could not afford an average 1-bedroom.`,
  },
  {
    with: "With Story 3's completions",
    text: `Vacancy fell to ${pct(S.vacancyLow)} in ${S.vacancyLowYear}, when few new homes were being finished. After completions jumped to ${num(F.s3.completions2023)} in 2023 it rose back to ${pct(S.vacancyLatest)} by ${S.latestYear}, and rent growth slowed from ${pct(S.rentGrowthPrev)} to ${pct(S.rentGrowthLatest)}.`,
  },
];

export default function StoryRentalMarket() {
  return (
    <StoryPage
      storyLabel="Story 2"
      title="What is happening in Windsor’s rental market?"
      intro={INTRO}
      questions={[
        "How do average rents, vacancy, rental stock and turnover vary by unit type and zone?",
        "Which parts of the market appear tighter or more affordable?",
      ]}
      filters={FILTERS}
      kpis={KPIS}
      variant="ticker"
      theme="neighbourhood"
      highlights={<StoryHighlights only={["decade"]} here="/stories/rental-market" />}
      dashboard={
        <SupersetGuestEmbed
          dashboard="story2"
          fallbackDashboardId="windsor-story-2"
          title="Story 2: What is happening in Windsor's rental market? (Superset dashboard)"
        />
      }
      narrative={NARRATIVE}
      definitions={DEFINITIONS}
      limitations={LIMITATIONS}
      connections={CONNECTIONS}
      source={`CMHC Rental Market Survey, Windsor CMA, October ${S.firstYear} to October ${S.latestYear}`}
    />
  );
}
