import StoryPage from "../components/StoryPage.jsx";

export default function StoryAffordability() {
  return (
    <StoryPage
      storyLabel="Story 1"
      title="Who faces the greatest housing affordability pressure?"
      questions={[
        "How does shelter-cost burden vary by income group and household type?",
        "How different is the burden for renters and owners?",
      ]}
      source="StatCan 98-10-0252-01, Shelter-cost-to-income ratio by tenure (Windsor CMA, 2021 Census) -- warehouse.fact_shelter_cost"
    />
  );
}
