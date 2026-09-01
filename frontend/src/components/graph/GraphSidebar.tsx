import React from 'react';
import { FilterState } from '../../types/graph';
import { 
  Filter, 
  RotateCcw, 
  Search, 
  Layers, 
  AlertTriangle, 
  Gauge, 
  X
} from 'lucide-react';

interface GraphSidebarProps {
  filters: FilterState;
  onFilterChange: (filters: FilterState) => void;
  onResetFilters: () => void;
  onResetZoom: () => void;
  isOpen: boolean;
  onToggleOpen: () => void;
}

export const GraphSidebar: React.FC<GraphSidebarProps> = ({
  filters,
  onFilterChange,
  onResetFilters,
  onResetZoom,
  isOpen,
  onToggleOpen,
}) => {
  const handleNodeTypeToggle = (key: keyof FilterState['nodeTypes']) => {
    onFilterChange({
      ...filters,
      nodeTypes: {
        ...filters.nodeTypes,
        [key]: !filters.nodeTypes[key],
      },
    });
  };

  const handleRiskToggle = (key: keyof FilterState['riskLevels']) => {
    onFilterChange({
      ...filters,
      riskLevels: {
        ...filters.riskLevels,
        [key]: !filters.riskLevels[key],
      },
    });
  };

  const handleConfidenceChange = (val: FilterState['confidenceThreshold']) => {
    onFilterChange({
      ...filters,
      confidenceThreshold: val,
    });
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      ...filters,
      searchTerm: e.target.value,
    });
  };

  return (
    <>
      {/* Mobile toggle button if closed */}
      {!isOpen && (
        <button
          onClick={onToggleOpen}
          aria-label="Open Filter Controls"
          className="md:hidden absolute top-4 left-4 z-20 flex items-center gap-1.5 px-3 py-2 rounded-md bg-slate-900/90 text-white border border-slate-700 shadow-md text-xs font-mono-code"
        >
          <Filter className="w-3.5 h-3.5 text-cyan-400" />
          <span>Filters</span>
        </button>
      )}

      {/* Control Panel Container */}
      <aside
        aria-label="Graph Filter Controls"
        className={`absolute top-4 left-4 z-20 w-72 rounded-xl border border-slate-700/60 bg-[#0d1117]/85 backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.7)] ring-1 ring-white/5 p-4 transition-all duration-300 font-sans text-xs ${
          isOpen ? 'translate-x-0 opacity-100' : '-translate-x-full md:translate-x-0 opacity-0 md:opacity-100 pointer-events-none md:pointer-events-auto'
        }`}
      >
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-cyan-400" />
            <span className="font-mono-code font-bold text-xs uppercase tracking-widest text-white">
              INTELLIGENCE FILTERS
            </span>
          </div>
          <button
            onClick={onToggleOpen}
            aria-label="Close sidebar"
            className="md:hidden p-1 rounded hover:bg-slate-800 text-slate-400"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Quick Search */}
        <div className="mt-3">
          <label htmlFor="graph-search-input" className="block text-[10px] font-mono-code uppercase tracking-wider text-slate-500 mb-1 font-semibold">
            ENTITY SEARCH
          </label>
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            <input
              id="graph-search-input"
              type="text"
              placeholder="Search actor, handle, wallet..."
              value={filters.searchTerm}
              onChange={handleSearchChange}
              className="w-full pl-8 pr-3 py-1.5 rounded bg-slate-900 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono-code text-[11px] transition-colors"
            />
            {filters.searchTerm && (
              <button
                onClick={() => onFilterChange({ ...filters, searchTerm: '' })}
                className="absolute right-2 top-2 text-slate-400 hover:text-white"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        <div className="space-y-4 mt-4">
          {/* SECTION 1: NODE TYPES */}
          <div>
            <div className="flex items-center gap-1.5 text-[10px] font-mono-code uppercase tracking-widest text-slate-500 font-semibold mb-2">
              <Layers className="w-3 h-3 text-cyan-400" />
              <span>NODE TYPES</span>
            </div>
            <div className="space-y-1.5 pl-1">
              <label className="flex items-center justify-between p-1.5 rounded bg-slate-900/50 hover:bg-slate-900 border border-slate-800/80 cursor-pointer select-none text-slate-300 hover:text-white transition-colors">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={filters.nodeTypes.actors}
                    onChange={() => handleNodeTypeToggle('actors')}
                    className="rounded border-slate-700 text-cyan-500 focus:ring-cyan-500/30 accent-cyan-500 w-3.5 h-3.5"
                  />
                  <span className="w-2 h-2 rounded-sm bg-cyan-400 shadow-[0_0_6px_rgba(6,182,212,0.6)]" />
                  <span className="font-semibold text-xs text-slate-200">Actors</span>
                </div>
                <span className="font-mono-code text-[9px] text-cyan-400 bg-cyan-500/10 px-1 py-0.5 rounded border border-cyan-500/20">
                  PRIMARY
                </span>
              </label>

              <label className="flex items-center justify-between p-1.5 rounded bg-slate-900/50 hover:bg-slate-900 border border-slate-800/80 cursor-pointer select-none text-slate-300 hover:text-white transition-colors">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={filters.nodeTypes.handles}
                    onChange={() => handleNodeTypeToggle('handles')}
                    className="rounded border-slate-700 text-indigo-500 focus:ring-indigo-500/30 accent-indigo-500 w-3.5 h-3.5"
                  />
                  <span className="w-2 h-2 rounded-sm bg-indigo-400 shadow-[0_0_6px_rgba(99,102,241,0.6)]" />
                  <span className="font-semibold text-xs text-slate-200">Handles</span>
                </div>
                <span className="font-mono-code text-[9px] text-indigo-400 bg-indigo-500/10 px-1 py-0.5 rounded border border-indigo-500/20">
                  ONLINE
                </span>
              </label>

              <label className="flex items-center justify-between p-1.5 rounded bg-slate-900/50 hover:bg-slate-900 border border-slate-800/80 cursor-pointer select-none text-slate-300 hover:text-white transition-colors">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={filters.nodeTypes.wallets}
                    onChange={() => handleNodeTypeToggle('wallets')}
                    className="rounded border-slate-700 text-emerald-500 focus:ring-emerald-500/30 accent-emerald-500 w-3.5 h-3.5"
                  />
                  <span className="w-2 h-2 rounded-sm bg-emerald-400 shadow-[0_0_6px_rgba(16,185,129,0.6)]" />
                  <span className="font-semibold text-xs text-slate-200">Wallets</span>
                </div>
                <span className="font-mono-code text-[9px] text-emerald-400 bg-emerald-500/10 px-1 py-0.5 rounded border border-emerald-500/20">
                  CRYPTO
                </span>
              </label>
            </div>
          </div>

          {/* SECTION 2: RISK LEVELS */}
          <div>
            <div className="flex items-center gap-1.5 text-[10px] font-mono-code uppercase tracking-widest text-slate-500 font-semibold mb-2">
              <AlertTriangle className="w-3 h-3 text-amber-500" />
              <span>RISK SEVERITY</span>
            </div>
            <div className="grid grid-cols-2 gap-1.5 pl-1">
              <label className="flex items-center gap-1.5 p-1.5 rounded bg-slate-900/40 border border-slate-800/70 cursor-pointer select-none text-slate-300 hover:bg-slate-900">
                <input
                  type="checkbox"
                  checked={filters.riskLevels.critical}
                  onChange={() => handleRiskToggle('critical')}
                  className="rounded border-slate-700 text-rose-500 accent-rose-500 w-3 h-3"
                />
                <span className="w-2 h-2 rounded-sm bg-red-500" />
                <span className="font-mono-code text-[11px]">Critical</span>
              </label>

              <label className="flex items-center gap-1.5 p-1.5 rounded bg-slate-900/40 border border-slate-800/70 cursor-pointer select-none text-slate-300 hover:bg-slate-900">
                <input
                  type="checkbox"
                  checked={filters.riskLevels.high}
                  onChange={() => handleRiskToggle('high')}
                  className="rounded border-slate-700 text-orange-500 accent-orange-500 w-3 h-3"
                />
                <span className="w-2 h-2 rounded-sm bg-orange-500" />
                <span className="font-mono-code text-[11px]">High</span>
              </label>

              <label className="flex items-center gap-1.5 p-1.5 rounded bg-slate-900/40 border border-slate-800/70 cursor-pointer select-none text-slate-300 hover:bg-slate-900">
                <input
                  type="checkbox"
                  checked={filters.riskLevels.medium}
                  onChange={() => handleRiskToggle('medium')}
                  className="rounded border-slate-700 text-amber-500 accent-amber-500 w-3 h-3"
                />
                <span className="w-2 h-2 rounded-sm bg-amber-500" />
                <span className="font-mono-code text-[11px]">Medium</span>
              </label>

              <label className="flex items-center gap-1.5 p-1.5 rounded bg-slate-900/40 border border-slate-800/70 cursor-pointer select-none text-slate-300 hover:bg-slate-900">
                <input
                  type="checkbox"
                  checked={filters.riskLevels.low}
                  onChange={() => handleRiskToggle('low')}
                  className="rounded border-slate-700 text-emerald-500 accent-emerald-500 w-3 h-3"
                />
                <span className="w-2 h-2 rounded-sm bg-emerald-500" />
                <span className="font-mono-code text-[11px]">Low</span>
              </label>
            </div>
          </div>

          {/* SECTION 3: CONFIDENCE THRESHOLD */}
          <div>
            <div className="flex items-center gap-1.5 text-[10px] font-mono-code uppercase tracking-widest text-slate-500 font-semibold mb-2">
              <Gauge className="w-3 h-3 text-cyan-400" />
              <span>CONFIDENCE THRESHOLD</span>
            </div>
            <div className="grid grid-cols-4 gap-1 p-1 rounded border border-slate-800 bg-slate-900 font-mono-code text-[10px]">
              {(['all', 'high', 'medium', 'low'] as const).map((tier) => (
                <button
                  key={tier}
                  onClick={() => handleConfidenceChange(tier)}
                  className={`py-1 rounded capitalize transition-colors ${
                    filters.confidenceThreshold === tier
                      ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {tier}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* BUTTON ACTIONS */}
        <div className="mt-5 pt-3 border-t border-slate-800 flex items-center gap-2">
          <button
            id="reset-view-btn"
            onClick={onResetZoom}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 font-mono-code text-[11px] font-semibold tracking-wider transition-colors border border-slate-700"
          >
            <RotateCcw className="w-3 h-3 text-cyan-400" />
            <span>RESET VIEWPORT</span>
          </button>
          
          <button
            id="reset-filters-btn"
            onClick={onResetFilters}
            className="flex items-center justify-center py-2 px-2.5 rounded border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 text-[11px] font-mono-code transition-colors"
            title="Reset all filter selections"
          >
            Reset
          </button>
        </div>
      </aside>
    </>
  );
};
