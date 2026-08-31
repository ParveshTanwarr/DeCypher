import { Link } from "react-router-dom";

const signals = [
  { value: "3,000+", label: "Actors analyzed" },
  { value: "4,483", label: "Handles mapped" },
  { value: "550K", label: "Posts processed" },
];

export function HomePage() {
  return (
    <main className="home-page">
      <div className="home-grid" aria-hidden="true" />
      <div className="home-orbit home-orbit-one" aria-hidden="true" />
      <div className="home-orbit home-orbit-two" aria-hidden="true" />

      <nav className="home-nav">
        <Link to="/" className="brand">
          <span className="brand-mark">D</span>
          <span>
            <strong>DeCypher</strong>
            <small>RELATIONSHIP INTELLIGENCE</small>
          </span>
        </Link>

        <div className="home-nav-links">
          <Link to="/graph">Graph</Link>
          <Link to="/actors/ACT-001">Investigations</Link>
          <button
            className="theme-button"
            type="button"
            aria-label="Theme settings"
          >
            ◐
          </button>
        </div>
      </nav>

      <section className="home-hero">
        <div className="hero-copy">
          <div className="eyebrow">
            <span className="status-dot" />
            INTELLIGENCE PLATFORM · LIVE
          </div>

          <h1>
            Trace the
            <br />
            <span>hidden connections.</span>
          </h1>

          <p>
            DeCypher turns fragmented digital identities into an
            intelligence graph—connecting actors, handles, wallets,
            infrastructure and behavioral evidence.
          </p>

          <div className="hero-actions">
            <Link to="/graph" className="primary-action">
              Launch investigation
              <span>↗</span>
            </Link>

            <Link to="/graph" className="secondary-action">
              Explore the graph
            </Link>
          </div>

          <div className="hero-signals">
            {signals.map((signal) => (
              <div className="signal" key={signal.label}>
                <strong>{signal.value}</strong>
                <span>{signal.label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="hero-visual" aria-hidden="true">
          <div className="network-glow" />

          <div className="network-node node-center">
            <span>ACTOR</span>
            <strong>ACT-001</strong>
          </div>

          <div className="network-node node-one">
            <span>HANDLE</span>
            <strong>HND-042</strong>
          </div>

          <div className="network-node node-two">
            <span>WALLET</span>
            <strong>WLT-019</strong>
          </div>

          <div className="network-node node-three">
            <span>HANDLE</span>
            <strong>HND-118</strong>
          </div>

          <div className="network-node node-four">
            <span>ACTOR</span>
            <strong>ACT-014</strong>
          </div>

          <svg className="network-lines" viewBox="0 0 700 600">
            <line x1="350" y1="290" x2="145" y2="130" />
            <line x1="350" y1="290" x2="560" y2="135" />
            <line x1="350" y1="290" x2="155" y2="475" />
            <line x1="350" y1="290" x2="555" y2="460" />
            <line x1="145" y1="130" x2="560" y2="135" />
            <line x1="155" y1="475" x2="555" y2="460" />
          </svg>

          <div className="scan-line" />
        </div>
      </section>

      <div className="home-footer">
        <span>BEHAVIORAL INTELLIGENCE</span>
        <span>IDENTITY GRAPH</span>
        <span>FORENSIC CORRELATION</span>
      </div>
    </main>
  );
}