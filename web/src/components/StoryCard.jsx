import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import useSpotlight from "../hooks/useSpotlight.js";

export default function StoryCard({ number, title, questions, detail }) {
  const [open, setOpen] = useState(false);
  const spotlight = useSpotlight();

  return (
    <motion.article
      className={`story-card ${spotlight.className} ${open ? "story-card--open" : ""}`}
      onMouseMove={spotlight.onMouseMove}
      whileHover={{ y: -4 }}
      transition={{ type: "spring", stiffness: 300, damping: 22 }}
    >
      <button
        type="button"
        className="story-card-trigger"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <motion.span
          className="story-card-number"
          aria-hidden="true"
          animate={{ rotate: open ? -6 : 0 }}
        >
          {number}
        </motion.span>
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

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            className="story-card-detail-wrap"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
          >
            <div className="story-card-detail">
              <p>{detail}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.article>
  );
}
