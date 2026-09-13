import { GLOSSARY } from "../format";

/** A hover/focus-explained term. `k` looks up GLOSSARY; pass `explain` directly to skip the lookup. */
export default function Tip({ k, explain, children }) {
  const text = explain || GLOSSARY[k] || k;
  return (
    <span className="tip" tabIndex={0} data-tip={text}>
      {children}
    </span>
  );
}
