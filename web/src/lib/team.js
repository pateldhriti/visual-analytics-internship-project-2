// The project team, shown on the Home page and in the sidebar of every page.
export const TEAM = ["Charmiben Patel", "Dhritiben Patel", "Pavan Rella", "Romit Patel"];

// "A, B, C and D"
export const teamNames = () => `${TEAM.slice(0, -1).join(", ")} and ${TEAM[TEAM.length - 1]}`;
