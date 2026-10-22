import PageContainer from "../components/PageContainer.jsx";

const SOURCES = [
  {
    name: "Census Profile, 2021 — Census Metropolitan Areas and Census Agglomerations (98-401-X2021002)",
    agency: "Statistics Canada",
    url: "https://www150.statcan.gc.ca/n1/en/catalogue/98-401-X2021002",
  },
  {
    name: "Shelter-cost-to-income ratio by tenure (98-10-0252-01)",
    agency: "Statistics Canada",
    url: "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=9810025201",
  },
  {
    name: "Rental Market Report, Windsor CMA 2025",
    agency: "CMHC",
    url: "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/market-reports/rental-market-reports-major-centres",
  },
  {
    name: "Rental Market Survey Data Tables (also used for the Canada-wide comparator workbook)",
    agency: "CMHC",
    url: "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/rental-market/rental-market-report-data-tables",
  },
  {
    name: "Starts, Completions and Units Under Construction by Geography",
    agency: "CMHC",
    url: "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/housing-market-data/starts-completions-units-under-construction-geography",
  },
];

export default function Methodology() {
  return (
    <PageContainer>
      <h1>Methodology</h1>
      <p>
        Every figure on this site traces back to an official Statistics Canada or CMHC download. Raw
        files are kept separate from processed data, loaded into PostgreSQL through documented
        Python ETL scripts, and queried through SQL views that Apache Superset builds charts from.
      </p>

      <h2>Stack</h2>
      <ul>
        <li>Data sources: Statistics Canada, CMHC</li>
        <li>Data processing: Python (pandas, SQLAlchemy)</li>
        <li>Database: PostgreSQL</li>
        <li>Analytics: Apache Superset</li>
        <li>Front end: React</li>
        <li>Containerisation: Docker</li>
      </ul>

      <h2>Data sources</h2>
      <ul>
        {SOURCES.map((s) => (
          <li key={s.url}>
            <a href={s.url} target="_blank" rel="noreferrer">
              {s.name}
            </a>{" "}
            &mdash; {s.agency}
          </li>
        ))}
      </ul>

      <h2>Known limitations</h2>
      <ul>
        <li>
          Sources span different reporting years &mdash; the 2021 Census, 2025 CMHC rental-market
          data, and 2026 construction data are shown side by side for context, not joined directly:
          they&rsquo;re connected only where geography and time period make the comparison valid.
        </li>
        <li>
          Housing-supply figures (starts, completions, units under construction) are Ontario- and
          Canada-wide only &mdash; CMHC&rsquo;s source table has no Windsor-specific breakdown, so
          there&rsquo;s no Windsor-only starts/completions figure anywhere on this site yet.
        </li>
        <li>
          Only one quarter of supply data has been extracted so far (Second Quarter 2026) &mdash;
          not a multi-year time series, so trend questions (&ldquo;is Windsor building enough
          housing over time?&rdquo;) can&rsquo;t be answered from this data yet.
        </li>
        <li>
          The Story 4 affordability-gap index (rent growth vs. renter income growth) isn&rsquo;t
          computed: no source extracted so far contains a renter-income time series to compute a
          real growth rate from, so that figure is left blank rather than estimated.
        </li>
        <li>
          Within the shelter-cost-burden breakdown (Story 1), about 8.8% of burdened households
          aren&rsquo;t accounted for by any published StatCan sub-category &mdash; flagged as an
          open data-quality question, not silently assumed into any one bucket.
        </li>
      </ul>
    </PageContainer>
  );
}
