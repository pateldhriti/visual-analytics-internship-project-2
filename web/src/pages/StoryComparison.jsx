import StoryPage from "../components/StoryPage.jsx";
import SupersetGuestEmbed from "../components/SupersetGuestEmbed.jsx";

// Text condensed from docs/story4_narrative_final.md. Every figure comes
// from the warehouse.v_story4_* views (the ten-year figures from
// v_story4_rent_history and v_story4_period_comparison) and v_dashboard1_cma_benchmark behind
// the Story 4 dashboard (id 6); re-check both after a data refresh.
const INTRO =
  "Is $1,454 a month high or low? This story places Windsor beside four Ontario cities of " +
  "similar size, London, Kitchener-Cambridge-Waterloo, Hamilton and St. Catharines-Niagara, on " +
  "the same measures for the same month, then follows all five over ten years, 2015 to 2025. " +
  "The October 2025 figures are for apartments, the only type CMHC compares across cities; the " +
  "ten-year figures also include row houses. In the dashboard below, Windsor is in blue.";

const NARRATIVE = [
  "Windsor is the cheapest of the five. A 2-bedroom apartment averaged $1,454 a month in October " +
    "2025, $73 less than St. Catharines-Niagara and $378 less than Kitchener-Cambridge-Waterloo, " +
    "and $199.50 below the five-city median. It was also the cheapest a year earlier.",
  "Cheap, but not loose. Windsor's apartment vacancy rate was 3.7%, the second lowest of the five; " +
    "only Hamilton (3.6%) was tighter. Vacancy rose in all five cities between 2024 and 2025, so " +
    "Windsor loosened along with the region rather than on its own.",
  "Rents are rising at a middle pace. In the same buildings both years, Windsor's 2-bedroom rent " +
    "rose 3.6%, third of five: faster than Hamilton (1.6%), slower than St. Catharines-Niagara " +
    "(5.5%). Windsor also had the lowest turnover, 12.2% against a median of 14.1%, so fewer units " +
    "come up for rent.",
  "Ten years on, the gap is closing. Windsor's 2-bedroom rent (apartments and row houses) went " +
    "from $823 in 2015 to $1,451 in 2025, up 76%; only Kitchener-Waterloo rose faster (82%). " +
    "Windsor's rent was 84% of the other four cities' average in 2015 and 87% in 2025.",
  "The pandemic years changed the pace. Windsor's rent rose 4.8% a year from 2015 to 2020 and " +
    "6.9% a year from 2020 to 2025, the biggest speed-up of the five cities, with jumps of 9.7% in " +
    "2020, 11.0% in 2021 and 10.4% in 2024. Likely reasons, not measured here: people leaving " +
    "Toronto for cheaper cities during COVID, then record immigration and international students. " +
    "Vacancy fell to 1.8% in 2022 and recovered to 3.6% by 2025 as new rental buildings opened and " +
    "student permits were capped, but rents kept rising.",
  "Cheaper than its peers is not the same as affordable. Story 1's median renter income of " +
    "$48,400 covers about $1,210 a month at 30% of income, well under Windsor's $1,454 average " +
    "2-bedroom rent.",
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
    text: "The steady yearly rise that gets from the first year's rent to the last (compound growth), so the two five-year periods, 2015 to 2020 and 2020 to 2025, compare directly.",
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
  "The reasons given for the 2020-2025 speed-up (migration, students, new buildings) are context from public reporting, not something this data measures.",
];

const FILTERS = [
  { label: "Geography", value: "Windsor + 4 similar Ontario cities" },
  { label: "Period", value: "October 2025, and every October 2015-2025 (Years filter)" },
  { label: "Unit scope", value: "Apartments only" },
];

const KPIS = [
  { label: "Windsor 2-bedroom apartment rent", value: "$1,454", accent: "blue", trend: "up" },
  { label: "Below the five-city median", value: "$199.50", accent: "teal", trend: "flat" },
  { label: "Windsor apartment vacancy", value: "3.7%", accent: "violet", trend: "up" },
  { label: "Windsor 2-bedroom rent since 2015", value: "+76%", accent: "rose", trend: "up" },
];

// Real Oct-25 2-bedroom apartment rents (warehouse.v_story4_rent_comparison),
// cheapest first -- the ladder variant renders this ranking directly.
const RANKING = [
  { label: "Windsor CMA", value: "$1,454", highlight: true, detail: "Cheapest of the five" },
  { label: "St. Catharines-Niagara CMA", value: "$1,527" },
  { label: "London CMA", value: "$1,651" },
  { label: "Hamilton CMA", value: "$1,656" },
  { label: "Kitchener-Cambridge-Waterloo CMA", value: "$1,832" },
];

// Story 5 findings that combine this story's data with another story's
// (docs/story5_combined_analysis.md; re-check after a data refresh).
const CONNECTIONS = [
  {
    with: "With Story 1's renter incomes",
    text: "Windsor's rent is the lowest of the five cities, but so are its renters' incomes: a year of 2-bedroom rent takes 36% of the median renter's income, about the same as in every other city. Windsor is cheap, not more affordable.",
  },
  {
    with: "With Story 3's construction",
    text: "Windsor builds the least of the five: 8.4 homes started a year per 1,000 households, and from 2016 to 2021 only 59% of the homes its population growth needed (72% to 91% elsewhere).",
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
      dashboard={
        <SupersetGuestEmbed
          dashboard="story4"
          fallbackDashboardId={6}
          title="Story 4: How does Windsor compare to similar markets? (Superset dashboard)"
        />
      }
      narrative={NARRATIVE}
      definitions={DEFINITIONS}
      limitations={LIMITATIONS}
      connections={CONNECTIONS}
      source="CMHC Rental Market Survey data tables, Canada, October 2024 and October 2025 (apartments); CMHC average rents and vacancy rates, October 2015-2025, via Statistics Canada tables 34-10-0133-01 and 34-10-0130-01"
    />
  );
}
