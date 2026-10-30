import StoryPage from "../components/StoryPage.jsx";

const DEFINITIONS = [
  {
    term: "Comparator CMA",
    text: "One of 4 Ontario CMAs -- London, Kitchener-Cambridge-Waterloo, Hamilton, St. Catharines-Niagara -- chosen for being size-comparable to Windsor (within roughly ±36% of its population) and confirmed on CMHC's major-centres list with the same RMS 2025 tables available.",
  },
];

const LIMITATIONS = [
  "The affordability-gap index (rent growth vs. renter-income growth) isn't computed -- no source extracted so far contains a renter-income time series to calculate a real growth rate from, so it's left blank rather than estimated.",
  "A genuine 5th comparator doesn't exist in this dataset: the only other major-centres-confirmed Ontario CMAs (Toronto, Ottawa) are 252% to 1,368% larger than Windsor by population, which would fail the size-comparability criterion outright.",
];

const FILTERS = [
  { label: "Geography", value: "Windsor + 4 comparator CMAs" },
  { label: "Period", value: "October 2025" },
  { label: "Unit scope", value: "Apartment-only" },
];

const KPIS = [
  { label: "Windsor apartment vacancy rate", value: "3.7%", accent: "blue", trend: "flat" },
  {
    label: "Vacancy rank among 5 Ontario CMAs",
    value: "2nd-tightest",
    accent: "violet",
    trend: "flat",
  },
];

// Real, already-verified vacancy figures for Windsor + its 4 comparator
// CMAs (docs/story4_exploratory_findings.md, warehouse.v_story4_vacancy_comparison,
// Oct-25, apartment scope) -- the story's own content IS this ranking, so
// the "ladder" variant renders it directly instead of burying it in prose.
const RANKING = [
  { label: "Hamilton CMA", value: "3.6%" },
  { label: "Windsor CMA", value: "3.7%", highlight: true, detail: "This project's own CMA" },
  { label: "St. Catharines-Niagara CMA", value: "3.9%" },
  { label: "London CMA", value: "4.0%" },
  { label: "Kitchener-Cambridge-Waterloo CMA", value: "4.1%" },
];

export default function StoryComparison() {
  return (
    <StoryPage
      storyLabel="Story 4"
      title="How does Windsor compare?"
      questions={[
        "Where compatible data exists, how does Windsor compare with selected Canadian CMAs on rental indicators?",
      ]}
      filters={FILTERS}
      kpis={KPIS}
      variant="ladder"
      theme="neighbourhood"
      ranking={RANKING}
      definitions={DEFINITIONS}
      limitations={LIMITATIONS}
      source="CMHC Rental Market Survey, Canada 2025 (Windsor + 4 comparator CMAs, Oct-25) -- warehouse.fact_rental_market"
    />
  );
}
