import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { API_BASE, useAppState } from "./api";
import LoadState from "./components/LoadState";
import { useAlerts } from "./useAlerts";
import StatusBar, { Sidebar } from "./components/Header";
import LiveLog from "./components/LiveLog";
import IntradayRecordBanner from "./components/IntradayRecordBanner";
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
import Kronos from "./pages/Kronos";

// `intraday` marks a page of the intraday paper record: it opens with the
// banner that says so (README section 116).
function Page({ children, intraday = false }) {
  const location = useLocation();
  return (
    <main className="page" key={location.pathname}>
      {intraday && <IntradayRecordBanner />}
      {children}
    </main>
  );
}

// An old address still opens its page, with its query string kept.
function Redirect({ to }) {
  const { search, hash } = useLocation();
  return <Navigate to={{ pathname: to, search, hash }} replace />;
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
      {/* The momentum book is the strategy, so it is the front page (README section 116). */}
      <Route path="/" element={<Page><MomentumBook /></Page>} />
      <Route path="/momentum-book" element={<Redirect to="/" />} />
      {/* The intraday engine's pages: a paper record, each under the banner. */}
      <Route path="/intraday" element={<Page intraday><Overview state={state} /></Page>} />
      <Route path="/overview" element={<Redirect to="/intraday" />} />
      <Route path="/premarket" element={<Page intraday><PreMarket state={state} /></Page>} />
      <Route path="/day-plan" element={<Page intraday><DayPlan /></Page>} />
      <Route path="/screener" element={<Page intraday><Screener state={state} /></Page>} />
      <Route path="/stock/:symbol" element={<Page intraday><Stock state={state} /></Page>} />
      <Route path="/technical-analysis" element={<Page intraday><TechnicalAnalysis /></Page>} />
      <Route path="/trades" element={<Page intraday><Trades state={state} /></Page>} />
      <Route path="/journal" element={<Page intraday><Journal /></Page>} />
      <Route path="/jev-book" element={<Page intraday><JevBook /></Page>} />
      <Route path="/kronos" element={<Page intraday><Kronos /></Page>} />
      <Route path="/portfolio" element={<Page><Portfolio state={state} /></Page>} />
      <Route path="/portfolio/diagnostic" element={<Page><PortfolioDiagnostic /></Page>} />
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
