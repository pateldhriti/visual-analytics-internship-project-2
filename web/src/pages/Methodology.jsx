import { motion } from "framer-motion";
import PageContainer from "../components/PageContainer.jsx";
import { staggerParent, fadeUp, reveal } from "../lib/motion.js";

// Plain-language methodology: sources, which year each figure is from,
// how missing values are handled, and the limits of the data. Kept in step
// with docs/data_dictionary.md and docs/decision_log.md.

const SOURCES = [
  {
    name: "Shelter-cost-to-income ratio by tenure (Table 98-10-0252-01), 2021 Census",
    agency: "Statistics Canada",
    use: "Story 1: who spends 30% or more of income on housing. Story 5: renter incomes in Windsor and the four comparison cities.",
    url: "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=9810025201",
  },
  {
    name: "Census Profile, 2021 (98-401-X2021002)",
    agency: "Statistics Canada",
    use: "Background figures such as the number of households. Story 5: population growth, household size and renters' shelter-cost burden in all five cities.",
    url: "https://www150.statcan.gc.ca/n1/en/catalogue/98-401-X2021002",
  },
  {
    name: "Rental Market Survey data tables, Windsor, October 2020 to 2025",
    agency: "CMHC",
    use: "Story 2: rent, vacancy, rental units and turnover by zone and unit size.",
    url: "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/rental-market/rental-market-report-data-tables",
  },
  {
    name: "Rental Market Survey data tables, Canada, October 2024 and 2025",
    agency: "CMHC",
    use: "Story 4: Windsor compared with four similar Ontario cities.",
    url: "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/rental-market/rental-market-report-data-tables",
  },
  {
    name: "Rental Market Survey data tables for London, Hamilton, Kitchener-Cambridge-Waterloo and St. Catharines-Niagara, October 2025",
    agency: "CMHC",
    use: "Story 5: the number of purpose-built rental units in each comparison city.",
    url: "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/rental-market/rental-market-report-data-tables",
  },
  {
    name: "Housing starts, under construction and completions, selected CMAs, monthly (Table 34-10-0154-01)",
    agency: "Statistics Canada (CMHC survey)",
    use: "Story 3: homes started and completed in Windsor, from 2016. Story 5: the same counts for the four comparison cities.",
    url: "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3410015401",
  },
  {
    name: "Housing indicators by tenure and age of primary household maintainer (Table 98-10-0241-01), 2021 Census",
    agency: "Statistics Canada",
    use: "Story 5: how many young renter households (ages 15 to 24) spend 30% or more of income on shelter, in all five cities.",
    url: "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=9810024101",
  },
  {
    name: "CMHC average rents and vacancy rates, October each year (Tables 34-10-0133-01 and 34-10-0130-01)",
    agency: "Statistics Canada (CMHC Rental Market Survey)",
    use: "Story 4: 2-bedroom rent and vacancy for Windsor and the four comparison cities every year from 2015 to 2025.",
    url: "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3410013301",
  },
  {
    name: "Starts, completions and units under construction, quarterly",
    agency: "CMHC",
    use: "Ontario and Canada context on the overview dashboard.",
    url: "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/housing-market-data/starts-completions-units-under-construction-geography",
  },
];

const STEPS = [
  ["Download", "Official files from Statistics Canada and CMHC, kept unchanged."],
  ["Check", "A schema guard stops the update if a file's columns change."],
  ["Clean", "Python reshapes each table and flags suppressed values."],
  ["Store", "A PostgreSQL warehouse links the sources by place, year and tenure."],
  ["Calculate", "Each figure is defined once, in SQL."],
  ["Show", "Apache Superset charts, embedded in this site."],
];

const YEARS = [
  ["Affordability (Story 1)", "2021 Census. Incomes are for 2020."],
  ["Rental market (Story 2)", "CMHC survey taken every October, 2020 to 2025."],
  ["Comparison with other cities (Story 4)", "CMHC survey, October 2024 and October 2025."],
  ["Housing supply (Story 3)", "Monthly, January 2016 to the latest month published."],
  [
    "Combined analysis (Story 5)",
    "Joins the sources above; each chart states the years it combines.",
  ],
];

const RULES = [
  {
    term: "Different years are labelled when combined",
    text: "Stories 1 to 4 keep each figure to its own year. Story 5 combines sources, sometimes from different years: for example, it compares 2020 incomes with 2025 rents. Each such figure says which years it uses and why the result is an upper bound or an estimate.",
  },
  {
    term: "Places are matched exactly",
    text: "Figures are compared only for the same area: the Windsor census metropolitan area (Windsor and nearby towns), or the same CMHC rental zone.",
  },
  {
    term: "Suppressed values stay blank",
    text: "Statistics Canada and CMHC hide some figures when too few households or units were surveyed, or to protect privacy. These appear as gaps or as “not published”, never as zero and never estimated.",
  },
  {
    term: "Reliability is shown",
    text: "CMHC grades each figure from a (excellent) to d (fair, use with caution). Figures graded d are flagged where they are explained.",
  },
  {
    term: "How the stories are combined",
    text: "Story 5 joins the sources on what they share: the renter, the city and the year. A rent is counted as affordable to a household earning at least 12 times the rent divided by 0.30 (the 30% rule).",
  },
  {
    term: "Rounding",
    text: "Statistics Canada rounds household counts to multiples of 5, so totals can differ by a few households from the sum of their parts.",
  },
  {
    term: "Apartments or apartments plus row houses",
    text: "Windsor's own figures (Story 2) include apartments and row houses. The comparison with other cities (Story 4) uses apartments only, because that is what CMHC publishes for every city, so the two can differ slightly.",
  },
];

const LIMITS = [
  "The rental survey covers purpose-built rental buildings only; rented condos, basements and houses are not included.",
  "Average rent includes tenants who moved in long ago, so it is lower than what a new tenant pays today.",
  "The affordability data is a single 2021 snapshot; it cannot show whether affordability has improved or worsened since.",
  "Income is not available year by year, so the affordability-gap index (rent growth minus income growth) is not calculated.",
  "Housing starts and completions are counted for the whole Windsor area; they are not split by rental zone or by who the homes are for.",
  "The site describes what the data shows. It does not forecast rents or prices.",
];

export default function Methodology() {
  return (
    <div className="story-page" data-theme="neighbourhood">
      <PageContainer>
        <motion.div {...reveal(staggerParent)}>
          <motion.h1 variants={fadeUp}>Methodology</motion.h1>
          <motion.p variants={fadeUp}>
            Every figure on this site comes from an official Statistics Canada or CMHC file. This
            page explains where the data comes from, which year each figure describes, how missing
            values are handled, and what the data cannot tell you.
          </motion.p>
        </motion.div>

        <h2>How the data gets here</h2>
        <motion.div {...reveal(staggerParent)} className="methodology-grid methodology-timeline">
          {STEPS.map(([label, value], i) => (
            <motion.div variants={fadeUp} className="card methodology-card" key={label}>
              <span className="methodology-step-index">{i + 1}</span>
              <p className="definition-term">{label}</p>
              <p className="definition-text">{value}</p>
            </motion.div>
          ))}
        </motion.div>

        <h2>Data sources</h2>
        <motion.ul {...reveal(staggerParent)} className="source-list">
          {SOURCES.map((s) => (
            <motion.li variants={fadeUp} key={s.name}>
              <a href={s.url} target="_blank" rel="noreferrer">
                {s.name}
              </a>{" "}
              &mdash; {s.agency}. {s.use}
            </motion.li>
          ))}
        </motion.ul>

        <h2>Which year each figure describes</h2>
        <motion.div {...reveal(staggerParent)} className="definitions-grid">
          {YEARS.map(([topic, year]) => (
            <motion.div variants={fadeUp} className="card definition-card" key={topic}>
              <p className="definition-term">{topic}</p>
              <p className="definition-text">{year}</p>
            </motion.div>
          ))}
        </motion.div>

        <h2>Rules we follow</h2>
        <motion.div {...reveal(staggerParent)} className="definitions-grid">
          {RULES.map((r) => (
            <motion.div variants={fadeUp} className="card definition-card" key={r.term}>
              <p className="definition-term">{r.term}</p>
              <p className="definition-text">{r.text}</p>
            </motion.div>
          ))}
        </motion.div>

        <h2>What the data cannot tell you</h2>
        <motion.div {...reveal(fadeUp)} className="limitations-note">
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {LIMITS.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </motion.div>
      </PageContainer>
    </div>
  );
}
