export default function StoryCard({ number, title, questions }) {
  return (
    <article className="story-card">
      <span className="story-card-number">Story {number}</span>
      <h3 className="story-card-title">{title}</h3>
      <ul className="story-card-questions">
        {questions.map((q) => (
          <li key={q}>{q}</li>
        ))}
      </ul>
    </article>
  );
}
