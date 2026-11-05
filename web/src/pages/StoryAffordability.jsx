import StoryPage from "../components/StoryPage.jsx";
import SupersetGuestEmbed from "../components/SupersetGuestEmbed.jsx";

// Text condensed from docs/story1_narrative_final.md. Every figure comes
// from the warehouse.v_story1_* views behind the Story 1 dashboard (id 3);
// re-check both after a data refresh.
const INTRO =
  "A household is cost-burdened when it spends 30% or more of its income on shelter: rent or " +
  "mortgage, utilities and property tax. In the Windsor area, 17.5% of households (28,745 of " +
  "164,220) were over that line in the 2021 Census. This story looks at which households carry " +
  "that burden.";

const NARRATIVE = [
  "Renters carry most of the burden. 34.8% of renter households spend 30% or more of their " +
    "income on shelter, against 10.9% of owner households, so a renter household is about three " +
    "times as likely to be cost-burdened. Renters are only 28% of Windsor's households but 55% of " +
    "those over the line. Both rates match the Census Profile's own published figures for Windsor.",
  "Income is the strongest driver. 93.1% of households earning under $10,000 are over the line, " +
    "and the rate falls steadily as income rises, to 1.5% for households earning $100,000 or more. " +
    "Households under $40,000 are 18% of all households but 60% of the burdened ones. The burden " +
    "rate drops below the Windsor average only once income passes about $60,000.",
  "Households with one income are most exposed. People living alone have the highest rate, " +
    "32.9%, and make up more than half of all burdened households; one-parent families follow at " +
    "23.3%, while couples are at about 9%. Most burdened households spend 30% to under 100% of " +
    "income on shelter; about 2,535 report shelter costs equal to or above their whole income, " +
    "often because their 2020 income was very low.",
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
  "StatCan rounds counts to multiples of 5, so totals can differ slightly (28,740 by tenure vs 28,745 overall).",
  "The 100%-or-more group is derived rather than published, and often reflects very low reported income rather than very high shelter costs.",
];

const FILTERS = [
  { label: "Geography", value: "Windsor CMA" },
  { label: "Period", value: "2021 Census (2020 income)" },
];

const KPIS = [
  { label: "Renter households cost-burdened", value: "34.8%", accent: "rose", trend: "up" },
  { label: "Owner households cost-burdened", value: "10.9%", accent: "blue", trend: "flat" },
  { label: "Burdened households who rent", value: "55%", accent: "teal", trend: "up" },
  { label: "Burden rate, income under $10,000", value: "93.1%", accent: "violet", trend: "up" },
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
        value: "34.8%",
        label: "of renter households spend 30%+ of income on shelter",
        detail: "against 10.9% of owners",
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
      source="Statistics Canada, Table 98-10-0252-01, Shelter-cost-to-income ratio by tenure, Windsor CMA, 2021 Census"
    />
  );
}
