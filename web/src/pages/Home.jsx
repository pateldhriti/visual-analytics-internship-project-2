import StoryCard from "../components/StoryCard.jsx";

const STORIES = [
  {
    number: 1,
    title: "Who faces the greatest housing affordability pressure?",
    questions: [
      "How does shelter-cost burden vary by income group and household type?",
      "How different is the burden for renters and owners?",
    ],
  },
  {
    number: 2,
    title: "What is happening in Windsor's rental market?",
    questions: [
      "How do average rents, vacancy, rental stock and turnover vary by unit type and zone?",
      "Which parts of the market appear tighter or more affordable?",
    ],
  },
  {
    number: 3,
    title: "What does housing supply look like?",
    questions: [
      "How many housing units are being started and completed, and which dwelling types contribute most?",
      "How can supply activity be interpreted alongside Windsor population and household context?",
    ],
  },
  {
    number: 4,
    title: "How does Windsor compare?",
    questions: [
      "Where compatible data exists, how does Windsor compare with selected Canadian CMAs on rental indicators?",
    ],
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

      <section className="story-grid">
        {STORIES.map((story) => (
          <StoryCard key={story.number} {...story} />
        ))}
      </section>
    </div>
  );
}
