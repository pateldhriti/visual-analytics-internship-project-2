import StoryPage from "../components/StoryPage.jsx";
import SupersetGuestEmbed from "../components/SupersetGuestEmbed.jsx";

// Text condensed from docs/story2_narrative_final.md. Every figure comes
// from the warehouse.v_story2_* views behind the Story 2 dashboard (id 4);
// re-check both after a data refresh.
const INTRO =
  "Windsor has 19,883 purpose-built rental units. Each October, CMHC surveys them for rent, " +
  "vacancy and how often tenants move. This story follows those measures from 2020 to 2025 and " +
  "across the area's seven rental zones. In the dashboard below, click any zone to filter the " +
  "zone charts and see that zone explained in plain language.";

const NARRATIVE = [
  "Rents rose every year. The average rent across all unit sizes went from $953 a month in 2020 " +
    "to $1,293 in 2025, up 35.7% in five years. Two-bedroom units rose the most, by $413 (39.8%) " +
    "to $1,451. Three-bedroom units are the exception, but their figures rest on a small sample " +
    "and CMHC publishes no 2025 value for them.",
  "Vacancy dipped, then recovered. It fell from 3.5% in 2020 to a low of 1.8% in 2022, when very " +
    "few units were free, and climbed back to 3.6% in 2025, around the level usually seen as " +
    "balanced. Rents kept rising through the recovery, by 8.1% in 2024 and 5.9% in 2025, so more " +
    "vacancy has not yet meant lower rents.",
  "Most rentals are in the city, and the city is cheaper. The four Windsor city zones hold 82% of " +
    "units; the Centre is the cheapest zone at $1,155 a month, with the highest vacancy (4.6%). " +
    "The county zones are smaller, pricier and tighter: Amherstburg averages $1,955, $800 more " +
    "than the Centre, and county vacancy is 2.0% to 2.7%.",
  "Small units turn over most. About 1 in 8 units changed tenants in the past year: 15.0% of " +
    "studios but only 5.3% of three-bedroom units, where households, often families, stay longer. " +
    "At 30% of income, Story 1's median renter income of $48,400 affords about $1,210 a month, " +
    "already below the 2025 average rent.",
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
  { label: "Period", value: "October 2020 to October 2025" },
  { label: "Unit scope", value: "Apartments and row houses" },
];

const KPIS = [
  { label: "Average monthly rent, all units", value: "$1,293", accent: "violet", trend: "up" },
  { label: "Vacancy rate", value: "3.6%", accent: "blue", trend: "up" },
  { label: "Rent increase since 2020", value: "35.7%", accent: "rose", trend: "up" },
  { label: "Rental units", value: "19,883", accent: "teal", trend: "flat" },
];

// Story 5 findings that combine this story's data with another story's
// (docs/story5_combined_analysis.md; re-check after a data refresh).
const CONNECTIONS = [
  {
    with: "With Story 1's renter incomes",
    text: "About 61% of Windsor renter households earn less than the roughly $58,000 an average 2-bedroom needs under the 30% rule, and about half could not afford an average 1-bedroom.",
  },
  {
    with: "With Story 3's completions",
    text: "Vacancy fell to 1.8% in 2022, when few new homes were being finished. After completions jumped to 1,967 in 2023 it rose back to 3.6% by 2025, and rent growth slowed from 8.1% to 5.9%.",
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
      dashboard={
        <SupersetGuestEmbed
          dashboard="story2"
          fallbackDashboardId={4}
          title="Story 2: What is happening in Windsor's rental market? (Superset dashboard)"
          height={1600}
        />
      }
      narrative={NARRATIVE}
      definitions={DEFINITIONS}
      limitations={LIMITATIONS}
      connections={CONNECTIONS}
      source="CMHC Rental Market Survey, Windsor CMA, October 2020 to October 2025"
    />
  );
}
