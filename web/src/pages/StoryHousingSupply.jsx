import StoryPage from "../components/StoryPage.jsx";

// Narrative paragraphs reused verbatim from docs/story3_narrative_v1.md's
// own draft text -- real, already-verified figures, not written fresh here.
const NARRATIVE = [
  "Ontario added 17,786 new housing units in the second quarter of 2026, according to CMHC's " +
    "construction survey — and the story of what kind of housing that number represents is at " +
    "least as telling as the total itself. Apartments (CMHC's “Apartment and Other” " +
    "category) accounted for 12,547 of those starts, 70% of everything built. Row housing came " +
    "next at 2,262 (13%), then singles at 2,693 (15%), with semi-detached homes a distant fourth " +
    "at 284 (2%). Ontario's new supply, in other words, is overwhelmingly multi-unit.",
  "Completions tell a related but distinct story. Ontario completed 14,083 units in the same " +
    "quarter — about 3,700 fewer than it started. That gap isn't evidence of a slowdown on its " +
    "own: completions lag starts by the length of a construction project, so a quarter with more " +
    "starts than completions is consistent with a pipeline that's still filling, not necessarily " +
    "one that's falling behind. What it does confirm is scale: 162,138 units are under " +
    "construction in Ontario right now, over 11 times the quarter's own completions.",
];

const DEFINITIONS = [
  {
    term: "Housing starts",
    text: "New residential units where construction began during the quarter, by dwelling type.",
  },
  {
    term: "Completions",
    text: "Units where construction finished during the quarter -- lags starts by the length of the construction project, so completions below starts in one quarter doesn't by itself mean a slowdown.",
  },
  {
    term: "Units under construction",
    text: "The running total of started-but-not-yet-completed units at quarter end -- a measure of pipeline scale, not of that quarter's own activity.",
  },
];

const LIMITATIONS = [
  "These figures are Ontario- and Canada-wide only -- CMHC's source table has no Windsor-specific breakdown, so there's no Windsor-only starts/completions figure here yet.",
  "Only one quarter (Second Quarter 2026) has been extracted so far -- not a multi-year time series, so trend questions can't be answered from this data yet.",
];

const FILTERS = [
  { label: "Geography", value: "Ontario" },
  { label: "Period", value: "Second Quarter 2026" },
  { label: "Dwelling type", value: "All types" },
];

const KPIS = [
  { label: "New housing starts", value: "17,786", accent: "teal", trend: "up" },
  { label: "Completions", value: "14,083", accent: "blue", trend: "flat" },
  { label: "Units under construction", value: "162,138", accent: "violet", trend: "up" },
  { label: "Apartment share of starts", value: "70%", accent: "rose", trend: "flat" },
];

export default function StoryHousingSupply() {
  return (
    <StoryPage
      storyLabel="Story 3"
      title="What does housing supply look like?"
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
      limitations={LIMITATIONS}
      source="CMHC Quarterly Starts, Completions, Units Under Construction (Ontario/Canada, Second Quarter 2026) -- warehouse.fact_starts_completions"
    />
  );
}
