import type { NodeCategory } from "../../types/graph";

const filterOptions: Array<{ category: NodeCategory; label: string }> = [
  { category: "actor", label: "Actors" },
  { category: "handle", label: "Handles" },
  { category: "wallet", label: "Wallets" },
];

interface GraphControlsProps {
  selectedCategories: Set<NodeCategory>;
  onToggleCategory: (category: NodeCategory) => void;
  onReset: () => void;
}

export function GraphControls({
  selectedCategories,
  onToggleCategory,
  onReset,
}: GraphControlsProps) {
  return (
    <section className="panel controls-panel" aria-label="Graph filters">
      <div className="panel-heading">
        <h2>Filters</h2>
        <button className="text-button" type="button" onClick={onReset}>
          Reset
        </button>
      </div>
      <div className="filter-list">
        {filterOptions.map((option) => (
          <label className="check-row" key={option.category}>
            <input
              type="checkbox"
              checked={selectedCategories.has(option.category)}
              onChange={() => onToggleCategory(option.category)}
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </section>
  );
}
