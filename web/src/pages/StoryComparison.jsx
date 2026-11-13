import StoryPage from "../components/StoryPage.jsx";
import StoryHighlights from "../components/StoryHighlights.jsx";
import SupersetGuestEmbed from "../components/SupersetGuestEmbed.jsx";
import { F, list, money, nth, num, pct } from "../lib/figures.js";

// Text condensed from docs/story4_narrative_final.md. Every figure comes
// from the warehouse.v_story4_* views (the ten-year figures from
// v_story4_rent_history and v_story4_period_comparison) and
// v_dashboard1_cma_benchmark behind the Story 4 dashboard, through
// web/src/data/figures.json (etl/site_figures.py).
const S = F.s4;
const C = F.s5;
const LATEST = F.s2.latestYear;
const lowest = (rank) => (rank === 1 ? "the lowest" : `the ${nth(rank)} lowest`);

const INTRO =
  `Is ${money(S.windsorRent)} a month high or low? This story places Windsor beside four Ontario ` +
  "cities of similar size, London, Kitchener-Cambridge-Waterloo, Hamilton and " +
  "St. Catharines-Niagara, on the same measures for the same month, then follows all five over " +
  `ten years, 2015 to ${LATEST}. The October ${LATEST} figures are for apartments, the only type ` +
  "CMHC compares across cities; the ten-year figures also include row houses. In the dashboard " +
  "below, Windsor is in blue.";

const NARRATIVE = [
  `${S.windsorRank === 1 ? "Windsor is the cheapest of the five." : "Windsor is not the cheapest of the five."} ` +
    `A 2-bedroom apartment averaged ${money(S.windsorRent)} a month in October ${LATEST}, ` +
    `${money(S.nextCheapestGap)} less than ${S.nextCheapest} and ${money(S.priciestGap)} less than ` +
    `${S.priciest}, and ${money(S.belowPeerMedian, 2)} below the median of the other four cities.` +
    (S.windsorCheapestLastYear ? " It was also the cheapest a year earlier." : ""),
  `Cheap, but not loose. Windsor's apartment vacancy rate was ${pct(S.windsorVacancy)}, ` +
    `${lowest(S.windsorVacancyRankLowest)} of the five` +
    (S.windsorVacancyRankLowest > 1
      ? `; only ${S.tightest} (${pct(S.tightestVacancy)}) was tighter`
      : "") +
    `. Vacancy rose in all five cities between ${LATEST - 1} and ${LATEST}, so Windsor loosened ` +
    "along with the region rather than on its own.",
  "Rents are rising at a middle pace. In the same buildings both years, Windsor's 2-bedroom rent " +
    `rose ${pct(S.windsorRentGrowth)}, ${nth(S.windsorRentGrowthRank)} of five: faster than ` +
    `${S.slowestGrowth} (${pct(S.slowestGrowthPct)}), slower than ${S.fastestGrowth} ` +
    `(${pct(S.fastestGrowthPct)}). Windsor also had the lowest turnover, ${pct(S.windsorTurnover)} ` +
    `against the other four cities' median of ${pct(S.peerTurnoverMedian)}, so fewer units come ` +
    "up for rent.",
  "Ten years on, the gap is closing. Windsor's 2-bedroom rent (apartments and row houses) went " +
    `from ${money(S.rent2015)} in 2015 to ${money(S.rent2025)} in ${LATEST}, up ` +
    `${pct(S.rentChangeDecade, 0)}; only ${S.fastestDecade} rose faster ` +
    `(${pct(S.fastestDecadePct, 0)}). Windsor's rent was ${pct(S.shareOfPeers2015, 0)} of the ` +
    `other four cities' average in 2015 and ${pct(S.shareOfPeers2025, 0)} in ${LATEST}.`,
  `The pandemic years changed the pace. Windsor's rent rose ${pct(S.growthBefore)} a year from ` +
    `2015 to 2020 and ${pct(S.growthAfter)} a year from 2020 to ${LATEST}` +
    (S.biggestSpeedup ? ", the biggest speed-up of the five cities" : "") +
    `, with jumps of ${list(S.jumps.map((j) => `${pct(j.pct)} in ${j.year}`))}. Likely reasons, ` +
    "not measured here: people leaving Toronto for cheaper cities during COVID, then record " +
    `immigration and international students. Vacancy fell to ${pct(S.vacancyLow)} in ` +
    `${S.vacancyLowYear} and recovered to ${pct(S.vacancyLatest)} by ${LATEST} as new rental ` +
    "buildings opened and student permits were capped, but rents kept rising.",
  "Cheaper than its peers is not the same as affordable. Story 1's median renter income of " +
    `${money(C.medianIncome)} covers about ${money(C.affordableRent)} a month at 30% of income, ` +
    `well under Windsor's ${money(S.windsorRent)} average 2-bedroom rent.`,
];

const DEFINITIONS = [
  {
    term: "Comparison cities",
    text: "London, Kitchener-Cambridge-Waterloo, Hamilton and St. Catharines-Niagara: Ontario CMAs close to Windsor in population with the same CMHC tables. Toronto and Ottawa are several times larger and are left out.",
  },
  {
    term: "Apartments only",
    text: "CMHC publishes the city comparison for purpose-built apartments only, so Windsor's figures here can differ slightly from Story 2's, which also include row houses.",
  },
  {
    term: "Average yearly increase",
    text: `The steady yearly rise that gets from the first year's rent to the last (compound growth), so the two five-year periods, 2015 to 2020 and 2020 to ${LATEST}, compare directly.`,
  },
  {
    term: "Rent growth (same buildings)",
    text: "CMHC's change in 2-bedroom rent for buildings surveyed in both years, so new, pricier buildings do not inflate the figure.",
  },
];

const LIMITATIONS = [
  "Five similar cities, not a national ranking.",
  "The affordability-gap index (rent growth minus renter income growth) cannot be computed: no source in this project reports renters' income year by year, so it is not estimated.",
  "Average rent includes long-time tenants, so it is lower than what a new tenant pays.",
  `The reasons given for the 2020-${LATEST} speed-up (migration, students, new buildings) are context from public reporting, not something this data measures.`,
];

const FILTERS = [
  { label: "Geography", value: "Windsor + 4 similar Ontario cities" },
  {
    label: "Period",
    value: `October ${LATEST}, and every October 2015-${LATEST} (Years filter)`,
  },
  { label: "Unit scope", value: "Apartments only; ten-year figures add row houses" },
];

const KPIS = [
  {
    label: "Windsor 2-bedroom apartment rent",
    value: money(S.windsorRent),
    accent: "blue",
    trend: "up",
  },
  {
    label: "Below the other four cities' median",
    value: money(S.belowPeerMedian, 2),
    accent: "teal",
    trend: "flat",
  },
  {
    label: "Windsor apartment vacancy",
    value: pct(S.windsorVacancy),
    accent: "violet",
    trend: "up",
  },
  {
    label: "Windsor 2-bedroom rent since 2015 (apartments + row houses)",
    value: `+${pct(S.rentChangeDecade, 0)}`,
    accent: "rose",
    trend: "up",
  },
];

// October 2-bedroom apartment rents (warehouse.v_story4_rent_comparison),
// cheapest first -- the ladder variant renders this ranking directly.
const RANKING = S.ranking.map((r, i) => ({
  label: r.market,
  value: money(r.rent),
  ...(r.isWindsor ? { highlight: true } : {}),
  ...(r.isWindsor && i === 0 ? { detail: "Cheapest of the five" } : {}),
}));

// Story 5 findings that combine this story's data with another story's
// (docs/story5_combined_analysis.md).
const CONNECTIONS = [
  {
    with: "With Story 1's renter incomes",
    text: `Windsor's rent is the lowest of the five cities, but so are its renters' incomes: a year of 2-bedroom rent takes ${pct(C.rentShare, 0)} of the median renter's income, about the same as in every other city (${pct(C.rentShareMin, 0)} to ${pct(C.rentShareMax, 0)}). Windsor is cheap, not more affordable.`,
  },
  {
    with: "With Story 3's construction",
    text: `Windsor builds the least of the five: ${num(C.startsPer1000, 1)} homes started a year per 1,000 households, and from 2016 to 2021 only ${pct(C.builtPerNeeded * 100, 0)} of the homes its population growth needed (${pct(C.builtPerNeededMin * 100, 0)} to ${pct(C.builtPerNeededMax * 100, 0)} elsewhere).`,
  },
];

export default function StoryComparison() {
  return (
    <StoryPage
      storyLabel="Story 4"
      title="How does Windsor compare?"
      intro={INTRO}
      questions={[
        "Where compatible data exists, how does Windsor compare with selected Canadian CMAs on rental indicators?",
      ]}
      filters={FILTERS}
      kpis={KPIS}
      variant="ladder"
      theme="neighbourhood"
      ranking={RANKING}
      highlights={<StoryHighlights only={["decade", "cheap"]} here="/stories/comparison" />}
      dashboard={
        <SupersetGuestEmbed
          dashboard="story4"
          fallbackDashboardId="windsor-story-4"
          title="Story 4: How does Windsor compare to similar markets? (Superset dashboard)"
        />
      }
      narrative={NARRATIVE}
      definitions={DEFINITIONS}
      limitations={LIMITATIONS}
      connections={CONNECTIONS}
      source={`CMHC Rental Market Survey data tables, Canada, October ${LATEST - 1} and October ${LATEST} (apartments); CMHC average rents and vacancy rates, October 2015-${LATEST}, via Statistics Canada tables 34-10-0133-01 and 34-10-0130-01`}
    />
  );
}
