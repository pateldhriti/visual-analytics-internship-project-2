import { Route, Routes } from "react-router-dom";
import Header from "./components/Header.jsx";
import Footer from "./components/Footer.jsx";
import Home from "./pages/Home.jsx";
import StoryAffordability from "./pages/StoryAffordability.jsx";
import StoryRentalMarket from "./pages/StoryRentalMarket.jsx";
import StoryHousingSupply from "./pages/StoryHousingSupply.jsx";
import StoryComparison from "./pages/StoryComparison.jsx";
import Methodology from "./pages/Methodology.jsx";
import EmbedSpike from "./pages/EmbedSpike.jsx";

export default function App() {
  return (
    <div className="app-shell">
      <Header />

      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/stories/affordability" element={<StoryAffordability />} />
          <Route path="/stories/rental-market" element={<StoryRentalMarket />} />
          <Route path="/stories/housing-supply" element={<StoryHousingSupply />} />
          <Route path="/stories/comparison" element={<StoryComparison />} />
          <Route path="/methodology" element={<Methodology />} />
          <Route path="/embed-spike" element={<EmbedSpike />} />
        </Routes>
      </main>

      <Footer />
    </div>
  );
}
