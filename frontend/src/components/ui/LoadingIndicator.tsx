import React from 'react';
import { Shield, Radio } from 'lucide-react';

interface LoadingIndicatorProps {
  message?: string;
  submessage?: string;
}

export const LoadingIndicator: React.FC<LoadingIndicatorProps> = ({
  message = 'CORRELATING IDENTITIES...',
  submessage = 'Traversing relationship nodes and cryptographic clusters',
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center space-y-4 animate-in fade-in duration-300">
      {/* Visual cyber orbit network */}
      <div className="relative w-20 h-20 flex items-center justify-center">
        {/* Outer rotating dashed ring */}
        <div className="absolute inset-0 rounded-full border border-cyan-500/30 dark:border-cyan-400/40 border-dashed animate-spin [animation-duration:8s]" />
        
        {/* Inner reverse rotating ring */}
        <div className="absolute inset-2 rounded-full border-t-2 border-r-2 border-indigo-500/60 dark:border-indigo-400/70 border-b-transparent border-l-transparent animate-spin [animation-duration:3s] [animation-direction:reverse]" />
        
        {/* Glowing pulse core */}
        <div className="w-10 h-10 rounded-full bg-cyan-500/10 dark:bg-cyan-500/20 border border-cyan-500/50 flex items-center justify-center shadow-[0_0_15px_rgba(6,182,212,0.4)]">
          <Shield className="w-5 h-5 text-cyan-600 dark:text-cyan-400 animate-pulse" />
        </div>

        {/* Orbiting satellite node */}
        <div className="absolute -top-1 w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.9)] animate-ping [animation-duration:2s]" />
      </div>

      <div className="space-y-1">
        <div className="flex items-center justify-center gap-2">
          <Radio className="w-3.5 h-3.5 text-cyan-500 animate-pulse" />
          <span className="font-mono-code text-xs tracking-widest text-cyan-600 dark:text-cyan-400 font-bold uppercase">
            DECyPHER
          </span>
        </div>
        <h4 className="font-mono-code text-sm font-semibold tracking-wider text-slate-800 dark:text-slate-200">
          {message}
        </h4>
        {submessage && (
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-xs mx-auto">
            {submessage}
          </p>
        )}
      </div>
    </div>
  );
};
