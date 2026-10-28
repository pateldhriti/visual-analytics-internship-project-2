import PageContainer from "./PageContainer.jsx";
import FilterBar from "./FilterBar.jsx";
import KpiRow from "./KpiRow.jsx";

// Reusable shape every story page (Story 1-4) renders through, so adding a
// real narrative or a real dashboard embed later means filling in props on
// an existing page, not rebuilding the page's layout from scratch each
// time. `dashboard` and `narrative` are optional on purpose: a story whose
// write-up or embed isn't ready yet still renders consistently with the
// others, via the same placeholder note the scaffold pages already used.
// `definitions` and `limitations` are optional too -- a story can state
// real metric definitions and known data limitations without every story
// needing both filled in at once. `filters` and `kpis` are optional too --
// not every story has verified figures ready for a KPI row yet.
export default function StoryPage({
  storyLabel,
  title,
  questions,
  filters,
  kpis,
  narrative,
  dashboard,
  definitions,
  limitations,
  source,
}) {
  return (
    <>
      <PageContainer>
        <p className="story-label">{storyLabel}</p>
        <h1>{title}</h1>
        {questions?.length > 0 && (
          <ul className="story-questions">
            {questions.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        )}

        <FilterBar filters={filters} />
        <KpiRow tiles={kpis} />
      </PageContainer>

      {/* Wider band than the prose column above -- a Superset dashboard's
          12-column grid plus its own filter sidebar needs more room than
          the ~68ch narrative text, so this breaks out to its own max-width
          instead of sharing PageContainer's narrower one (same pattern as
          Home.jsx's full-bleed hero banner). */}
      <div className="story-dashboard-band">
        <div className="story-dashboard-slot">
          {dashboard ?? (
            <p className="placeholder-note">Embedded dashboard goes here &mdash; not yet built.</p>
          )}
        </div>
      </div>

      <PageContainer>
        {narrative?.length > 0 ? (
          <div className="story-narrative">
            {narrative.map((paragraph, i) => (
              <p key={i}>{paragraph}</p>
            ))}
          </div>
        ) : (
          <p className="placeholder-note">
            Full narrative write-up goes here &mdash; not yet drafted.
          </p>
        )}

        {definitions?.length > 0 && (
          <div className="definitions-grid">
            {definitions.map((d) => (
              <div className="card definition-card" key={d.term}>
                <p className="definition-term">{d.term}</p>
                <p className="definition-text">{d.text}</p>
              </div>
            ))}
          </div>
        )}

        {limitations?.length > 0 && (
          <div className="limitations-note">
            <strong>Known limitations</strong>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </div>
        )}

        {source && <p className="story-source-line">Source: {source}</p>}
      </PageContainer>
    </>
  );
}
