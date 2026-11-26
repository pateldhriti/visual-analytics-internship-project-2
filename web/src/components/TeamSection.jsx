import { motion } from "framer-motion";
import { SUPERVISOR, TEAM, initials } from "../lib/team.js";
import { fadeIn, staggerParent } from "../lib/motion.js";

// A round photo, or the person's initials when there is no photo.
function Photo({ person }) {
  return person.photo ? (
    <img
      className="team-photo"
      src={`/team/${person.photo}`}
      alt={`Photo of ${person.name}`}
      width="128"
      height="128"
    />
  ) : (
    <span className="team-photo team-photo--initials" aria-hidden="true">
      {initials(person.name.replace(/^Dr\.\s+/, ""))}
    </span>
  );
}

// "Meet the team": the supervisor in a centred card, then a card for each
// member with a round photo (or initials), name, role and a short bio.
export default function TeamSection() {
  return (
    <motion.section
      className="section team-section"
      id="team"
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-100px" }}
      variants={staggerParent}
    >
      <div className="section-heading">
        <h2>Meet the team</h2>
        <p className="section-note">COMP 8977 &middot; University of Windsor</p>
      </div>
      <motion.div className="team-card team-card--supervisor" variants={fadeIn}>
        <Photo person={SUPERVISOR} />
        <h3 className="team-name">{SUPERVISOR.name}</h3>
        <p className="team-role team-role--accent">{SUPERVISOR.role}</p>
        <p className="team-affiliation">{SUPERVISOR.affiliation}</p>
        <p className="team-bio team-bio--centred">{SUPERVISOR.bio}</p>
      </motion.div>
      <motion.ul className="team-grid" variants={staggerParent}>
        {TEAM.map((member) => (
          <motion.li className="team-card team-member" key={member.name} variants={fadeIn}>
            <Photo person={member} />
            <h3 className="team-name">{member.name}</h3>
            <p className="team-role">{member.role}</p>
            <p className="team-bio">{member.bio}</p>
          </motion.li>
        ))}
      </motion.ul>
    </motion.section>
  );
}
