import { motion } from "framer-motion";
import PageContainer from "./PageContainer.jsx";
import FilterBar from "./FilterBar.jsx";
import KpiRow from "./KpiRow.jsx";
import { staggerParent, fadeUp, fadeIn, slideFromRight, scaleIn, reveal } from "../lib/motion.js";

// Turns "Story 1" into "01" -- the recurring index numeral every story page
// shows, the one visual thread tying 5 otherwise differently-shaped pages
// back into one family. Falls back to the raw label if it's ever not in
// the "Story N" shape (e.g. a future non-numbered page using this component).
function indexNumeral(storyLabel) {
  const match = storyLabel?.match(/(\d+)/);
  return match ? match[1].padStart(2, "0") : storyLabel;
}

// Reusable shape every story page (Story 1-5) renders through -- but NOT a
// single fixed layout anymore. `variant` picks one of 5 distinct visual
// treatments (see index.css's "Story variants" block), so each tab reads as
// its own page rather than 5 copies of one template with different text.
// `dashboard` and `narrative` stay optional: a story whose write-up or
// embed isn't ready yet still renders consistently, via the same honest
// placeholder note the scaffold pages always used -- the "horizon" variant
// just dresses that same honest gap differently instead of hiding it.
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
  variant = "classic",
  highlightStat, // spotlight variant: { value, label, detail }
  ranking, // ladder variant: [{ label, value, highlight, detail }]
  theme, // one of index.css's [data-theme] presets -- a temporary
  // theme-comparison aid (one candidate theme per story tab) so the
  // same real content can be compared side by side before picking one
  // to apply everywhere. Omit it to use the site's current default.
}) {
  const numeral = indexNumeral(storyLabel);
  const isSpotlight = variant === "spotlight" && highlightStat;
  const isLadder = variant === "ladder" && ranking?.length > 0;
  const isBlueprint = variant === "blueprint";
  const isTicker = variant === "ticker";
  const isHorizon = variant === "horizon";

  return (
    <div className={`story-page story-page--${variant}`} data-theme={theme}>
      <PageContainer>
        <motion.div className="story-head" {...reveal(staggerParent)}>
          <motion.span variants={fadeIn} className="story-index-numeral" aria-hidden="true">
            {numeral}
          </motion.span>

          <div className="story-head-body">
            <motion.p variants={fadeUp} className="story-label">
              {storyLabel}
            </motion.p>
            <motion.h1 variants={fadeUp}>{title}</motion.h1>
            {questions?.length > 0 && (
              <motion.ul variants={fadeUp} className="story-questions">
                {questions.map((q) => (
                  <li key={q}>{q}</li>
                ))}
              </motion.ul>
            )}
          </div>

          {isSpotlight && (
            <motion.div variants={scaleIn} className="story-spotlight-stat">
              <p className="story-spotlight-value">{highlightStat.value}</p>
              <p className="story-spotlight-label">{highlightStat.label}</p>
              {highlightStat.detail && (
                <p className="story-spotlight-detail">{highlightStat.detail}</p>
              )}
            </motion.div>
          )}
        </motion.div>

        <motion.div {...reveal(fadeUp)}>
          <FilterBar filters={filters} />
        </motion.div>

        {isTicker && kpis?.length > 0 ? (
          <motion.div {...reveal(fadeIn)} className="kpi-ticker" aria-label="Key figures">
            <div className="kpi-ticker-track">
              {[...kpis, ...kpis].map((tile, i) => (
                <div className={`kpi-ticker-item kpi-tile-badge--${tile.accent ?? "blue"}`} key={i}>
                  <span className="kpi-ticker-value">{tile.value}</span>
                  <span className="kpi-ticker-label">{tile.label}</span>
                </div>
              ))}
            </div>
          </motion.div>
        ) : (
          <motion.div {...reveal(staggerParent)}>
            <KpiRow tiles={kpis} />
          </motion.div>
        )}

        {isLadder && (
          <motion.div {...reveal(staggerParent)} className="ranking-ladder" role="list">
            {ranking.map((rung, i) => (
              <motion.div
                variants={slideFromRight}
                role="listitem"
                className={`ranking-rung${rung.highlight ? " ranking-rung--highlight" : ""}`}
                key={rung.label}
              >
                <span className="ranking-rung-position">{i + 1}</span>
                <span className="ranking-rung-label">{rung.label}</span>
                <span className="ranking-rung-value">{rung.value}</span>
                {rung.detail && <span className="ranking-rung-detail">{rung.detail}</span>}
              </motion.div>
            ))}
          </motion.div>
        )}
      </PageContainer>

      {/* Wider band than the prose column above -- a Superset dashboard's
          12-column grid plus its own filter sidebar needs more room than
          the ~68ch narrative text, so this breaks out to its own max-width
          instead of sharing PageContainer's narrower one (same pattern as
          Home.jsx's full-bleed hero banner). */}
      <motion.div {...reveal(fadeIn)} className="story-dashboard-band">
        <div className="story-dashboard-slot">
          {dashboard ?? (
            <p className={isHorizon ? "horizon-note" : "placeholder-note"}>
              {isHorizon
                ? "This story's dashboard is still being built -- check back once the combined view is live."
                : "Embedded dashboard goes here — not yet built."}
            </p>
          )}
        </div>
      </motion.div>

      <PageContainer>
        {narrative?.length > 0 ? (
          <motion.div {...reveal(staggerParent)} className="story-narrative">
            {narrative.map((paragraph, i) => (
              <motion.p variants={fadeUp} key={i}>
                {paragraph}
              </motion.p>
            ))}
          </motion.div>
        ) : (
          <motion.p {...reveal(fadeIn)} className={isHorizon ? "horizon-note" : "placeholder-note"}>
            {isHorizon
              ? "The write-up for this story is still in progress -- it'll bring the other 4 stories together once their combined view is built."
              : "Full narrative write-up goes here — not yet drafted."}
          </motion.p>
        )}

        {definitions?.length > 0 &&
          (isBlueprint ? (
            <motion.div {...reveal(staggerParent)} className="blueprint-grid">
              {definitions.map((d, i) => (
                <motion.div variants={fadeUp} className="blueprint-card" key={d.term}>
                  <span className="blueprint-card-index">{String(i + 1).padStart(2, "0")}</span>
                  <p className="definition-term">{d.term}</p>
                  <p className="definition-text">{d.text}</p>
                </motion.div>
              ))}
            </motion.div>
          ) : (
            <motion.div {...reveal(staggerParent)} className="definitions-grid">
              {definitions.map((d) => (
                <motion.div variants={fadeUp} className="card definition-card" key={d.term}>
                  <p className="definition-term">{d.term}</p>
                  <p className="definition-text">{d.text}</p>
                </motion.div>
              ))}
            </motion.div>
          ))}

        {limitations?.length > 0 && (
          <motion.div {...reveal(fadeUp)} className="limitations-note">
            <strong>Known limitations</strong>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </motion.div>
        )}

        {source && <p className="story-source-line">Source: {source}</p>}
      </PageContainer>
    </div>
  );
}
