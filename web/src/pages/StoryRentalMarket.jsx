import StoryPage from "../components/StoryPage.jsx";

const DEFINITIONS = [
  {
    term: "Vacancy rate",
    text: "Share of surveyed rental units that were unoccupied and available for rent at survey date.",
  },
  {
    term: "Turnover rate",
    text: "Share of occupied units where the tenant changed over the past 12 months -- a proxy for how often units in a zone or unit type change hands.",
  },
  {
    term: "Zone",
    text: "CMHC's own geographic breakdown of the Windsor CMA into 7 zones plus 2 aggregate rows, used consistently across every rental-market table in this story.",
  },
  {
    term: "Reliability letter",
    text: "CMHC's own data-quality grade on a cell: a/b/c are good-to-excellent, d means use with caution, and ‘**’ means the value was suppressed for sample size or confidentiality.",
  },
];

const LIMITATIONS = [
  "Row/townhouse-only figures are heavily suppressed in Windsor's workbook -- row housing is a small share of the rental stock, so many zone x bedroom-type cells for that segment carry no reliable value.",
  "Universe (unit-count) tables carry no reliability letters or suppression at all -- raw counts are always a plain number, which is a real structural difference from the rate and rent tables, not an inconsistency.",
];

const FILTERS = [
  { label: "Geography", value: "Windsor CMA" },
  { label: "Period", value: "October 2025" },
  { label: "Unit scope", value: "Combined (apartment + row)" },
];

const KPIS = [
  { label: "Vacancy rate", value: "3.6%", accent: "blue", trend: "up" },
  { label: "Average 2-bedroom rent", value: "$1,451", accent: "violet", trend: "up" },
];

export default function StoryRentalMarket() {
  return (
    <StoryPage
      storyLabel="Story 2"
      title="What is happening in Windsor’s rental market?"
      questions={[
        "How do average rents, vacancy, rental stock and turnover vary by unit type and zone?",
        "Which parts of the market appear tighter or more affordable?",
      ]}
      filters={FILTERS}
      kpis={KPIS}
      definitions={DEFINITIONS}
      limitations={LIMITATIONS}
      source="CMHC Rental Market Survey, Windsor CMA 2025 (Oct-24/Oct-25) -- warehouse.fact_rental_market"
    />
  );
}
