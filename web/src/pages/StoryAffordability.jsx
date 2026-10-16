import PageContainer from "../components/PageContainer.jsx";

export default function StoryAffordability() {
  return (
    <PageContainer>
      <p className="story-label">Story 1</p>
      <h1>Who faces the greatest housing affordability pressure?</h1>
      <ul>
        <li>How does shelter-cost burden vary by income group and household type?</li>
        <li>How different is the burden for renters and owners?</li>
      </ul>
      <p className="placeholder-note">
        Embedded dashboard and full narrative go here &mdash; scaffold placeholder only.
      </p>
    </PageContainer>
  );
}
