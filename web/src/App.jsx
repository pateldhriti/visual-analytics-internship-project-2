import { NavLink, Route, Routes } from "react-router-dom";
import ThemeToggle from "./components/ThemeToggle.jsx";
import Home from "./pages/Home.jsx";
import Sources from "./pages/Sources.jsx";

export default function App() {
  return (
    <div className="site">
      <header className="site-header">
        <div className="site-header-inner">
          <span className="brand">
            <span className="brand-mark" aria-hidden="true">
              W
            </span>
            Windsor Housing Analytics
          </span>

          <div className="header-right">
            <nav className="site-nav">
              <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
                Home
              </NavLink>
              <NavLink to="/sources" className={({ isActive }) => (isActive ? "active" : "")}>
                Data Sources
              </NavLink>
            </nav>
            <ThemeToggle />
          </div>
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
