import StoryPage from "../components/StoryPage.jsx";

export default function StoryRentalMarket() {
  return (
    <StoryPage
      storyLabel="Story 2"
      title="What is happening in Windsor’s rental market?"
      questions={[
        "How do average rents, vacancy, rental stock and turnover vary by unit type and zone?",
        "Which parts of the market appear tighter or more affordable?",
      ]}
      source="CMHC Rental Market Survey, Windsor CMA 2025 (Oct-24/Oct-25) -- warehouse.fact_rental_market"
    />
  );
}
