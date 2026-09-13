import { useNavigate } from "react-router-dom";

export default function SymLink({ sym }) {
  const navigate = useNavigate();
  return (
    <button className="symlink" onClick={() => navigate(`/stock/${encodeURIComponent(sym)}`)}>
      {sym}
    </button>
  );
}
