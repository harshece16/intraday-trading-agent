import { Component } from "react";

/**
 * Catches a crash inside one page so the header, the Paper/Live switch, the
 * sidebar and the live log stay up (#238). Keyed on the path by App.jsx, so
 * moving to another page clears it.
 */
export default class PageErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("Page crashed:", error, info?.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <main className="page">
        <div className="load-error" role="alert">
          <b>This page hit an error and stopped</b>: {String(this.state.error?.message || this.state.error)}.{" "}
          The rest of the dashboard still works, including the Paper/Live switch above.{" "}
          <button className="more" onClick={() => this.setState({ error: null })}>Try again</button>
        </div>
      </main>
    );
  }
}
