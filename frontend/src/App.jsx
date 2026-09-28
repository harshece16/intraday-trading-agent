import { useEffect, useState } from "react";
import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";
import { API_BASE, useAppState } from "./api";
import LoadState from "./components/LoadState";
import { useAlerts } from "./useAlerts";
import StatusBar, { Sidebar } from "./components/Header";
import LiveLog from "./components/LiveLog";
import Overview from "./pages/Overview";
import PreMarket from "./pages/PreMarket";
import DayPlan from "./pages/DayPlan";
import Screener from "./pages/Screener";
import Stock from "./pages/Stock";
import TechnicalAnalysis from "./pages/TechnicalAnalysis";
import Portfolio from "./pages/Portfolio";
import PortfolioDiagnostic from "./pages/PortfolioDiagnostic";
import Journal from "./pages/Journal";
import Trades from "./pages/Trades";
import MomentumBook from "./pages/MomentumBook";
import JevBook from "./pages/JevBook";

function Page({ children }) {
  const location = useLocation();
  return <main className="page" key={location.pathname}>{children}</main>;
}

function Connecting() {
  const [slow, setSlow] = useState(false);
  useEffect(() => { const t = setTimeout(() => setSlow(true), 8000); return () => clearTimeout(t); }, []);
  return slow
    ? <LoadState error={`can't reach the engine at ${API_BASE}. Is the backend running? This page keeps retrying`} />
    : <LoadState label="Connecting to the engine…" />;
}

function AppRoutes({ state }) {
  if (!state) return <Page><Connecting /></Page>;
  return (
    <Routes>
      <Route path="/" element={<Page><Overview state={state} /></Page>} />
      <Route path="/premarket" element={<Page><PreMarket state={state} /></Page>} />
      <Route path="/day-plan" element={<Page><DayPlan /></Page>} />
      <Route path="/screener" element={<Page><Screener state={state} /></Page>} />
      <Route path="/stock/:symbol" element={<Page><Stock state={state} /></Page>} />
      <Route path="/technical-analysis" element={<Page><TechnicalAnalysis /></Page>} />
      <Route path="/portfolio" element={<Page><Portfolio state={state} /></Page>} />
      <Route path="/portfolio/diagnostic" element={<Page><PortfolioDiagnostic /></Page>} />
      <Route path="/journal" element={<Page><Journal /></Page>} />
      <Route path="/trades" element={<Page><Trades state={state} /></Page>} />
      <Route path="/momentum-book" element={<Page><MomentumBook /></Page>} />
      <Route path="/jev-book" element={<Page><JevBook /></Page>} />
    </Routes>
  );
}

function Shell() {
  const state = useAppState();
  useAlerts(state);
  const [liveLogOpen, setLiveLogOpen] = useState(false);
  return (
    <div className="app">
      <Sidebar state={state} liveLogOpen={liveLogOpen} onToggleLiveLog={() => setLiveLogOpen((v) => !v)} />
      <div className="app-main">
        <StatusBar state={state} />
        <AppRoutes state={state} />
      </div>
      <LiveLog state={state} open={liveLogOpen} onClose={() => setLiveLogOpen(false)} />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  );
}
