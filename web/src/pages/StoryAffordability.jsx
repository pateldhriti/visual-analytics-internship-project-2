import StoryPage from "../components/StoryPage.jsx";
import StoryHighlights from "../components/StoryHighlights.jsx";
import SupersetGuestEmbed from "../components/SupersetGuestEmbed.jsx";
import { F, money, num, pct } from "../lib/figures.js";

// Text condensed from docs/story1_narrative_final.md. Every figure comes
// from the warehouse.v_story1_* views behind the Story 1 dashboard, through
// web/src/data/figures.json (etl/site_figures.py).
const S = F.s1;
const TIMES =
  ["", "as", "twice as", "three times as", "four times as"][S.renterTimesOwner] ??
  `${S.renterTimesOwner} times as`;

const INTRO =
  "A household is cost-burdened when it spends 30% or more of its income on shelter: rent or " +
  `mortgage, utilities and property tax. In the Windsor area, ${pct(S.burdenPct)} of households ` +
  `(${num(S.burdened)} of ${num(S.households)}) were over that line in the 2021 Census. This ` +
  "story looks at which households carry that burden.";

const NARRATIVE = [
  `Renters carry most of the burden. ${pct(S.renterPct)} of renter households spend 30% or more ` +
    `of their income on shelter, against ${pct(S.ownerPct)} of owner households, so a renter ` +
    `household is about ${TIMES} likely to be cost-burdened. Renters are only ` +
    `${pct(S.renterShareOfHouseholds, 0)} of Windsor's households but ` +
    `${pct(S.renterShareOfBurdened, 0)} of those over the line. Both rates match the Census ` +
    "Profile's own published figures for Windsor.",
  `Income is the strongest driver. ${pct(S.lowestBandPct)} of households earning under $10,000 ` +
    "are over the line, and the rate falls steadily as income rises, to " +
    `${pct(S.highestBandPct)} for households earning $100,000 or more. Households under $40,000 ` +
    `are ${pct(S.under40ShareOfHouseholds, 0)} of all households but ` +
    `${pct(S.under40ShareOfBurdened, 0)} of the burdened ones. The burden rate drops below the ` +
    `Windsor average only once income passes about ${money(S.belowAverageFromIncome)}.`,
  "Households with one income are most exposed. People living alone have the highest rate, " +
    `${pct(S.onePersonPct)}, and make up ${pct(S.onePersonShareOfBurdened, 0)} of all burdened ` +
    `households; one-parent families follow at ${pct(S.oneParentPct)}, while couples are at about ` +
    `${pct(S.couplePct, 0)}. Most burdened households spend 30% to under 100% of income on ` +
    `shelter; about ${num(S.hundredPlus)} report shelter costs equal to or above their whole ` +
    "income, often because their 2020 income was very low.",
];

const DEFINITIONS = [
  {
    term: "Shelter-cost-to-income ratio",
    text: "Share of household income spent on shelter: rent or mortgage payments, utilities, and property tax where applicable.",
  },
  {
    term: "30% threshold",
    text: "The standard affordability line used by Statistics Canada and CMHC. Households spending 30% or more of income on shelter are cost-burdened.",
  },
  {
    term: "100% or more",
    text: "Households whose shelter costs equal or exceed their income. Not published as its own row: it is the 30%+ total minus the 30%-to-under-100% band.",
  },
  {
    term: "“Not applicable” households",
    text: "Households with zero or negative income, or living on a farm they operate. They have no ratio and are left out of every burden rate.",
  },
];

const LIMITATIONS = [
  "One 2021 Census snapshot with 2020 incomes, so it can't show whether the burden is rising or falling. Pandemic benefits raised many low incomes in 2020.",
  `StatCan rounds counts to multiples of 5, so totals can differ slightly (${num(S.burdenedByTenure)} by tenure vs ${num(S.burdened)} overall).`,
  "The 100%-or-more group is derived rather than published, and often reflects very low reported income rather than very high shelter costs.",
];

const FILTERS = [
  { label: "Geography", value: "Windsor CMA" },
  { label: "Period", value: "2021 Census (2020 income)" },
];

const KPIS = [
  {
    label: "Renter households cost-burdened",
    value: pct(S.renterPct),
    accent: "rose",
    trend: "up",
  },
  {
    label: "Owner households cost-burdened",
    value: pct(S.ownerPct),
    accent: "blue",
    trend: "flat",
  },
  {
    label: "Burdened households who rent",
    value: pct(S.renterShareOfBurdened, 0),
    accent: "teal",
    trend: "up",
  },
  {
    label: "Burden rate, income under $10,000",
    value: pct(S.lowestBandPct),
    accent: "violet",
    trend: "up",
  },
];

// Story 5 findings that combine this story's data with another story's
// (docs/story5_combined_analysis.md).
const C = F.s5;
const CONNECTIONS = [
  {
    with: "With Story 2's rents",
    text: `An average Windsor 2-bedroom (${money(C.rent2Bed)}) needs a household income of about ${money(C.incomeNeeded)} under the 30% rule. The median renter household earned ${money(C.medianIncome)}, so about ${pct(C.cannotAffordPct, 0)} of renter households earn less than that.`,
  },
  {
    with: "With Story 4's comparison cities",
    text: `Windsor has the lowest rent of the five cities but also the second-lowest renter incomes: a year of 2-bedroom rent takes ${pct(C.rentShare, 0)} of the median renter's income${C.sameShareAs.length ? `, the same as ${C.sameShareAs.join(" and ")}` : ""}. Its share of renters spending 30% or more (${pct(C.burdenPct)}) is ${C.burdenLowest ? "still the lowest of the five" : "not the lowest of the five"}.`,
  },
];

export default function StoryAffordability() {
  return (
    <StoryPage
      storyLabel="Story 1"
      title="Who faces the greatest housing affordability pressure?"
      intro={INTRO}
      questions={[
        "How does shelter-cost burden vary by income group and household type?",
        "How different is the burden for renters and owners?",
      ]}
      filters={FILTERS}
      kpis={KPIS}
      variant="spotlight"
      theme="neighbourhood"
      highlightStat={{
        value: pct(S.renterPct),
        label: "of renter households spend 30%+ of income on shelter",
        detail: `against ${pct(S.ownerPct)} of owners`,
      }}
      highlights={<StoryHighlights only={["afford"]} here="/stories/affordability" />}
      dashboard={
        <SupersetGuestEmbed
          dashboard="story1"
          fallbackDashboardId="windsor-story-1"
          title="Story 1: Who faces the greatest affordability pressure? (Superset dashboard)"
        />
      }
      narrative={NARRATIVE}
      definitions={DEFINITIONS}
      limitations={LIMITATIONS}
      connections={CONNECTIONS}
      source="Statistics Canada, Table 98-10-0252-01, Shelter-cost-to-income ratio by tenure, Windsor CMA, 2021 Census"
    />
  );
}
