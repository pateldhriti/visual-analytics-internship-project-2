import { AnimatePresence, motion } from "framer-motion";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import ScrollProgress from "./components/ScrollProgress.jsx";
import ThemeToggle from "./components/ThemeToggle.jsx";
import Home from "./pages/Home.jsx";
import Sources from "./pages/Sources.jsx";

const pageTransition = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
  transition: { duration: 0.22, ease: "easeOut" },
};

export default function App() {
  const location = useLocation();

  return (
    <div className="site">
      <ScrollProgress />

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
        <AnimatePresence mode="wait">
          <motion.div key={location.pathname} {...pageTransition}>
            <Routes location={location}>
              <Route path="/" element={<Home />} />
              <Route path="/sources" element={<Sources />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
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
