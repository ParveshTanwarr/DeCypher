import type { NodeCategory, RiskLevel } from "../../types/graph";

const categoryItems: Array<{ category: NodeCategory; label: string }> = [
  { category: "actor", label: "Actor" },
  { category: "handle", label: "Handle" },
  { category: "wallet", label: "Wallet" },
];

const riskItems: Array<{ risk: RiskLevel; label: string }> = [
  { risk: "critical", label: "Critical risk" },
  { risk: "high", label: "High risk" },
  { risk: "medium", label: "Medium risk" },
  { risk: "low", label: "Low risk" },
];

export function GraphLegend() {
  return (
    <section className="panel legend-panel" aria-label="Graph legend">
      <h2>Legend</h2>
      <div className="legend-group">
        {categoryItems.map((item) => (
          <div className="legend-row" key={item.category}>
            <span className={`legend-node legend-node-${item.category}`} />
            <span>{item.label}</span>
          </div>
        ))}
      </div>
      <div className="legend-group">
        {riskItems.map((item) => (
          <div className="legend-row" key={item.risk}>
            <span className={`legend-risk legend-risk-${item.risk}`} />
            <span>{item.label}</span>
          </div>
        ))}
      </div>
      <div className="legend-note">Larger nodes and stronger links indicate higher confidence.</div>
    </section>
  );
}
