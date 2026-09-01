import React, { useState } from 'react';
import { Info, ChevronDown, ChevronUp } from 'lucide-react';

export const GraphLegend: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="absolute bottom-4 left-4 z-20 w-64 rounded-xl border border-slate-700/60 bg-[#0d1117]/85 backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.7)] ring-1 ring-white/5 p-3 font-sans text-xs transition-all">
      <div 
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-between cursor-pointer select-none pb-1"
      >
        <div className="flex items-center gap-1.5 font-mono-code font-bold text-[11px] uppercase tracking-widest text-slate-300">
          <Info className="w-3.5 h-3.5 text-cyan-400" />
          <span>GRAPH LEGEND</span>
        </div>
        <button className="text-slate-500 hover:text-white">
          {collapsed ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {!collapsed && (
        <div className="mt-2 space-y-2.5 pt-2 border-t border-slate-800/80">
          {/* ENTITY TYPES */}
          <div>
            <span className="text-[9px] font-mono-code uppercase text-slate-500 tracking-widest font-semibold">
              Entity Category
            </span>
            <div className="grid grid-cols-3 gap-1 mt-1 font-mono-code text-[10px]">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-sm bg-cyan-400 shadow-[0_0_6px_rgba(6,182,212,0.8)]" />
                <span className="text-slate-300">Actor</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-sm bg-indigo-400 shadow-[0_0_6px_rgba(99,102,241,0.8)]" />
                <span className="text-slate-300">Handle</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-sm bg-emerald-400 shadow-[0_0_6px_rgba(16,185,129,0.8)]" />
                <span className="text-slate-300">Wallet</span>
              </div>
            </div>
          </div>

          {/* RISK CLASSIFICATION */}
          <div>
            <span className="text-[9px] font-mono-code uppercase text-slate-500 tracking-widest font-semibold">
              Actor Risk Halo
            </span>
            <div className="grid grid-cols-4 gap-1 mt-1 text-[10px] font-mono-code">
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-sm bg-red-500" />
                <span className="text-red-400 font-semibold">Crit</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-sm bg-orange-500" />
                <span className="text-orange-400 font-semibold">High</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-sm bg-amber-500" />
                <span className="text-amber-400 font-semibold">Med</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-sm bg-emerald-500" />
                <span className="text-emerald-400 font-semibold">Low</span>
              </div>
            </div>
          </div>

          {/* EXPLANATORY HINTS */}
          <div className="pt-2 border-t border-slate-800 text-[10px] text-slate-400 space-y-0.5 leading-tight font-mono">
            <p>• Node size indicates centrality.</p>
            <p>• Edge width indicates confidence.</p>
          </div>
        </div>
      )}
    </div>
  );
};
