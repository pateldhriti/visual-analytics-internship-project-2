import { motion } from "framer-motion";
import { TEAM, initials } from "../lib/team.js";
import { fadeIn, staggerParent } from "../lib/motion.js";

// "Meet the team": a round photo (or initials), name, role and a short bio
// for each member.
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
      <motion.ul className="team-grid" variants={staggerParent}>
        {TEAM.map((member) => (
          <motion.li className="team-member" key={member.name} variants={fadeIn}>
            {member.photo ? (
              <img
                className="team-photo"
                src={`/team/${member.photo}`}
                alt={`Photo of ${member.name}`}
                width="128"
                height="128"
              />
            ) : (
              <span className="team-photo team-photo--initials" aria-hidden="true">
                {initials(member.name)}
              </span>
            )}
            <h3 className="team-name">{member.name}</h3>
            <p className="team-role">{member.role}</p>
            <p className="team-bio">{member.bio}</p>
          </motion.li>
        ))}
      </motion.ul>
    </motion.section>
  );
}
