export default function Methodology() {
  return (
    <div className="page">
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
      <p className="placeholder-note">
        Full methodology write-up (data quality checks, known limitations, refresh process) goes
        here &mdash; scaffold placeholder only.
      </p>
    </div>
  );
}
