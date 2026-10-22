import { Link } from "react-router-dom";
import PageContainer from "../components/PageContainer.jsx";

// Every figure here is real and independently verified elsewhere in this
// project (docs/story1_validation.md, docs/kpi_catalogue.md) -- nothing on
// this page is a placeholder or sample value.
const KPIS = [
  { value: "422,630", label: "Windsor CMA population", source: "StatCan, 2021 Census" },
  { value: "34.8%", label: "Renters spending 30%+ on shelter", source: "StatCan 98-10-0252-01" },
  { value: "3.6%", label: "Rental vacancy rate (Oct-25)", source: "CMHC RMS, Windsor" },
  { value: "$1,451", label: "Average 2-bedroom rent (Oct-25)", source: "CMHC RMS, Windsor" },
];

const STORIES = [
  {
    to: "/stories/affordability",
    label: "Story 1",
    title: "Who faces the greatest housing affordability pressure?",
    blurb: "Shelter-cost burden by tenure, income band, and household type.",
  },
  {
    to: "/stories/rental-market",
    label: "Story 2",
    title: "What is happening in Windsor's rental market?",
    blurb: "Rent, vacancy, rental stock, and turnover by zone and unit type.",
  },
  {
    to: "/stories/housing-supply",
    label: "Story 3",
    title: "What does housing supply look like?",
    blurb: "Starts and completions, and which dwelling types contribute most.",
  },
  {
    to: "/stories/comparison",
    label: "Story 4",
    title: "How does Windsor compare?",
    blurb: "Rental indicators against similar-sized Canadian CMAs.",
  },
];

// Owner vs. renter shelter-cost burden -- the real, independently reproduced
// figures from docs/story1_validation.md (matches StatCan's own published
// Census Profile rate exactly). A native bar, not a live Superset embed --
// see docs/superset_embedding_research.md for why that piece isn't built yet.
const BURDEN_PREVIEW = [
  { label: "Renter", value: 34.8 },
  { label: "Owner", value: 10.9 },
];

export default function Home() {
  return (
    <>
      <section className="hero">
        <PageContainer>
          <p className="hero-eyebrow">Windsor Housing Analytics &middot; University of Windsor</p>
          <h1>Housing affordability and market trends in Windsor, CMA</h1>
          <p className="hero-lede">
            A public, web-based look at housing affordability and housing-market conditions in the
            Windsor Census Metropolitan Area &mdash; built entirely from official Statistics Canada
            and CMHC open data, with every figure traceable back to its source.
          </p>
        </PageContainer>
      </section>

      <PageContainer>
        <section className="section">
          <div className="section-heading">
            <h2>Verified indicators</h2>
            <p className="section-note">Windsor CMA, most recent available period</p>
          </div>
          <div className="kpi-grid">
            {KPIS.map((kpi) => (
              <div className="card kpi-card" key={kpi.label}>
                <p className="kpi-value">{kpi.value}</p>
                <p className="kpi-label">{kpi.label}</p>
                <p className="kpi-source">{kpi.source}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="section">
          <div className="section-heading">
            <h2>Explore the research stories</h2>
          </div>
          <div className="story-grid">
            {STORIES.map((story) => (
              <Link to={story.to} className="card story-card card--hoverable" key={story.to}>
                <p className="story-label">{story.label}</p>
                <h3>{story.title}</h3>
                <p>{story.blurb}</p>
                <span className="story-card-arrow">Read the story &rarr;</span>
              </Link>
            ))}
          </div>
        </section>

        <section className="section">
          <div className="section-heading">
            <h2>Shelter-cost burden, by tenure</h2>
            <p className="section-note">Share spending 30%+ of income on shelter</p>
          </div>
          <div className="card chart-preview-card">
            <div className="bar-chart">
              {BURDEN_PREVIEW.map((row) => (
                <div className="bar-row" key={row.label}>
                  <span className="bar-row-label">{row.label}</span>
                  <span className="bar-track">
                    <span className="bar-fill" style={{ width: `${(row.value / 40) * 100}%` }} />
                  </span>
                  <span className="bar-row-value">{row.value}%</span>
                </div>
              ))}
            </div>
            <p className="chart-preview-caption">
              StatCan 98-10-0252-01, Windsor CMA, 2021 Census &mdash; reproduced and independently
              verified against StatCan&rsquo;s own published Census Profile rate. Full breakdown on{" "}
              <Link to="/stories/affordability">Story 1</Link>.
            </p>
          </div>
        </section>

        <section className="section">
          <div className="section-heading">
            <h2>Methodology, in brief</h2>
          </div>
          <div className="methodology-band">
            <p>
              Every figure on this site traces back to an official Statistics Canada or CMHC
              download. Raw files are kept separate from processed data, loaded into PostgreSQL
              through documented Python ETL scripts, and queried through SQL views that Apache
              Superset builds charts from. See the{" "}
              <Link to="/methodology">full methodology page</Link> for the stack, data sources, and
              known limitations.
            </p>
            <ul className="source-list">
              <li>Census Profile, 2021 &mdash; Statistics Canada</li>
              <li>Shelter-cost-to-income ratio by tenure &mdash; Statistics Canada</li>
              <li>Rental Market Survey, Windsor &amp; Canada &mdash; CMHC</li>
              <li>Starts, Completions and Units Under Construction &mdash; CMHC</li>
            </ul>
          </div>
        </section>
      </PageContainer>
    </>
  );
}
