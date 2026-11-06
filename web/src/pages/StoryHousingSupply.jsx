import StoryPage from "../components/StoryPage.jsx";
import SupersetGuestEmbed from "../components/SupersetGuestEmbed.jsx";

// Text condensed from docs/story3_narrative_final.md. Every figure comes
// from warehouse.v_story3_windsor_supply_annual and
// v_story3_windsor_supply_per_1000_households, the views behind the Story 3
// dashboard (id 7); re-check both after a data refresh.
const INTRO =
  "Rents and affordability depend partly on how many new homes are built. CMHC counts every " +
  "home whose construction starts and finishes in the Windsor area each month. This story " +
  "follows those counts from 2016 to 2025: how much Windsor is building, and what kind of housing.";

const NARRATIVE = [
  "Building rose, then fell back. Windsor started about 1,300 homes a year from 2016 to 2023. " +
    "In 2024 starts jumped to 2,157, the most in ten years (13.0 per 1,000 households), but " +
    "2025 fell back to 1,262, 41% fewer and about the level of 2016.",
  "The mix has turned to apartments. Only 6% of the homes started in 2016 were apartments; in " +
    "2025 it was 60% (752 of 1,262), while single-detached starts fell from 804 to 331. That is " +
    "the housing type most renters use, although the apartment count also includes condos.",
  "More homes are being finished than started. In 2023 and 2025 completions outpaced starts " +
    "(1,967 against 1,208, and 1,671 against 1,262) as earlier projects reached the end. Homes " +
    "under construction fell to 1,635 at the end of 2025, so the pipeline is getting smaller.",
  "What this means: Windsor is building more apartments, not more homes overall. Story 2 found " +
    "vacancy rising since 2022, consistent with these completions; with starts down again, that " +
    "flow of new homes is likely to slow unless building picks up.",
];

const DEFINITIONS = [
  {
    term: "Housing starts",
    text: "Homes whose construction began during the period (CMHC counts a start when the foundation is in place).",
  },
  {
    term: "Completions",
    text: "Homes finished during the period, usually one to three years after they started.",
  },
  {
    term: "Under construction",
    text: "Homes started but not yet finished at the end of the period: the pipeline of future completions.",
  },
  {
    term: "Apartment and other",
    text: "CMHC's category for apartment buildings of every kind, rental and condominium, plus a few other structure types.",
  },
];

const LIMITATIONS = [
  "Counts cover the whole Windsor area; they are not split by rental zone or by whether a home is for rent or for sale.",
  "“Per 1,000 households” uses the 2021 Census household count for every year, so it shows the trend rather than an exact rate.",
  "2026 is partial (January to September) and is not used for yearly comparisons.",
];

const FILTERS = [
  { label: "Geography", value: "Windsor CMA" },
  { label: "Period", value: "2016 to 2025" },
  { label: "Dwelling type", value: "All types" },
];

// Windsor CMA, 2025 -- the same figures as the Story 3 dashboard's cards.
const KPIS = [
  { label: "Homes started in Windsor, 2025", value: "1,262", accent: "teal", trend: "down" },
  { label: "Homes completed, 2025", value: "1,671", accent: "blue", trend: "flat" },
  { label: "Under construction at year end", value: "1,635", accent: "violet", trend: "flat" },
  { label: "Apartment share of 2025 starts", value: "60%", accent: "rose", trend: "up" },
];

export default function StoryHousingSupply() {
  return (
    <StoryPage
      storyLabel="Story 3"
      title="Is Windsor building enough housing?"
      intro={INTRO}
      questions={[
        "How many housing units are being started and completed, and which dwelling types contribute most?",
        "How can supply activity be interpreted alongside Windsor population and household context?",
      ]}
      filters={FILTERS}
      kpis={KPIS}
      variant="blueprint"
      theme="neighbourhood"
      narrative={NARRATIVE}
      definitions={DEFINITIONS}
      dashboard={
        <SupersetGuestEmbed
          dashboard="story3"
          fallbackDashboardId={7}
          title="Story 3: Is Windsor building enough housing? (Superset dashboard)"
        />
      }
      limitations={LIMITATIONS}
      source="CMHC Starts and Completions Survey, Windsor CMA, Statistics Canada Table 34-10-0154-01, January 2016 to September 2026"
    />
  );
}
