import React from 'react';
import { Shield, Lock, Terminal } from 'lucide-react';
import { Link } from 'react-router-dom';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full border-t border-slate-800/80 bg-[#05070a] text-slate-400 font-sans text-xs">
      {/* Sleek status / telemetry bar */}
      <div className="h-8 bg-[#0d1117]/80 backdrop-blur-md border-b border-slate-800/80 flex items-center px-4 sm:px-8 justify-between text-[10px] text-slate-500 font-mono">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5 text-slate-400">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
            <span>LATENCY: <strong className="text-slate-300">14ms</strong></span>
          </span>
          <span className="hidden sm:inline text-slate-700">|</span>
          <span className="hidden sm:inline">
            THREAT_LEVEL: <span className="text-red-400 font-bold">ELEVATED</span>
          </span>
          <span className="hidden md:inline text-slate-700">|</span>
          <span className="hidden md:inline text-slate-400">
            ENGINE: <strong className="text-cyan-400">D3-FORCE GRAPH</strong>
          </span>
        </div>

        <div className="flex items-center gap-4">
          <span className="hidden sm:inline text-slate-500 font-mono">NODE_ID: SIH_FINAL_DEMO_01</span>
          <span className="flex items-center gap-1.5 text-cyan-400 font-semibold font-mono">
            <span className="w-2 h-2 rounded-full bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.8)]" />
            SYSTEM_READY
          </span>
        </div>
      </div>

      {/* Main footer row */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex flex-col md:flex-row items-center justify-between gap-4 font-mono text-xs">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-cyan-400 font-bold">
            <Shield className="w-4 h-4 text-cyan-400" />
            <span>DECyPHER</span>
          </div>
          <span className="text-slate-700">•</span>
          <span className="text-slate-400 text-[11px]">CYBER RELATIONSHIP INTELLIGENCE PLATFORM</span>
        </div>

        <div className="flex flex-wrap items-center gap-4 text-[11px]">
          <Link to="/graph" className="text-slate-400 hover:text-cyan-400 transition-colors">
            Relationship Graph
          </Link>
          <span className="text-slate-700">•</span>
          <Link to="/actors/A00001" className="text-slate-400 hover:text-cyan-400 transition-colors">
            Actor A00001
          </Link>
          <span className="text-slate-700">•</span>
          <Link to="/reports/A00001" className="text-slate-400 hover:text-cyan-400 transition-colors">
            Attribution Briefing
          </Link>
        </div>

        <div className="flex items-center gap-3 text-[10px] text-slate-500">
          <span className="flex items-center gap-1">
            <Lock className="w-3 h-3 text-emerald-500" /> AES-256 ENCRYPTED
          </span>
          <span className="text-slate-700">|</span>
          <span className="flex items-center gap-1">
            <Terminal className="w-3 h-3 text-cyan-500" /> SIH DEMO READY
          </span>
        </div>
      </div>
    </footer>
  );
};
