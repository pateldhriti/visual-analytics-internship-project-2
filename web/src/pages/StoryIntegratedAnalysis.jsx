import { motion } from "framer-motion";
import StoryPage from "../components/StoryPage.jsx";
import { staggerParent, fadeUp, reveal } from "../lib/motion.js";

// Story 5 pulls one headline conclusion from each of Stories 1-4 into one
// page. The images are static snapshots of the Story 5 Superset dashboard's
// charts (etl/render_story5_snapshots.py, drawn from the same warehouse
// views), and the insights match that dashboard's notes
// (etl/build_story5_dashboard.py) -- re-run both after a data refresh.
const SUPERSET_DASHBOARD_URL = "http://localhost:8088/superset/dashboard/8/";

const CONCLUSIONS = [
  {
    story: "Story 1 · Affordability",
    title: "Renters carry most of the burden",
    image: "/story5/story1-burdened-by-tenure.png",
    alt: "Donut chart: of 28,740 cost-burdened households, 15,735 (55%) rent and 13,005 (45%) own.",
    insights: [
      "Of the 28,740 Windsor households spending 30% or more of income on shelter, 15,735 (55%) rent and 13,005 (45%) own.",
      "Renters are only 28% of all households (45,280 of 164,220), so they make up about twice the share of the burdened that their numbers alone would suggest.",
    ],
  },
  {
    story: "Story 2 · Rental market",
    title: "Most rentals are in the city",
    image: "/story5/story2-rental-stock-by-zone.png",
    alt: "Donut chart of 19,883 rental units by zone: Zone 1 Centre 28%, Zone 3 East Outer 26%, Zone 4 West 18%, Zone 2 East Inner 10%, Zone 7 South Essex County 9%, Zone 6 North Essex County 6%, Zone 5 Amherstburg 3%.",
    insights: [
      "The four Windsor city zones hold 16,226 of the 19,883 purpose-built rental units (82%); Zone 1 - Centre alone has 5,509 (28%).",
      "The county zones are small and dearer: Amherstburg has 597 units (3%) and the highest average rent of any zone, $1,955 against $1,155 in Zone 1.",
    ],
  },
  {
    story: "Story 3 · Housing supply",
    title: "New supply has turned to apartments",
    image: "/story5/story3-starts-by-dwelling-type.png",
    alt: "Donut chart of 1,262 housing starts in 2025: apartments 752 (60%), singles 331 (26%), semis 90 (7%), row 89 (7%).",
    insights: [
      "Of 1,262 homes started in 2025, 752 (60%) were apartments, against 6% of starts in 2016.",
      "But total starts fell 41% from 2024's 2,157, so the new supply is a larger share of a smaller number.",
    ],
  },
  {
    story: "Story 4 · Comparison",
    title: "Windsor is the cheapest of its peers",
    image: "/story5/story4-rent-vs-peers.png",
    alt: "Bar chart of average 2-bedroom rent, October 2025: Windsor $1,454, St. Catharines-Niagara $1,527, London $1,651, Hamilton $1,656, Kitchener-Cambridge-Waterloo $1,832.",
    insights: [
      "Windsor's average 2-bedroom rent ($1,454) is the lowest of the five comparison cities: $73 below St. Catharines-Niagara and $378 below Kitchener-Cambridge-Waterloo.",
      "This is a ranking rather than parts of a whole, so it is shown as bars, not a pie.",
    ],
  },
];

const KPIS = [
  { label: "Burdened households who rent", value: "55%", accent: "rose" },
  { label: "Rental units in the 4 city zones", value: "82%", accent: "blue" },
  { label: "2025 starts that were apartments", value: "60%", accent: "teal" },
  { label: "2-bed rent, lowest of 5 cities", value: "$1,454", accent: "violet" },
];

const NARRATIVE = [
  "Put together, the four stories describe a market that is cheap by comparison but not affordable for the people who rent in it. Windsor has the lowest 2-bedroom rent of five similar Ontario cities, yet renters are 55% of the households spending 30% or more of their income on shelter while being only 28% of households. Story 1's income breakdown points to why: burden is concentrated in the lowest income bands, which suggests the pressure comes more from low incomes than from rents that are high by Ontario standards.",
  "Where renters live is fairly concentrated: 82% of purpose-built rental units are in the four Windsor city zones, which also have generally lower rents. New construction has moved toward apartments -- 60% of 2025 starts -- which is the kind of housing most renters use. The caution is volume: starts fell 41% in 2025 after a one-year surge, so the supply that could ease renter pressure is growing more slowly than the 2024 figures suggested.",
];

const LIMITATIONS = [
  "Each chart is one headline conclusion, not the full story -- the Story 1-4 pages and their dashboards have the filters and breakdowns behind each figure.",
  "Sources differ in date: affordability is from the 2021 Census, rental figures from CMHC's October 2025 survey, and starts from 2025. They are read side by side, not joined into one calculation.",
  "“Apartment and Other” starts include condominium apartments, not only purpose-built rentals.",
];

const FILTERS = [
  { label: "Geography", value: "Windsor CMA vs. comparator CMAs" },
  { label: "Scope", value: "Affordability + rental + supply + comparison" },
];

function ConclusionGrid() {
  return (
    <>
      <motion.div {...reveal(staggerParent)} className="conclusion-grid">
        {CONCLUSIONS.map((c) => (
          <motion.article variants={fadeUp} className="card conclusion-card" key={c.story}>
            <p className="conclusion-story">{c.story}</p>
            <h2 className="conclusion-title">{c.title}</h2>
            <img
              className="conclusion-image"
              src={c.image}
              alt={c.alt}
              loading="lazy"
              width="1350"
              height="840"
            />
            <ul className="conclusion-insights">
              {c.insights.map((insight) => (
                <li key={insight}>{insight}</li>
              ))}
            </ul>
          </motion.article>
        ))}
      </motion.div>
      <p className="conclusion-live-link">
        Chart images are snapshots of the{" "}
        <a href={SUPERSET_DASHBOARD_URL} target="_blank" rel="noreferrer">
          live Story 5 dashboard &nearr;
        </a>
      </p>
    </>
  );
}

export default function StoryIntegratedAnalysis() {
  return (
    <StoryPage
      storyLabel="Story 5"
      title="How do affordability, rental conditions, and supply fit together?"
      questions={[
        "Where shelter-cost burden is highest, is the rental market also the tightest?",
        "Does Windsor's housing-supply pipeline match where affordability pressure is greatest?",
        "Taken together, how does Windsor's overall housing situation compare with its peer CMAs?",
      ]}
      filters={FILTERS}
      kpis={KPIS}
      dashboard={<ConclusionGrid />}
      narrative={NARRATIVE}
      limitations={LIMITATIONS}
      variant="horizon"
      theme="neighbourhood"
      source="Story 1: StatCan 98-10-0252-01 (2021 Census); Story 2: CMHC Rental Market Survey, Oct-25; Story 3: CMHC via StatCan 34-10-0154-01; Story 4: CMHC Rental Market Survey, Oct-25 -- Superset dashboard 8"
    />
  );
}
