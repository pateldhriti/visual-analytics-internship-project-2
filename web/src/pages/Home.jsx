import KpiStrip from "../components/KpiStrip.jsx";
import StoryCard from "../components/StoryCard.jsx";

// Detail text uses only numbers already verified against the live
// database this session -- see docs/story1_questions_and_measures.md,
// docs/conceptual_er_model.md and sql/story4_views.sql. Story 3's detail
// names its real data gap rather than implying more than exists.
const STORIES = [
  {
    number: 1,
    title: "Who faces the greatest housing affordability pressure?",
    questions: [
      "How does shelter-cost burden vary by income group and household type?",
      "How different is the burden for renters and owners?",
    ],
    detail:
      "In Windsor CMA, 10.9% of owner households spend 30%+ of income on shelter costs, " +
      "compared with 34.5% of renter households — renters are burdened more than 3x as " +
      "often as owners. Source: StatCan table 98-10-0252-01, 2021 Census.",
  },
  {
    number: 2,
    title: "What is happening in Windsor's rental market?",
    questions: [
      "How do average rents, vacancy, rental stock and turnover vary by unit type and zone?",
      "Which parts of the market appear tighter or more affordable?",
    ],
    detail:
      "Windsor CMA's purpose-built apartment vacancy rate was 3.7% in October 2025, " +
      "up from 3.3% a year earlier. Average 2-bedroom apartment rent reached $1,454. " +
      "Source: CMHC Rental Market Survey, Windsor, 2025.",
  },
  {
    number: 3,
    title: "What does housing supply look like?",
    questions: [
      "How many housing units are being started and completed, and which dwelling types contribute most?",
      "How can supply activity be interpreted alongside Windsor population and household context?",
    ],
    detail:
      "Ontario started 17,786 housing units in Q2 2026, 70% of them apartments. No Windsor-" +
      "specific starts figure exists in this project's data yet — this quarter's CMHC table " +
      "reports Ontario/Canada totals only. See docs/story3_narrative_v1.md for the full picture.",
  },
  {
    number: 4,
    title: "How does Windsor compare?",
    questions: [
      "Where compatible data exists, how does Windsor compare with selected Canadian CMAs on rental indicators?",
    ],
    detail:
      "Apartment vacancy rates, Oct-25: Toronto 3.0%, Windsor 3.7%, London 4.0%, Kitchener-" +
      "Cambridge-Waterloo 4.1%. Windsor sits in the middle of this comparison set — tighter " +
      "than Toronto, looser than the other two Southwestern Ontario peers.",
  },
];

export default function Home() {
  return (
    <div className="page page-home">
      <section className="hero">
        <h1>Housing affordability and market trends in Windsor, CMA</h1>
        <p>
          A public, web-based look at housing affordability and housing-market conditions
          in the Windsor Census Metropolitan Area, built entirely from official Canadian open
          data &mdash; Statistics Canada&rsquo;s Census and shelter-cost tables, and CMHC&rsquo;s
          rental-market and construction data. Every figure is traceable back to its official
          source; see the <a href="/sources">Data Sources</a> page for exactly where each
          dataset comes from, its release date and its licence.
        </p>
      </section>

      <KpiStrip />

      <section className="story-grid">
        <p className="story-grid-hint">Click a story to see a real headline number.</p>
        {STORIES.map((story) => (
          <StoryCard key={story.number} {...story} />
        ))}
      </section>
    </div>
  );
}
