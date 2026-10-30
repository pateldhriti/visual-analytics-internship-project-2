import StoryPage from "../components/StoryPage.jsx";

const FILTERS = [
  { label: "Geography", value: "Windsor CMA vs. comparator CMAs" },
  { label: "Scope", value: "Affordability + rental + supply + comparison" },
];

const LIMITATIONS = [
  "This page is a placeholder for a real cross-story analysis -- no SQL view joining affordability, " +
    "rental-market, supply, and comparison data exists yet, so nothing here is backed by a query the " +
    "way Stories 1-4 are.",
  "Scoped to directly address a gap raised in team review: the four stories currently read as four " +
    "separate datasets rather than one combined analysis. Building this page for real (a joined view, " +
    "plus a Superset dashboard) is scheduled alongside next week's dashboard-building work.",
];

export default function StoryIntegratedAnalysis() {
  return (
    <StoryPage
      storyLabel="Story 5"
      title="How do affordability, rental conditions, and supply fit together?"
      questions={[
        "Where shelter-cost burden is highest, is the rental market also the tightest?",
        "Does Windsor's housing-supply pipeline match where affordability pressure is greatest?",
        "Taken together, how does Windsor's overall housing situation compare with its peer CMAs?",
      ]}
      filters={FILTERS}
      limitations={LIMITATIONS}
      variant="horizon"
      theme="neighbourhood"
    />
  );
}
