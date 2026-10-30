import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, animate, motion, MotionConfig, useMotionValue } from "framer-motion";
import PageContainer from "../components/PageContainer.jsx";
import KpiRow from "../components/KpiRow.jsx";
import { staggerParent, fadeUp, fadeIn } from "../lib/motion.js";

const MotionLink = motion(Link);

// Counts up from 0 to a real, already-verified number -- it never displays
// a value that wasn't passed in as real data. Re-triggers whenever `value`
// changes (e.g. switching metrics in the data explorer).
function AnimatedNumber({ value, decimals = 0, prefix = "", suffix = "" }) {
  const motionValue = useMotionValue(0);
  const format = (n) =>
    `${prefix}${decimals > 0 ? n.toFixed(decimals) : Math.round(n).toLocaleString()}${suffix}`;
  const [display, setDisplay] = useState(() => format(0));

  useEffect(() => {
    const controls = animate(motionValue, value, {
      duration: 1.3,
      ease: "easeOut",
      onUpdate: (latest) => setDisplay(format(latest)),
    });
    return () => controls.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, decimals, prefix, suffix]);

  return <>{display}</>;
}

// Small icon set shared by the story cards -- same glyph family as the
// sidebar (components/Sidebar.jsx), duplicated here rather than imported
// across an unrelated component boundary.
const STORY_ICONS = {
  affordability: (
    <path d="M10 2v16M14 5.5c0-1.4-1.6-2.5-4-2.5s-4 1.1-4 2.5 1.6 2.3 4 2.7c2.4.4 4 1.3 4 2.8s-1.6 2.5-4 2.5-4-1.1-4-2.5" />
  ),
  rental: <path d="M13 3a4 4 0 1 1 0 8 4 4 0 0 1 0-8ZM2 17l5-5 2.5 2.5L15 9" />,
  supply: <path d="M3 17V9l4-2v10M9 17V5l4-2v14M15 17V9l2-1v9M3 17h14" />,
  comparison: (
    <path d="M10 2v15M4 6l-2 5a3 3 0 0 0 6 0l-2-5Zm12 0-2 5a3 3 0 0 0 6 0l-2-5ZM3 6h4M13 6h4M6 17h8" />
  ),
  integrated: <path d="m10 2 8 4-8 4-8-4 8-4ZM2 10l8 4 8-4M2 14l8 4 8-4" />,
};

function StoryIcon({ name }) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {STORY_ICONS[name]}
    </svg>
  );
}

// Every figure below is real and independently verified elsewhere in this
// project (docs/story1_validation.md, docs/kpi_catalogue.md,
// docs/comparator_cmas_justification.md) -- nothing here is a placeholder
// or a sample value copied from a reference design.
const STORIES = [
  {
    to: "/stories/affordability",
    label: "Story 1",
    title: "Who faces the greatest housing affordability pressure?",
    blurb: "Shelter-cost burden by tenure, income band, and household type.",
    icon: "affordability",
    accent: "rose",
  },
  {
    to: "/stories/rental-market",
    label: "Story 2",
    title: "What is happening in Windsor's rental market?",
    blurb: "Rent, vacancy, rental stock, and turnover by zone and unit type.",
    icon: "rental",
    accent: "blue",
  },
  {
    to: "/stories/housing-supply",
    label: "Story 3",
    title: "What does housing supply look like?",
    blurb: "Starts and completions, and which dwelling types contribute most.",
    icon: "supply",
    accent: "teal",
  },
  {
    to: "/stories/comparison",
    label: "Story 4",
    title: "How does Windsor compare?",
    blurb: "Rental indicators against similar-sized Canadian CMAs.",
    icon: "comparison",
    accent: "violet",
  },
  {
    to: "/stories/integrated-analysis",
    label: "Story 5",
    title: "How do affordability, rental conditions, and supply fit together?",
    blurb: "A combined read across all four stories -- in progress, not yet built.",
    icon: "integrated",
    accent: "blue",
  },
];

// Flat KPI row directly below the banner -- same KpiRow component every
// story page uses, each value real and traced to the panel it replaces.
const HOME_KPIS = [
  {
    label: "Renter households spending 30%+ on shelter",
    value: "34.8%",
    accent: "rose",
    trend: "up",
    caption: "Windsor CMA, 2021 Census",
  },
  {
    label: "Average 2-bedroom rent",
    value: "$1,451",
    accent: "blue",
    trend: "up",
    caption: "Windsor CMA, October 2025",
  },
  {
    label: "New housing starts",
    value: "17,786",
    accent: "teal",
    trend: "up",
    caption: "Ontario, Second Quarter 2026",
  },
  {
    label: "Windsor apartment vacancy rank",
    value: "2nd-tightest",
    accent: "violet",
    trend: "flat",
    caption: "of 5 Ontario CMAs, October 2025",
  },
];

// Data-explorer preview: a metric selector switching between 3 real,
// already-verified datasets -- not a decorative chart. Reuses the site's
// existing native bar-chart styling.
const EXPLORER_METRICS = [
  {
    id: "burden",
    label: "Shelter-cost burden",
    max: 40,
    unit: "%",
    rows: [
      { label: "Renter", value: 34.8 },
      { label: "Owner", value: 10.9 },
    ],
    caption:
      "StatCan 98-10-0252-01, Windsor CMA, 2021 Census -- reproduced and independently verified against StatCan's own published Census Profile rate.",
    to: "/stories/affordability",
  },
  {
    id: "supply",
    label: "Supply pipeline",
    max: 162138,
    unit: "units",
    rows: [
      { label: "Starts", value: 17786 },
      { label: "Completions", value: 14083 },
      { label: "Under construction", value: 162138 },
    ],
    caption:
      "CMHC Starts, Completions and Units Under Construction, Ontario, Second Quarter 2026 -- Ontario-wide only, no Windsor-specific figure yet.",
    to: "/stories/housing-supply",
  },
  {
    id: "comparison",
    label: "Comparator vacancy",
    max: 4.5,
    unit: "%",
    rows: [
      { label: "Hamilton", value: 3.6 },
      { label: "Windsor", value: 3.7 },
      { label: "St. Catharines-Niagara", value: 3.9 },
      { label: "London", value: 4.0 },
      { label: "Kitchener-Cambridge-Waterloo", value: 4.1 },
    ],
    caption:
      "CMHC Rental Market Survey, apartment-only scope, October 2025 -- Windsor and 4 size-comparable Ontario CMAs.",
    to: "/stories/comparison",
  },
];

// Real banner photo -- aerial view of Windsor, Ontario (2025), by WMrapids
// on Wikimedia Commons, released CC0 (public domain, no attribution
// required). Credited on the Sources page anyway, consistent with the
// team's practice of citing third-party media even when not legally
// required. Replaces the earlier illustrated isometric skyline.
const BANNER_PHOTO = {
  src: "/images/windsor-skyline.jpg",
  alt: "Aerial view of Windsor, Ontario, with the Detroit River and Detroit skyline in the background",
};

export default function Home() {
  const [activeMetric, setActiveMetric] = useState(EXPLORER_METRICS[0].id);
  const metric = EXPLORER_METRICS.find((m) => m.id === activeMetric) ?? EXPLORER_METRICS[0];

  return (
    <MotionConfig reducedMotion="user">
      <div className="story-page home-page" data-theme="neighbourhood">
        {/* A 2-column editorial masthead -- headline text on plain paper,
          the real photo held in its own bordered frame like a captioned
          newspaper photograph, not a full-bleed marketing banner with
          text scrimmed over it. Fully light: nothing here is a dark
          surface, the photo is the only non-paper-colored element. */}
        <section className="hero-banner">
          <PageContainer>
            <div className="hero-banner-grid">
              <motion.div variants={staggerParent} initial="hidden" animate="show">
                <motion.p variants={fadeUp} className="hero-eyebrow">
                  Windsor Housing Analytics &middot; University of Windsor
                </motion.p>
                <motion.h1 variants={fadeUp} className="hero-headline">
                  Understanding housing in <em>Windsor</em> and beyond.
                </motion.h1>
                <motion.p variants={fadeUp} className="hero-lede">
                  An integrated analysis of housing affordability, rental market, supply, and
                  comparison conditions in the Windsor Census Metropolitan Area &mdash; built
                  entirely from official Statistics Canada and CMHC open data, with every figure
                  traceable back to its source.
                </motion.p>
                <motion.div variants={fadeUp} className="hero-cta-row">
                  <Link to="/stories/affordability" className="hero-cta hero-cta-primary">
                    Explore the Data
                  </Link>
                  <a href="#stories" className="hero-cta hero-cta-secondary">
                    Discover the Stories &rarr;
                  </a>
                </motion.div>
              </motion.div>

              <motion.figure
                className="hero-banner-figure"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.7, ease: "easeOut", delay: 0.15 }}
              >
                <img className="hero-banner-photo" src={BANNER_PHOTO.src} alt={BANNER_PHOTO.alt} />
                <figcaption className="hero-banner-caption">
                  Windsor, Ontario &mdash; aerial view
                </figcaption>
              </motion.figure>
            </div>
          </PageContainer>
        </section>

        <PageContainer>
          <KpiRow tiles={HOME_KPIS} />

          <motion.section
            className="section"
            id="stories"
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-100px" }}
            variants={staggerParent}
          >
            <motion.div variants={fadeUp} className="section-heading">
              <h2>Explore the research stories</h2>
            </motion.div>
            <motion.div className="story-grid" variants={staggerParent}>
              {STORIES.map((story) => (
                <MotionLink
                  to={story.to}
                  className="card story-card card--hoverable"
                  key={story.to}
                  variants={fadeIn}
                >
                  <span className={`story-card-icon kpi-tile-badge--${story.accent}`}>
                    <StoryIcon name={story.icon} />
                  </span>
                  <p className="story-label">{story.label}</p>
                  <h3>{story.title}</h3>
                  <p>{story.blurb}</p>
                  <span className="story-card-arrow">Read the story &rarr;</span>
                </MotionLink>
              ))}
            </motion.div>
          </motion.section>

          <motion.section
            className="section"
            id="explorer"
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-100px" }}
            variants={staggerParent}
          >
            <motion.div variants={fadeUp} className="section-heading">
              <h2>Dig into the data yourself</h2>
              <p className="section-note">Pick a metric &mdash; every dataset here is real</p>
            </motion.div>
            <motion.div variants={fadeUp} className="card chart-preview-card">
              <div className="metric-selector" role="group" aria-label="Choose a metric to preview">
                {EXPLORER_METRICS.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    className={`metric-btn${m.id === activeMetric ? " is-active" : ""}`}
                    aria-pressed={m.id === activeMetric}
                    onClick={() => setActiveMetric(m.id)}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
              <AnimatePresence mode="wait">
                <motion.div
                  className="bar-chart"
                  key={metric.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.25, ease: "easeOut" }}
                >
                  {metric.rows.map((row) => (
                    <div className="bar-row" key={row.label}>
                      <span className="bar-row-label">{row.label}</span>
                      <span className="bar-track">
                        <motion.span
                          className="bar-fill"
                          initial={{ width: 0 }}
                          animate={{ width: `${(row.value / metric.max) * 100}%` }}
                          transition={{ type: "spring", stiffness: 120, damping: 20 }}
                        />
                      </span>
                      <span className="bar-row-value">
                        <AnimatedNumber
                          value={row.value}
                          decimals={metric.unit === "%" ? 1 : 0}
                          suffix={metric.unit === "%" ? "%" : ""}
                        />
                      </span>
                    </div>
                  ))}
                </motion.div>
              </AnimatePresence>
              <p className="chart-preview-caption">
                {metric.caption} Full breakdown on <Link to={metric.to}>{metric.label}</Link>.
              </p>
            </motion.div>
          </motion.section>

          <motion.section
            className="section"
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-100px" }}
            variants={fadeUp}
          >
            <div className="section-heading">
              <h2>Data provenance</h2>
            </div>
            <div className="methodology-band">
              <p>
                Every figure on this site traces back to an official Statistics Canada or CMHC
                download. Raw files are kept separate from processed data, loaded into PostgreSQL
                through documented Python ETL scripts, and queried through SQL views that Apache
                Superset builds charts from. See the{" "}
                <Link to="/methodology">full methodology page</Link> for the stack, data sources,
                and known limitations.
              </p>
              <ul className="source-list">
                <li>Census Profile, 2021 &mdash; Statistics Canada</li>
                <li>Shelter-cost-to-income ratio by tenure &mdash; Statistics Canada</li>
                <li>Rental Market Survey, Windsor &amp; Canada &mdash; CMHC</li>
                <li>Starts, Completions and Units Under Construction &mdash; CMHC</li>
              </ul>
            </div>
          </motion.section>
        </PageContainer>
      </div>
    </MotionConfig>
  );
}
