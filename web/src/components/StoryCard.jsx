import { useState } from "react";

export default function StoryCard({ number, title, questions, detail }) {
  const [open, setOpen] = useState(false);

  return (
    <article className={`story-card ${open ? "story-card--open" : ""}`}>
      <button
        type="button"
        className="story-card-trigger"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="story-card-number" aria-hidden="true">
          {number}
        </span>
        <h3 className="story-card-title">{title}</h3>
        <span className="story-card-chevron" aria-hidden="true">
          {open ? "−" : "+"}
        </span>
      </button>

      <ul className="story-card-questions">
        {questions.map((q) => (
          <li key={q}>{q}</li>
        ))}
      </ul>

      <div className="story-card-detail" hidden={!open}>
        <p>{detail}</p>
      </div>
    </article>
  );
}
