import StoryPage from "../components/StoryPage.jsx";

export default function StoryComparison() {
  return (
    <StoryPage
      storyLabel="Story 4"
      title="How does Windsor compare?"
      questions={[
        "Where compatible data exists, how does Windsor compare with selected Canadian CMAs on rental indicators?",
      ]}
      source="CMHC Rental Market Survey, Canada 2025 (Windsor + 4 comparator CMAs, Oct-25) -- warehouse.fact_rental_market"
    />
  );
}
