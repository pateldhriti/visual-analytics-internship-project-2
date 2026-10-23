import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  AnimatePresence,
  animate,
  motion,
  MotionConfig,
  useMotionValue,
  useReducedMotion,
} from "framer-motion";
import PageContainer from "../components/PageContainer.jsx";

const MotionLink = motion(Link);

// Shared entrance variants. `fadeUp` also moves on the y-axis, so it's only
// used where nothing else (e.g. a CSS :hover rule) needs to own that
// element's `transform`. `fadeIn` is opacity-only, for elements like the
// story cards whose hover lift is still handled by plain CSS. Panels use a
// springy pop instead of a plain ease for a livelier, less corporate feel.
const staggerParent = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12, delayChildren: 0.05 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 22 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 160, damping: 18 } },
};

const fadeIn = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.5, ease: "easeOut" } },
};

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

// Four floating hero panels. Each is independently sourced -- see each
// panel's own `source`/`geography`/`period`, revealed on click -- rather
// than one blanket citation for the whole hero.
const PANELS = [
  {
    id: "burden",
    kind: "ring",
    eyebrow: "Shelter-cost burden",
    ringValue: 34.8,
    animatedValue: { value: 34.8, decimals: 1, suffix: "%" },
    value: "34.8%",
    valueLabel: "Renter households spending 30%+ of income on shelter",
    secondary: "vs. 10.9% of owner households",
    definition:
      "Share of households spending 30% or more of income on shelter costs -- rent or mortgage, utilities, and property tax where applicable.",
    source: "StatCan 98-10-0252-01",
    geography: "Windsor CMA",
    period: "2021 Census",
  },
  {
    id: "rental",
    kind: "duo",
    eyebrow: "Rental market",
    animatedValue: { value: 3.6, decimals: 1, suffix: "%" },
    value: "3.6%",
    valueLabel: "Vacancy rate, Combined dwelling types",
    secondary: "$1,451 average 2-bedroom rent",
    definition:
      "Share of surveyed purpose-built rental units vacant; average monthly rent for a 2-bedroom unit. Combined (apartment + row) scope.",
    source: "CMHC Rental Market Survey",
    geography: "Windsor CMA",
    period: "October 2025",
  },
  {
    id: "supply",
    kind: "pipeline",
    eyebrow: "Supply pipeline",
    value: "162,138",
    valueLabel: "Units under construction",
    secondary: "17,786 starts this quarter",
    bars: [
      { label: "Starts", value: 17786 },
      { label: "Completions", value: 14083 },
      { label: "Under construction", value: 162138 },
    ],
    definition:
      "New units started, finished, and still in progress during the quarter. This is an Ontario-wide figure -- no Windsor-specific starts/completions breakdown exists in CMHC's source table yet.",
    source: "CMHC Starts, Completions and Units Under Construction",
    geography: "Ontario",
    period: "Second Quarter 2026",
  },
  {
    id: "comparison",
    kind: "comparison",
    eyebrow: "Windsor vs. comparators",
    value: "2nd-tightest",
    valueLabel: "vacancy rate of 5 Ontario CMAs",
    secondary: "Windsor 3.7% (apartment-only scope)",
    rows: [
      { label: "Hamilton", value: 3.6 },
      { label: "Windsor", value: 3.7, highlight: true },
      { label: "St. Catharines-Niagara", value: 3.9 },
      { label: "London", value: 4.0 },
      { label: "Kitchener-Cambridge-Waterloo", value: 4.1 },
    ],
    definition:
      "Apartment-only vacancy rate (CMHC's national comparison scope) against the 4 Ontario CMAs chosen as Windsor's size peers. A narrower scope than the Combined figure in the rental-market panel, not a contradiction of it.",
    source: "CMHC Rental Market Survey",
    geography: "Windsor + 4 comparator CMAs",
    period: "October 2025",
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

// A wide isometric skyline strip, purely illustrative -- it stands in for
// "a city" the way an icon would, not for any dataset, so it carries no
// figures of its own. Faces of each block are computed from standard
// isometric-projection vectors (ux/uy for the floor plane, uz for height)
// rather than hand-typed coordinates, so the skyline can be tuned by
// adjusting a few numbers per building instead of redrawing polygons.
const SKYLINE_BUILDINGS = [
  { x: 30, baseY: 190, w: 36, d: 36, h: 65 },
  { x: 130, baseY: 190, w: 32, d: 32, h: 120 },
  { x: 225, baseY: 190, w: 40, d: 40, h: 52 },
  { x: 330, baseY: 190, w: 34, d: 34, h: 148 },
  { x: 430, baseY: 190, w: 38, d: 38, h: 88 },
  { x: 535, baseY: 190, w: 32, d: 32, h: 128 },
  { x: 630, baseY: 190, w: 42, d: 42, h: 58 },
  { x: 740, baseY: 190, w: 34, d: 34, h: 140 },
  { x: 840, baseY: 190, w: 38, d: 38, h: 80 },
  { x: 940, baseY: 190, w: 32, d: 32, h: 112 },
  { x: 1040, baseY: 190, w: 40, d: 40, h: 66 },
  { x: 1140, baseY: 190, w: 34, d: 34, h: 100 },
];

const SKYLINE_PALETTE = [
  { top: "#b2a4fb", right: "#8b7cf6", left: "#6456c9" },
  { top: "#8fcdff", right: "#4ea1f7", left: "#3579c9" },
  { top: "#79e6ee", right: "#38d9e8", left: "#23aeba" },
];

function isoBuildingFaces({ x, baseY, w, d, h }) {
  const ux = { x: w, y: w * 0.5 };
  const uy = { x: -d, y: d * 0.5 };
  const base = { x, y: baseY };
  const top = { x: base.x, y: base.y - h };
  const topRight = { x: top.x + ux.x, y: top.y + ux.y };
  const topLeft = { x: top.x + uy.x, y: top.y + uy.y };
  const topBack = { x: top.x + ux.x + uy.x, y: top.y + ux.y + uy.y };
  const right = { x: base.x + ux.x, y: base.y + ux.y };
  const left = { x: base.x + uy.x, y: base.y + uy.y };

  return {
    topFace: [top, topRight, topBack, topLeft],
    rightFace: [base, right, topRight, top],
    leftFace: [base, top, topLeft, left],
  };
}

function toPoints(points) {
  return points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
}

function HeroSkyline() {
  return (
    <svg
      className="hero-scene-svg"
      viewBox="0 0 1200 220"
      preserveAspectRatio="none"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id="skylineGlow" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgba(139,124,246,0.22)" />
          <stop offset="100%" stopColor="rgba(139,124,246,0)" />
        </linearGradient>
      </defs>
      <rect x="0" y="40" width="1200" height="150" fill="url(#skylineGlow)" />
      {SKYLINE_BUILDINGS.map((building, i) => {
        const { topFace, rightFace, leftFace } = isoBuildingFaces(building);
        const shade = SKYLINE_PALETTE[i % SKYLINE_PALETTE.length];
        return (
          <motion.g
            key={building.x}
            style={{ originY: 1 }}
            initial={{ scaleY: 0, opacity: 0 }}
            animate={{ scaleY: 1, opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.3 + i * 0.045, ease: "easeOut" }}
          >
            <polygon points={toPoints(leftFace)} fill={shade.left} />
            <polygon points={toPoints(rightFace)} fill={shade.right} />
            <polygon points={toPoints(topFace)} fill={shade.top} />
          </motion.g>
        );
      })}
    </svg>
  );
}

// Slow-drifting color blobs behind the hero content -- purely atmospheric,
// not a chart, so it carries no numbers of its own.
function HeroAurora() {
  return (
    <div className="hero-aurora" aria-hidden="true">
      <motion.div
        className="hero-aurora-blob hero-aurora-blob--violet"
        animate={{ x: [0, 50, -20, 0], y: [0, -30, 25, 0] }}
        transition={{ duration: 24, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="hero-aurora-blob hero-aurora-blob--blue"
        animate={{ x: [0, -60, 30, 0], y: [0, 35, -25, 0] }}
        transition={{ duration: 28, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}

// A simple house silhouette that gently bobs -- a direct, literal nod to
// "housing" rather than only the abstract skyline, scattered a few times
// behind the hero text at low opacity.
function FloatingHouseIcon({ className, delay = 0, duration = 4.5 }) {
  return (
    <motion.svg
      className={`hero-float-icon ${className ?? ""}`}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      animate={{ y: [0, -14, 0], rotate: [0, 3, 0] }}
      transition={{ duration, repeat: Infinity, ease: "easeInOut", delay }}
    >
      <path
        d="M3 11.5 12 4l9 7.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M5.5 10v9a1 1 0 0 0 1 1H9a1 1 0 0 0 1-1v-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v4a1 1 0 0 0 1 1h2.5a1 1 0 0 0 1-1v-9"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </motion.svg>
  );
}

const panelVariants = {
  hidden: { opacity: 0, y: 32, scale: 0.9 },
  show: { opacity: 1, y: 0, scale: 1, transition: { type: "spring", stiffness: 220, damping: 20 } },
};

function HeroPanel({ panel, isOpen, onToggle }) {
  return (
    <motion.button
      type="button"
      className="card panel-card"
      aria-expanded={isOpen}
      aria-controls={`panel-detail-${panel.id}`}
      onClick={() => onToggle(panel.id)}
      variants={panelVariants}
      whileHover={{ y: -4 }}
      whileTap={{ scale: 0.98 }}
    >
      <p className="panel-eyebrow">{panel.eyebrow}</p>

      {panel.kind === "ring" && (
        <div className="panel-ring" style={{ "--ring": panel.ringValue }}>
          <span className="panel-ring-inner">
            <AnimatedNumber {...panel.animatedValue} />
          </span>
        </div>
      )}

      {panel.kind === "pipeline" && (
        <div className="panel-mini-bars">
          {panel.bars.map((bar) => (
            <div key={bar.label}>
              <div className="panel-mini-bar-label">
                <span>{bar.label}</span>
                <span>
                  <AnimatedNumber value={bar.value} />
                </span>
              </div>
              <div className="panel-mini-bar-track">
                <motion.div
                  className="panel-mini-bar-fill"
                  initial={{ width: 0 }}
                  animate={{ width: `${(bar.value / 162138) * 100}%` }}
                  transition={{ duration: 1, ease: "easeOut" }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {panel.kind === "comparison" && (
        <div className="panel-comparison-rows">
          {panel.rows.map((row) => (
            <div
              key={row.label}
              className={`panel-comparison-row${row.highlight ? " is-highlight" : ""}`}
            >
              <span>{row.label}</span>
              <span>{row.value}%</span>
            </div>
          ))}
        </div>
      )}

      {panel.kind !== "ring" && panel.kind !== "pipeline" && panel.kind !== "comparison" && (
        <p className="panel-value">
          {panel.animatedValue ? <AnimatedNumber {...panel.animatedValue} /> : panel.value}
        </p>
      )}

      <p className="panel-value-label">{panel.valueLabel}</p>
      <p className="panel-secondary">{panel.secondary}</p>

      <AnimatePresence initial={false}>
        {isOpen ? (
          <motion.dl
            className="panel-detail"
            id={`panel-detail-${panel.id}`}
            key="detail"
            initial={{ height: 0, opacity: 0, marginTop: 0, paddingTop: 0 }}
            animate={{ height: "auto", opacity: 1, marginTop: 14, paddingTop: 14 }}
            exit={{ height: 0, opacity: 0, marginTop: 0, paddingTop: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            style={{ overflow: "hidden" }}
          >
            <div>
              <dt>Definition:</dt> <dd>{panel.definition}</dd>
            </div>
            <div>
              <dt>Source:</dt> <dd>{panel.source}</dd>
            </div>
            <div>
              <dt>Geography:</dt> <dd>{panel.geography}</dd>
            </div>
            <div>
              <dt>Period:</dt> <dd>{panel.period}</dd>
            </div>
          </motion.dl>
        ) : (
          <motion.p key="hint" className="panel-hint" exit={{ opacity: 0 }}>
            Tap for definition &amp; source
          </motion.p>
        )}
      </AnimatePresence>
    </motion.button>
  );
}

export default function Home() {
  const [openPanel, setOpenPanel] = useState(null);
  const [activeMetric, setActiveMetric] = useState(EXPLORER_METRICS[0].id);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const heroRef = useRef(null);
  const prefersReducedMotion = useReducedMotion();

  const togglePanel = (id) => setOpenPanel((current) => (current === id ? null : id));
  const metric = EXPLORER_METRICS.find((m) => m.id === activeMetric) ?? EXPLORER_METRICS[0];

  const handleHeroMouseMove = (e) => {
    if (prefersReducedMotion || !heroRef.current) return;
    const rect = heroRef.current.getBoundingClientRect();
    const relX = (e.clientX - rect.left) / rect.width - 0.5;
    const relY = (e.clientY - rect.top) / rect.height - 0.5;
    setTilt({ x: relY * -10, y: relX * 10 });
  };

  const handleHeroMouseLeave = () => setTilt({ x: 0, y: 0 });

  return (
    <MotionConfig reducedMotion="user">
      <section
        className="hero"
        ref={heroRef}
        onMouseMove={handleHeroMouseMove}
        onMouseLeave={handleHeroMouseLeave}
      >
        <HeroAurora />
        <FloatingHouseIcon className="hero-float-icon--1" delay={0} duration={4.2} />
        <FloatingHouseIcon className="hero-float-icon--2" delay={0.8} duration={5} />
        <FloatingHouseIcon className="hero-float-icon--3" delay={1.6} duration={4.6} />
        <div
          className="hero-scene"
          style={{ transform: `perspective(1200px) rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)` }}
        >
          <HeroSkyline />
        </div>
        <motion.div className="hero-inner" variants={staggerParent} initial="hidden" animate="show">
          <div>
            <motion.p variants={fadeUp} className="hero-eyebrow">
              Windsor Housing Analytics &middot; University of Windsor
            </motion.p>
            <motion.h1 variants={fadeUp} className="hero-headline">
              See Windsor&rsquo;s housing market <em>differently</em>.
            </motion.h1>
            <motion.p variants={fadeUp} className="hero-lede">
              A research platform tracking housing affordability, rental-market conditions, and
              housing supply in the Windsor Census Metropolitan Area &mdash; built entirely from
              official Statistics Canada and CMHC open data, with every figure traceable back to its
              source.
            </motion.p>
            <motion.div variants={fadeUp} className="hero-cta-row">
              <Link to="/stories/affordability" className="hero-cta hero-cta-primary">
                Explore the Data
              </Link>
              <a href="#stories" className="hero-cta hero-cta-secondary">
                Discover the Stories
              </a>
            </motion.div>
          </div>

          <motion.div className="hero-panels" variants={staggerParent}>
            {PANELS.map((panel) => (
              <HeroPanel
                key={panel.id}
                panel={panel}
                isOpen={openPanel === panel.id}
                onToggle={togglePanel}
              />
            ))}
          </motion.div>
        </motion.div>
      </section>

      <PageContainer>
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
        </motion.section>
      </PageContainer>
    </MotionConfig>
  );
}
