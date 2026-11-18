// The project team, shown in the "Meet the team" section of the Home page.
// photo: a file in web/public/team/ (e.g. "dhritiben.jpg"), or null to show
// the person's initials in the circle instead.
export const TEAM = [
  {
    name: "Dhritiben Patel",
    role: "Project Manager",
    photo: null,
    bio: "Keeps the plan and the weekly rhythm on track. Built the affordability story (Story 1) and the combined analysis that joins all five stories (Story 5), designed the website, and moved the project onto the University of Windsor's servers.",
  },
  {
    name: "Charmiben Patel",
    role: "Front-End and Embedding Lead",
    photo: null,
    bio: "Built the secure way the website shows live Superset dashboards, the Executive Overview and the housing-supply story (Story 3). Checked every page for accessibility and phone use, and published the website on the university's server.",
  },
  {
    name: "Romit Patel",
    role: "Data Pipeline Lead",
    photo: null,
    bio: "Built the pipeline that loads every source with one command, and the weekly refresh that stops with an alert if a source file changes shape. Created the rental-market story (Story 2) and its dashboard.",
  },
  {
    name: "Pavan Rella",
    role: "Dashboards and Performance Lead",
    photo: null,
    bio: "Built the comparison with four similar Ontario cities (Story 4) and its ten-year view of rents, set the filter standards every dashboard follows, made each KPI show the same number everywhere, and tuned Superset for speed.",
  },
];

export const initials = (name) =>
  name
    .split(" ")
    .map((part) => part[0])
    .join("");
