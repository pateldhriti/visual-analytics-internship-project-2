import { NavLink, Route, Routes } from "react-router-dom";
import Home from "./pages/Home.jsx";
import StoryAffordability from "./pages/StoryAffordability.jsx";
import StoryRentalMarket from "./pages/StoryRentalMarket.jsx";
import StoryHousingSupply from "./pages/StoryHousingSupply.jsx";
import StoryComparison from "./pages/StoryComparison.jsx";
import Methodology from "./pages/Methodology.jsx";

// Minimal nav for now -- the real header/footer/responsive shell is a
// separate task (Layout and navigation shell), not this scaffold.
export default function App() {
  return (
    <div className="app-shell">
      <nav className="scaffold-nav">
        <NavLink to="/" end>
          Home
        </NavLink>
        <NavLink to="/stories/affordability">Story 1</NavLink>
        <NavLink to="/stories/rental-market">Story 2</NavLink>
        <NavLink to="/stories/housing-supply">Story 3</NavLink>
        <NavLink to="/stories/comparison">Story 4</NavLink>
        <NavLink to="/methodology">Methodology</NavLink>
      </nav>

      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/stories/affordability" element={<StoryAffordability />} />
          <Route path="/stories/rental-market" element={<StoryRentalMarket />} />
          <Route path="/stories/housing-supply" element={<StoryHousingSupply />} />
          <Route path="/stories/comparison" element={<StoryComparison />} />
          <Route path="/methodology" element={<Methodology />} />
        </Routes>
      </main>
    </div>
  );
}
