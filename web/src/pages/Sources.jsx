import PageContainer from "../components/PageContainer.jsx";

// Every dataset this project actually uses, with its real publisher,
// catalogue/edition, release date, licence, and source URL. Release dates
// and licence links were checked directly against each publisher's own
// page (not assumed) -- 98-10-0252-01's release date was originally
// recorded as 2023-01-17 in an earlier draft of this page; re-checked
// against StatCan's own table page and corrected to the real value,
// 2022-09-23. Two things are flagged honestly rather than guessed: the
// CMHC starts/completions edition's exact publish date isn't confirmed
// (only its "Second Quarter 2026" edition label is), and CMHC's data
// licence is linked to CMHC's own site rather than labeled as a specific
// named licence, since CMHC's data-table pages don't state one.
const DATASETS = [
  {
    name: "Census Profile, 2021 — Census Metropolitan Areas and Census Agglomerations",
    publisher: "Statistics Canada",
    catalogue: "98-401-X2021002",
    releaseDate: "2022-12-15",
    licence: "Statistics Canada Open Licence",
    licenceUrl: "https://www.statcan.gc.ca/en/reference/licence",
    url: "https://www150.statcan.gc.ca/n1/en/catalogue/98-401-X2021002",
    usedFor: "Windsor CMA population, income, labour, households and housing context.",
  },
  {
    name: "Shelter-cost-to-income ratio by tenure: Canada, provinces and territories, census metropolitan areas and census agglomerations",
    publisher: "Statistics Canada",
    catalogue: "Table 98-10-0252-01",
    releaseDate: "2022-09-23",
    licence: "Statistics Canada Open Licence",
    licenceUrl: "https://www.statcan.gc.ca/en/reference/licence",
    url: "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=9810025201",
    usedFor: "Affordability by income group, household type, tenure and shelter-cost burden.",
  },
  {
    name: "Rental Market Survey Data Tables — Windsor",
    publisher: "Canada Mortgage and Housing Corporation (CMHC)",
    catalogue: "2025 edition",
    releaseDate: "2025-12-11",
    licence: "CMHC data licence (see CMHC website for full terms)",
    licenceUrl: "https://www.cmhc-schl.gc.ca",
    url: "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/rental-market/rental-market-report-data-tables",
    usedFor: "Vacancy, average rent, rental universe, turnover, bedroom type and zones.",
  },
  {
    name: "Rental Market Survey Data Tables — Canada (comparator CMAs)",
    publisher: "Canada Mortgage and Housing Corporation (CMHC)",
    catalogue: "2025 edition",
    releaseDate: "2025-12-11",
    licence: "CMHC data licence (see CMHC website for full terms)",
    licenceUrl: "https://www.cmhc-schl.gc.ca",
    url: "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/rental-market/rental-market-report-data-tables",
    usedFor: "Windsor benchmarked against 4 size-comparable Ontario CMAs (Story 4).",
  },
  {
    name: "Quarterly Starts, Completions, Units Under Construction by Canada and Provinces",
    publisher: "Canada Mortgage and Housing Corporation (CMHC)",
    catalogue: "Second Quarter 2026 edition",
    releaseDate: "Edition dated Second Quarter 2026 — exact publish date not confirmed",
    licence: "CMHC data licence (see CMHC website for full terms)",
    licenceUrl: "https://www.cmhc-schl.gc.ca",
    url: "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/housing-market-data/starts-completions-units-under-construction-geography",
    usedFor:
      "Housing starts, completions and under-construction activity by dwelling type (Ontario and Canada totals; no CMA-level breakdown in this edition).",
  },
];

export default function Sources() {
  return (
    <PageContainer>
      <h1>Data sources</h1>
      <p className="hero-lede" style={{ marginBottom: 32 }}>
        Every dataset this site uses, with its publisher, catalogue or edition, release date,
        licence, and a direct link to the source. See the{" "}
        <a href="/methodology">full methodology page</a> for the stack and known limitations.
      </p>

      <div className="methodology-grid">
        {DATASETS.map((d) => (
          <div className="card methodology-card" key={d.url + d.name}>
            <h2>{d.name}</h2>
            <dl style={{ margin: 0, display: "grid", gap: 6 }}>
              <div>
                <dt style={{ display: "inline", fontWeight: 700 }}>Publisher: </dt>
                <dd style={{ display: "inline", margin: 0 }}>{d.publisher}</dd>
              </div>
              <div>
                <dt style={{ display: "inline", fontWeight: 700 }}>Catalogue: </dt>
                <dd style={{ display: "inline", margin: 0 }}>{d.catalogue}</dd>
              </div>
              <div>
                <dt style={{ display: "inline", fontWeight: 700 }}>Release date: </dt>
                <dd style={{ display: "inline", margin: 0 }}>{d.releaseDate}</dd>
              </div>
              <div>
                <dt style={{ display: "inline", fontWeight: 700 }}>Licence: </dt>
                <dd style={{ display: "inline", margin: 0 }}>
                  <a href={d.licenceUrl} target="_blank" rel="noreferrer">
                    {d.licence}
                  </a>
                </dd>
              </div>
              <div>
                <dt style={{ display: "inline", fontWeight: 700 }}>Used for: </dt>
                <dd style={{ display: "inline", margin: 0 }}>{d.usedFor}</dd>
              </div>
            </dl>
            <p style={{ marginTop: 14, marginBottom: 0 }}>
              <a href={d.url} target="_blank" rel="noreferrer">
                View source &rarr;
              </a>
            </p>
          </div>
        ))}
      </div>
    </PageContainer>
  );
}
