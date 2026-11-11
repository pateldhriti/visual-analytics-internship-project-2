import StoryPage from "../components/StoryPage.jsx";
import StoryHighlights from "../components/StoryHighlights.jsx";
import SupersetGuestEmbed from "../components/SupersetGuestEmbed.jsx";

// Story 5 is the combined story: every figure here comes from a view that
// joins data from two of Stories 1-4 (sql/story5_views.sql), shown on the
// Story 5 Superset dashboard (id 8, etl/build_story5_dashboard.py). Text
// condensed from docs/story5_combined_analysis.md; re-check both after a
// data refresh.
const INTRO =
  "Each of the first four stories answers its own question from one dataset. This story " +
  "combines them. The datasets share the city, the year and the renter, so they can be joined " +
  "to answer seven questions none of them can answer alone.";

const QUESTIONS = [
  "Can Windsor renters afford the rent? (Story 1 incomes + Story 2 rents)",
  "Is Windsor affordable, or only cheap? (Story 1 incomes + Story 4 comparison cities)",
  "Did new homes ease the rental market? (Story 3 completions + Story 2 vacancy)",
  "Is Windsor building as much as its peers? (Story 3 construction + Story 4 comparison cities)",
  "Did building keep up with population growth? (Story 3 completions + Census population, 5 cities)",
  "Can young renters and students afford to rent? (Census renters by age + Story 1 + Story 4 cities)",
  "How big is the rental market, and how do the cities compare overall? (CMHC rental units + Census renters, then every measure)",
];

const KPIS = [
  { label: "Windsor renters who cannot afford an average 2-bedroom", value: "61%", accent: "rose" },
  {
    label: "Share of the median renter's income a 2-bedroom takes",
    value: "36%",
    accent: "violet",
  },
  { label: "Homes completed 2023 to 2025, as vacancy rose", value: "5,247", accent: "teal" },
  {
    label: "Homes started a year per 1,000 households (fewest of 5)",
    value: "8.4",
    accent: "blue",
  },
];

const NARRATIVE = [
  "Can renters afford the rent? Under the 30% rule, an average Windsor 2-bedroom ($1,451 a " +
    "month) needs a household income of about $58,000. The median renter household earned " +
    "$48,400, so about 61% of renter households, some 27,700, earn less than that; even a " +
    "1-bedroom is out of reach for about half.",
  "Affordable, or only cheap? Windsor has the lowest 2-bedroom rent of the five cities, but its " +
    "renters also have the second-lowest incomes. A year of rent takes 36% of the median " +
    "renter's income, the same as Hamilton and close to the others (36% to 39%). Windsor is " +
    "cheap, not more affordable, although its share of renters spending 30% or more on shelter " +
    "(34.8%) is the lowest of the five.",
  "Did new homes ease the market? Few homes were finished in 2021 and 2022, and vacancy fell to " +
    "1.8% in 2022. Completions then jumped to 1,967 in 2023 and stayed high; vacancy climbed back " +
    "to 3.6% by 2025 and rent growth slowed from 8.1% to 5.9%. Story 2's rising vacancy follows " +
    "Story 3's completion surge.",
  "Is Windsor building enough? Since 2016 Windsor has started 8.4 homes a year for every 1,000 " +
    "households, the fewest of the five cities; Kitchener-Cambridge-Waterloo started 19.7. Only " +
    "in 2024 did Windsor reach the comparison cities' average, and 2025 fell back.",
  "Did building keep up with population? Between the 2016 and 2021 Censuses Windsor gained " +
    "23,912 people, about 9,500 homes' worth at its household size, but completed only 5,666 " +
    "homes: 0.59 for every home needed, the lowest of the five cities (0.72 to 0.91 elsewhere). " +
    "Windsor grew about as fast as Hamilton and St. Catharines-Niagara, so slow building is not " +
    "explained by slow growth.",
  "How big is the rental market? Windsor has about 44 purpose-built rental units for every 100 " +
    "renter households, the second-lowest of the five cities, so roughly half or more of its " +
    "renters live in rented houses, condos and basements outside CMHC's survey. A tighter market " +
    "does not explain the differences between cities: vacancy is 3.6% to 4.1% everywhere, and " +
    "Windsor's is nearly as tight as Hamilton's with less renter pressure.",
  "Can young renters afford it? In Windsor, 46.5% of renter households led by someone aged " +
    "15 to 24 spend 30% or more of their income on shelter, against 34.8% of all renters: the most " +
    "burdened age group. Young renters are worse off in every city, but Windsor's are the least " +
    "burdened of the five (50.6% to 55.3% elsewhere). An average studio needs about $37,900 a year. " +
    "Together: Windsor's low rents reflect low incomes, building has fallen short of population " +
    "growth, the recent completions only partly caught up, and young renters feel it most.",
];

// How the datasets are joined, shown as the definitions grid.
const DEFINITIONS = [
  {
    term: "Story 1 + Story 2: by renter",
    text: "Each rent is turned into the income it needs (rent x 12 / 0.30) and compared with Windsor renter households' incomes, band by band.",
  },
  {
    term: "Story 1 + Story 4: by city",
    text: "The same Census table Story 1 uses for Windsor also covers the four comparison cities, so each city's rent is set against its own renters' incomes.",
  },
  {
    term: "Story 3 + Story 2: by year",
    text: "Windsor's homes completed each calendar year sit next to that October's vacancy rate and rent increase, 2020 to 2025.",
  },
  {
    term: "Story 3 + Story 4: by city and year",
    text: "Homes started in each of the five cities, divided by that city's households (2021 Census), 2016 to 2025.",
  },
  {
    term: "Story 3 + Census population: by city",
    text: "Homes completed 2016 to 2020 against the homes each city's 2016-2021 population growth needed (growth divided by people per household).",
  },
  {
    term: "Census renters by age + Story 1 + Story 4: by city",
    text: "Renter households by the age of the person who maintains them (2021 Census), with Story 1's measure of spending 30% or more on shelter, for all five cities.",
  },
  {
    term: "CMHC rental units + Census renters: by city",
    text: "Purpose-built rental units counted by CMHC in October 2025, per 100 renter households counted by the 2021 Census, for all five cities.",
  },
];

const LIMITATIONS = [
  "Incomes are from the 2021 Census (2020 incomes) and rents from October 2025. Incomes have risen since, so the shares who cannot afford a rent are an upper bound.",
  "Incomes are published in $10,000 bands; within the band containing the income needed, households are assumed to be spread evenly.",
  "Completions count all new homes, including condos and houses for sale, while vacancy covers purpose-built rentals, so section 3 shows timing, not cause.",
  "Rents for the city comparison are for apartments only (CMHC publishes no other comparison); Windsor's own figures include row houses.",
  "Homes needed assumes 2021 household sizes for the whole 2016-2021 period, and completions are not net of demolitions, so those ratios are estimates; the ranking between cities is the reliable part.",
  "The young-renter figures count students who head their own rented household; students in residence, living with parents, or away during the May 2021 online term are not included.",
  "Rental units are counted in 2025 and renter households in 2021, and some units are vacant, so the share of renters outside purpose-built rentals is an estimate.",
];

const FILTERS = [
  { label: "Geography", value: "Windsor CMA and 4 comparison cities" },
  { label: "Joins", value: "Stories 1+2, 1+4, 3+2, 3+4, 3+Census, Census by age, rental stock" },
  { label: "Years", value: "2016 to 2025 (adjustable in the dashboard)" },
];

export default function StoryIntegratedAnalysis() {
  return (
    <StoryPage
      storyLabel="Story 5"
      title="How do affordability, rental conditions, and supply fit together?"
      intro={INTRO}
      questions={QUESTIONS}
      filters={FILTERS}
      kpis={KPIS}
      highlights={
        <StoryHighlights only={["afford", "cheap", "supply"]} here="/stories/integrated-analysis" />
      }
      dashboard={
        <SupersetGuestEmbed
          dashboard="story5"
          fallbackDashboardId={8}
          title="Story 5: How do affordability, rental conditions, and supply fit together? (Superset dashboard)"
        />
      }
      narrative={NARRATIVE}
      definitions={DEFINITIONS}
      limitations={LIMITATIONS}
      variant="horizon"
      theme="neighbourhood"
      source="StatCan 98-10-0252-01 and Census Profile 98-401-X2021002 (2021 Census); CMHC Rental Market Survey, October 2020 to 2025; StatCan 34-10-0154-01 starts and completions, 2016 to 2025; StatCan 98-10-0241-01 housing indicators by age (2021 Census); CMHC Rental Market Survey city tables, October 2025"
    />
  );
}
