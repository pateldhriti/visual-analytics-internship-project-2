import StoryPage from "../components/StoryPage.jsx";
import SupersetGuestEmbed from "../components/SupersetGuestEmbed.jsx";

// Narrative paragraphs reused verbatim from docs/story1_narrative_v1.md's own
// draft text -- real, verified figures (corrected via docs/story1_validation.md),
// not written fresh here.
const NARRATIVE = [
  "In Windsor, renters hit the 30%-of-income shelter-cost line far more often than owners do - " +
    "34.8% of renter households spend 30% or more of their income on shelter, compared with 10.9% " +
    "of owner households. That's not a small gap: a renter household is more than three times as " +
    "likely to be cost-burdened as an owner household in the same city. This figure has been " +
    "independently reproduced from two different Statistics Canada products and confirmed to match " +
    "exactly - not an estimate, a verified number.",
  "Splitting owners and renters further by household type sharpens the picture without changing " +
    "its shape. Non-census-family one-person households carry the heaviest burden at 32.9%, " +
    "followed closely by non-census-family households overall at 31.1% and one-parent families at " +
    "23.3% - all well above Windsor's citywide baseline of 17.5%. The households most exposed " +
    "to housing-cost pressure tend to be the ones without a second income or a shared-earner " +
    "structure to fall back on.",
  "Income tells a sharper version of the same story - sharper than first calculated. " +
    "Households earning under $10,000 a year are burdened at 93.1%, not the 73.6% originally " +
    "reported: that correction came from excluding households with no computable shelter-cost " +
    "ratio at all (zero or negative income, or an agricultural-operation dwelling) from the " +
    "denominator, the same adjustment StatCan's own published rate already makes. The lowest " +
    "income bracket isn't a close second to $10,000-$19,999 (76.5%) - it's clearly the most " +
    "burdened group in Windsor by a wide margin.",
  "Within the group spending 30% or more, most of the burden is severe rather than borderline: " +
    "91.2% of burdened households (26,210 of 28,745) are in the 30%-to-under-100% range, not just " +
    "barely over the line. The remaining 2,535 households (8.8%) aren't accounted for by any " +
    "sub-category StatCan publishes for this table - flagged honestly as an open data-quality " +
    "question, not assumed to be 100%+ spenders without a source for that label.",
];

const DEFINITIONS = [
  {
    term: "Shelter-cost-to-income ratio",
    text: "Share of household income spent on shelter costs -- rent or mortgage payments, utilities, and property tax where applicable.",
  },
  {
    term: "30% threshold",
    text: "StatCan's standard affordability line. Households spending 30% or more of income on shelter are considered cost-burdened.",
  },
  {
    term: "“Not applicable” households",
    text: "Households with no computable ratio at all -- zero or negative income, or an agricultural-operation dwelling. Excluded from the burden-rate denominator.",
  },
  {
    term: "Household type",
    text: "Census family structure (e.g. one-person, couple with/without children) -- 16 real categories, 2 label pairs disambiguated by StatCan's own member ID.",
  },
];

const LIMITATIONS = [
  "8.8% of burdened households (2,535 of 28,745) aren't accounted for by any StatCan sub-category this table publishes -- flagged openly, not assumed into any one bucket.",
  "This is a single 2021 Census snapshot, not a time series -- it can't show whether the burden is rising or falling over time.",
];

const FILTERS = [
  { label: "Geography", value: "Windsor CMA" },
  { label: "Period", value: "2021 Census" },
];

const KPIS = [
  { label: "Renter households cost-burdened", value: "34.8%", accent: "rose", trend: "up" },
  { label: "Owner households cost-burdened", value: "10.9%", accent: "blue", trend: "flat" },
  { label: "Burden rate, income under $10,000", value: "93.1%", accent: "violet", trend: "up" },
  { label: "Burdened households in severe range", value: "91.2%", accent: "teal", trend: "flat" },
];

export default function StoryAffordability() {
  return (
    <StoryPage
      storyLabel="Story 1"
      title="Who faces the greatest housing affordability pressure?"
      questions={[
        "How does shelter-cost burden vary by income group and household type?",
        "How different is the burden for renters and owners?",
      ]}
      filters={FILTERS}
      kpis={KPIS}
      variant="spotlight"
      theme="neighbourhood"
      highlightStat={{
        value: "93.1%",
        label: "burden rate, income under $10,000",
        detail: "the steepest of any income bracket in Windsor",
      }}
      dashboard={
        <SupersetGuestEmbed
          dashboard="story1"
          fallbackDashboardId={3}
          title="Story 1: Who faces the greatest affordability pressure? (Superset dashboard)"
        />
      }
      narrative={NARRATIVE}
      definitions={DEFINITIONS}
      limitations={LIMITATIONS}
      source="StatCan 98-10-0252-01, Shelter-cost-to-income ratio by tenure (Windsor CMA, 2021 Census) -- warehouse.fact_shelter_cost"
    />
  );
}
