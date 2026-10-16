import PageContainer from "../components/PageContainer.jsx";

export default function StoryRentalMarket() {
  return (
    <PageContainer>
      <p className="story-label">Story 2</p>
      <h1>What is happening in Windsor&rsquo;s rental market?</h1>
      <ul>
        <li>
          How do average rents, vacancy, rental stock and turnover vary by unit type and zone?
        </li>
        <li>Which parts of the market appear tighter or more affordable?</li>
      </ul>
      <p className="placeholder-note">
        Embedded dashboard and full narrative go here &mdash; scaffold placeholder only.
      </p>
    </PageContainer>
  );
}
