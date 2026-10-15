import { NavLink, Route, Routes } from "react-router-dom";
import Home from "./pages/Home.jsx";
import Sources from "./pages/Sources.jsx";

export default function App() {
  return (
    <div className="site">
      <header className="site-header">
        <div className="site-header-inner">
          <span className="site-title">Windsor Housing Analytics</span>
          <nav className="site-nav">
            <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
              Home
            </NavLink>
            <NavLink to="/sources" className={({ isActive }) => (isActive ? "active" : "")}>
              Data Sources
            </NavLink>
          </nav>
        </div>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/sources" element={<Sources />} />
        </Routes>
      </main>

      <footer className="site-footer">
        <p>
          Built from official Statistics Canada and CMHC open data. See{" "}
          <NavLink to="/sources">Data Sources</NavLink> for licences and release dates.
        </p>
      </footer>
    </div>
  );
}
