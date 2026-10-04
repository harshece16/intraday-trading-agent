import { Link } from "react-router-dom";

/** A stock's name as a real link: keyboard, middle-click and new tab work (#244). */
export default function SymLink({ sym }) {
  return <Link className="symlink" to={`/stock/${encodeURIComponent(sym)}`}>{sym}</Link>;
}
