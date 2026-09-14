import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";
import { useAppState } from "./api";
import Header from "./components/Header";
import Overview from "./pages/Overview";
import Screener from "./pages/Screener";
import Stock from "./pages/Stock";
import TechnicalAnalysis from "./pages/TechnicalAnalysis";
import Portfolio from "./pages/Portfolio";
import PortfolioDiagnostic from "./pages/PortfolioDiagnostic";
import Journal from "./pages/Journal";
import Trades from "./pages/Trades";

function Page({ children }) {
  const location = useLocation();
  return <main className="page" key={location.pathname}>{children}</main>;
}

function AppRoutes({ state }) {
  if (!state) return <Page><p className="empty">Connecting…</p></Page>;
  return (
    <Routes>
      <Route path="/" element={<Page><Overview state={state} /></Page>} />
      <Route path="/screener" element={<Page><Screener state={state} /></Page>} />
      <Route path="/stock/:symbol" element={<Page><Stock state={state} /></Page>} />
      <Route path="/technical-analysis" element={<Page><TechnicalAnalysis /></Page>} />
      <Route path="/portfolio" element={<Page><Portfolio state={state} /></Page>} />
      <Route path="/portfolio/diagnostic" element={<Page><PortfolioDiagnostic /></Page>} />
      <Route path="/journal" element={<Page><Journal /></Page>} />
      <Route path="/trades" element={<Page><Trades state={state} /></Page>} />
    </Routes>
  );
}

function Shell() {
  const state = useAppState();
  return (
    <>
      <Header state={state} />
      <AppRoutes state={state} />
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  );
}
