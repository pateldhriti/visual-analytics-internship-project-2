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
    releaseDate: "2023-01-17",
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
    name: "Rental Market Survey Data Tables — Canada (supporting/benchmark)",
    publisher: "Canada Mortgage and Housing Corporation (CMHC)",
    catalogue: "2025 edition",
    releaseDate: "2025-12-11",
    licence: "CMHC data licence (see CMHC website for full terms)",
    licenceUrl: "https://www.cmhc-schl.gc.ca",
    url: "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/rental-market/rental-market-report-data-tables",
    usedFor: "Optional Windsor benchmarking against other Canadian centres (Story 4).",
  },
  {
    name: "Quarterly Starts, Completions, Units Under Construction by Canada and Provinces",
    publisher: "Canada Mortgage and Housing Corporation (CMHC)",
    catalogue: "Second Quarter 2026 edition",
    releaseDate: "Edition dated Second Quarter 2026 — exact publish date not confirmed",
    licence: "CMHC data licence (see CMHC website for full terms)",
    licenceUrl: "https://www.cmhc-schl.gc.ca",
    url: "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/housing-market-data/starts-completions-units-under-construction-geography",
    usedFor: "Housing starts, completions and under-construction activity by dwelling type (Ontario and Canada totals; no CMA-level breakdown in this edition).",
  },
];

export default function Sources() {
  return (
    <div className="page page-sources">
      <section className="hero hero--narrow">
        <h1>Data Sources</h1>
        <p>
          Every dataset used in this project comes directly from Statistics Canada or CMHC.
          Raw downloads are kept separate from processed data so every figure can be traced
          back to its official source.
        </p>
      </section>

      <section className="sources-list">
        {DATASETS.map((d) => (
          <article className="source-card" key={d.name}>
            <h3>
              <a href={d.url} target="_blank" rel="noreferrer">
                {d.name}
              </a>
            </h3>
            <dl>
              <div>
                <dt>Publisher</dt>
                <dd>{d.publisher}</dd>
              </div>
              <div>
                <dt>Catalogue / edition</dt>
                <dd>{d.catalogue}</dd>
              </div>
              <div>
                <dt>Release date</dt>
                <dd>{d.releaseDate}</dd>
              </div>
              <div>
                <dt>Licence</dt>
                <dd>
                  <a href={d.licenceUrl} target="_blank" rel="noreferrer">
                    {d.licence}
                  </a>
                </dd>
              </div>
              <div>
                <dt>Used for</dt>
                <dd>{d.usedFor}</dd>
              </div>
            </dl>
          </article>
        ))}
      </section>
    </div>
  );
}
