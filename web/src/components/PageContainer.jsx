// Shared page-width/padding wrapper so every page lines up under the
// header consistently instead of each page picking its own max-width.
export default function PageContainer({ children }) {
  return <div className="page-container">{children}</div>;
}
