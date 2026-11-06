import { Route, Routes } from "react-router-dom";
import Sidebar from "./components/Sidebar.jsx";
import Footer from "./components/Footer.jsx";
import Home from "./pages/Home.jsx";
import StoryAffordability from "./pages/StoryAffordability.jsx";
import StoryRentalMarket from "./pages/StoryRentalMarket.jsx";
import StoryHousingSupply from "./pages/StoryHousingSupply.jsx";
import StoryComparison from "./pages/StoryComparison.jsx";
import StoryIntegratedAnalysis from "./pages/StoryIntegratedAnalysis.jsx";
import Methodology from "./pages/Methodology.jsx";
import Sources from "./pages/Sources.jsx";
import EmbedSpike from "./pages/EmbedSpike.jsx";

export default function App() {
  return (
    <div className="app-shell">
      {/* First focusable element: lets keyboard and screen-reader users jump
          past the sidebar's nine links straight to the page content. */}
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <Sidebar />

      <div className="app-content">
        <main id="main-content" tabIndex={-1}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/stories/affordability" element={<StoryAffordability />} />
            <Route path="/stories/rental-market" element={<StoryRentalMarket />} />
            <Route path="/stories/housing-supply" element={<StoryHousingSupply />} />
            <Route path="/stories/comparison" element={<StoryComparison />} />
            <Route path="/stories/integrated-analysis" element={<StoryIntegratedAnalysis />} />
            <Route path="/methodology" element={<Methodology />} />
            <Route path="/sources" element={<Sources />} />
            <Route path="/embed-spike" element={<EmbedSpike />} />
          </Routes>
        </main>

        <Footer />
      </div>
    </div>
  );
}
