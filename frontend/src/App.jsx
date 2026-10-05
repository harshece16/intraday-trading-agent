import { lazy, Suspense, useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { API_BASE, useAppState } from "./api";
import LoadState from "./components/LoadState";
import PageErrorBoundary from "./components/PageErrorBoundary";
import { useAlerts } from "./useAlerts";
import StatusBar, { Sidebar } from "./components/Header";
import LiveLog from "./components/LiveLog";
import IntradayRecordBanner from "./components/IntradayRecordBanner";

// Each page is its own chunk, loaded when first opened: the front page no
// longer downloads every page and the chart library (README section 120).
const Overview = lazy(() => import("./pages/Overview"));
const PreMarket = lazy(() => import("./pages/PreMarket"));
const DayPlan = lazy(() => import("./pages/DayPlan"));
const Screener = lazy(() => import("./pages/Screener"));
const Stock = lazy(() => import("./pages/Stock"));
const TechnicalAnalysis = lazy(() => import("./pages/TechnicalAnalysis"));
const Portfolio = lazy(() => import("./pages/Portfolio"));
const PortfolioDiagnostic = lazy(() => import("./pages/PortfolioDiagnostic"));
const Journal = lazy(() => import("./pages/Journal"));
const Trades = lazy(() => import("./pages/Trades"));
const MomentumBook = lazy(() => import("./pages/MomentumBook"));
const JevBook = lazy(() => import("./pages/JevBook"));
const Kronos = lazy(() => import("./pages/Kronos"));
const RuleLab = lazy(() => import("./pages/RuleLab"));
const PaperDesk = lazy(() => import("./pages/PaperDesk"));
const ProcessLog = lazy(() => import("./pages/ProcessLog"));

// `intraday` marks a page of the intraday paper record: it opens with the
// banner that says so (README section 116).
function Page({ children, intraday = false }) {
  const location = useLocation();
  return (
    <main className="page" key={location.pathname}>
      {intraday && <IntradayRecordBanner />}
      <Suspense fallback={<LoadState label="Loading the page…" />}>{children}</Suspense>
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

// Pages that don't read the live state are built once, so the 3 s state push
// doesn't re-render them: React skips an element it has already rendered.
const DESK = <Page><PaperDesk /></Page>;
const PROCESS_LOG = <Page><ProcessLog /></Page>;
const MOMENTUM = <Page><MomentumBook /></Page>;
const DAY_PLAN = <Page intraday><DayPlan /></Page>;
const TECHNICAL = <Page intraday><TechnicalAnalysis /></Page>;
const JOURNAL = <Page intraday><Journal /></Page>;
const JEV = <Page intraday><JevBook /></Page>;
const KRONOS = <Page intraday><Kronos /></Page>;
const RULE_LAB = <Page intraday><RuleLab /></Page>;
const DIAGNOSTIC = <Page><PortfolioDiagnostic /></Page>;

function AppRoutes({ state }) {
  if (!state) return <Page><Connecting /></Page>;
  return (
    <Routes>
      {/* The paper desk is the front page: four paper books as equal experiments, and one
          process log (README section 125). No book is the strategy. */}
      <Route path="/" element={DESK} />
      <Route path="/paper-desk" element={<Redirect to="/" />} />
      <Route path="/process-log" element={PROCESS_LOG} />
      <Route path="/momentum-book" element={MOMENTUM} />
      {/* The intraday engine's pages: a paper record, each under the banner. */}
      <Route path="/intraday" element={<Page intraday><Overview state={state} /></Page>} />
      <Route path="/overview" element={<Redirect to="/intraday" />} />
      <Route path="/premarket" element={<Page intraday><PreMarket state={state} /></Page>} />
      <Route path="/day-plan" element={DAY_PLAN} />
      <Route path="/screener" element={<Page intraday><Screener state={state} /></Page>} />
      <Route path="/stock/:symbol" element={<Page intraday><Stock state={state} /></Page>} />
      <Route path="/technical-analysis" element={TECHNICAL} />
      <Route path="/trades" element={<Page intraday><Trades state={state} /></Page>} />
      <Route path="/journal" element={JOURNAL} />
      <Route path="/jev-book" element={JEV} />
      <Route path="/kronos" element={KRONOS} />
      <Route path="/rule-lab" element={RULE_LAB} />
      <Route path="/portfolio" element={<Page><Portfolio state={state} /></Page>} />
      <Route path="/portfolio/diagnostic" element={DIAGNOSTIC} />
    </Routes>
  );
}

function Shell() {
  const state = useAppState();
  const { pathname } = useLocation();
  useAlerts(state);
  const [liveLogOpen, setLiveLogOpen] = useState(false);
  return (
    <div className="app">
      <Sidebar state={state} liveLogOpen={liveLogOpen} onToggleLiveLog={() => setLiveLogOpen((v) => !v)} />
      <div className="app-main">
        <StatusBar state={state} />
        <PageErrorBoundary key={pathname}>
          <AppRoutes state={state} />
        </PageErrorBoundary>
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
