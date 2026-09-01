import React from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getActorProfile, MOCK_NODES } from '../data/mockGraph';
import { RiskBadge, ConfidenceScore } from '../components/ui/Badge';
import { 
  FileText, 
  ArrowLeft, 
  Network, 
  Printer, 
  ShieldAlert, 
  CheckCircle2, 
  AlertTriangle, 
  Fingerprint, 
  Layers, 
  Clock, 
  Lock,
  ChevronDown
} from 'lucide-react';

export const ReportPage: React.FC = () => {
  const { actorId = 'A00001' } = useParams<{ actorId: string }>();
  const navigate = useNavigate();
  const actor = getActorProfile(actorId);

  if (!actor) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center space-y-4">
        <h2 className="text-xl font-bold font-mono-code">Investigation Report Not Found</h2>
        <Link to="/graph" className="inline-flex items-center gap-2 px-4 py-2 rounded bg-cyan-500 text-black font-mono-code text-xs font-bold">
          <ArrowLeft className="w-4 h-4" /> Back to Graph
        </Link>
      </div>
    );
  }

  const allActors = MOCK_NODES.filter((n) => n.category === 'ACTOR');

  return (
    <div className="min-h-[calc(100vh-3.5rem)] bg-slate-100 dark:bg-[#070b12] text-slate-900 dark:text-slate-100 font-sans py-8 px-4 sm:px-6 lg:px-8 transition-colors">
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* TOP TOOLBAR */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-300 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(`/actors/${actor.id}`)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-mono-code text-slate-700 dark:text-slate-300 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Investigation</span>
            </button>

            <button
              onClick={() => navigate('/graph')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-mono-code text-slate-700 dark:text-slate-300 transition-colors"
            >
              <Network className="w-3.5 h-3.5 text-cyan-500" />
              <span>View Relationship Graph</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            {/* Actor quick switcher */}
            <div className="relative inline-block">
              <select
                aria-label="Switch Actor Report"
                value={actor.id}
                onChange={(e) => navigate(`/reports/${e.target.value}`)}
                className="pl-3 pr-8 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 font-mono-code text-xs appearance-none cursor-pointer focus:outline-none focus:ring-1 focus:ring-cyan-500"
              >
                {allActors.map((a) => (
                  <option key={a.id} value={a.id}>
                    Report: {a.id} ({a.risk?.toUpperCase()})
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
            </div>

            <button
              onClick={() => window.print()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-800 dark:bg-slate-800 hover:bg-slate-700 text-white font-mono-code text-xs font-medium transition-colors"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print Briefing</span>
            </button>
          </div>
        </div>

        {/* CLASSIFIED INTELLIGENCE DOSSIER / BRIEFING DOCUMENT */}
        <article 
          id="intelligence-report-document"
          className="rounded-xl border border-slate-300 dark:border-slate-800 bg-white dark:bg-[#0c121e] shadow-soft p-6 sm:p-10 space-y-8 print:border-none print:shadow-none"
        >
          {/* REPORT CLASSIFICATION HEADER */}
          <div className="border-b-2 border-slate-900 dark:border-slate-700 pb-6 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono-code font-extrabold text-sm tracking-widest text-cyan-600 dark:text-cyan-400">
                    DECyPHER
                  </span>
                  <span className="text-slate-300 dark:text-slate-700">|</span>
                  <span className="font-mono-code text-[11px] uppercase tracking-widest text-slate-500 dark:text-slate-400">
                    INVESTIGATION REPORT
                  </span>
                </div>
                <h1 className="text-2xl sm:text-3xl font-extrabold font-mono-code text-slate-900 dark:text-white tracking-tight">
                  TARGET DOSSIER: {actor.id}
                </h1>
                <p className="text-xs font-mono-code text-slate-500 dark:text-slate-400">
                  {actor.name} • CLUSTER ID: {actor.clusterId}
                </p>
              </div>

              {/* CLASSIFICATION BADGE */}
              <div className="flex flex-col items-end space-y-1.5">
                <div className="flex items-center gap-2">
                  <RiskBadge level={actor.risk} size="lg" />
                </div>
                <div className="font-mono-code text-xs text-slate-600 dark:text-slate-400">
                  CONFIDENCE: <strong className="text-cyan-600 dark:text-cyan-400 font-bold">{Math.round(actor.confidence * 100)}%</strong>
                </div>
                <div className="text-[10px] font-mono-code text-slate-400">
                  REF: DCY-INTEL-{actor.id}-2025
                </div>
              </div>
            </div>

            {/* MANDATORY ANALYTICAL INDICATIVE DISCLAIMER */}
            <div className="p-3 rounded-md bg-amber-500/10 dark:bg-amber-500/15 border border-amber-500/30 text-amber-800 dark:text-amber-300 text-xs font-mono-code flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
              <p className="leading-relaxed">
                <strong>EVIDENTIARY NOTICE:</strong> Evidence confidence is indicative and should be interpreted as an analytical signal rather than proof of identity.
              </p>
            </div>
          </div>

          {/* 1. EXECUTIVE SUMMARY */}
          <section className="space-y-3">
            <h2 className="font-mono-code font-bold text-xs uppercase tracking-widest text-cyan-600 dark:text-cyan-400 pb-1 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
              <span>1. EXECUTIVE SUMMARY</span>
            </h2>
            <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed font-sans">
              {actor.executiveSummary}
            </p>
          </section>

          {/* 2. RELATIONSHIP FINDINGS */}
          <section className="space-y-3">
            <h2 className="font-mono-code font-bold text-xs uppercase tracking-widest text-cyan-600 dark:text-cyan-400 pb-1 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
              <span>2. RELATIONSHIP FINDINGS</span>
            </h2>
            <ul className="space-y-2 text-xs sm:text-sm text-slate-700 dark:text-slate-300">
              {actor.relationshipFindings.map((finding, idx) => (
                <li key={idx} className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-cyan-500 shrink-0 mt-0.5" />
                  <span className="leading-relaxed">{finding}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* 3. BEHAVIORAL SIGNALS & STYLOMETRY */}
          <section className="space-y-3">
            <h2 className="font-mono-code font-bold text-xs uppercase tracking-widest text-cyan-600 dark:text-cyan-400 pb-1 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
              <span>3. BEHAVIORAL & STYLOMETRIC SIGNALS</span>
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {actor.behavioralSignals.map((sig, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono-code font-bold text-[11px] text-slate-800 dark:text-slate-200">
                      {sig.feature}
                    </span>
                    <span className="font-mono-code text-[11px] font-bold text-cyan-600 dark:text-cyan-400">
                      {Math.round(sig.similarityScore * 100)}%
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-400 font-sans leading-relaxed">
                    {sig.description}
                  </p>
                </div>
              ))}
            </div>
          </section>

          {/* 4. WALLET & INFRASTRUCTURE SIGNALS */}
          <section className="space-y-3">
            <h2 className="font-mono-code font-bold text-xs uppercase tracking-widest text-cyan-600 dark:text-cyan-400 pb-1 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
              <span>4. WALLET / INFRASTRUCTURE SIGNALS</span>
            </h2>
            <div className="space-y-2">
              {actor.infrastructureFindings.map((finding, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/40 text-xs font-mono-code text-slate-700 dark:text-slate-300 leading-relaxed"
                >
                  {finding}
                </div>
              ))}
            </div>
          </section>

          {/* 5. IDENTITY LIFECYCLE */}
          <section className="space-y-3">
            <h2 className="font-mono-code font-bold text-xs uppercase tracking-widest text-cyan-600 dark:text-cyan-400 pb-1 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
              <span>5. IDENTITY LIFECYCLE & REBRANDING</span>
            </h2>
            <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 space-y-2">
              <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed font-sans">
                {actor.lifecycleAnalysis}
              </p>
            </div>
          </section>

          {/* 6. CONFIDENCE ASSESSMENT */}
          <section className="space-y-3">
            <h2 className="font-mono-code font-bold text-xs uppercase tracking-widest text-cyan-600 dark:text-cyan-400 pb-1 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
              <span>6. CONFIDENCE ASSESSMENT</span>
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono-code text-xs">
              <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
                <span className="text-[10px] uppercase text-slate-400 block mb-1">Financial Linkage</span>
                <span className="text-base font-bold text-emerald-600 dark:text-emerald-400">94% High</span>
              </div>
              <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
                <span className="text-[10px] uppercase text-slate-400 block mb-1">Stylometry Linkage</span>
                <span className="text-base font-bold text-indigo-600 dark:text-indigo-400">91% High</span>
              </div>
              <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
                <span className="text-[10px] uppercase text-slate-400 block mb-1">Infrastructure Linkage</span>
                <span className="text-base font-bold text-cyan-600 dark:text-cyan-400">86% Probable</span>
              </div>
            </div>
          </section>

          {/* 7. FINAL ANALYST ASSESSMENT */}
          <section className="space-y-3 pt-2">
            <h2 className="font-mono-code font-bold text-xs uppercase tracking-widest text-cyan-600 dark:text-cyan-400 pb-1 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
              <span>7. FINAL ANALYST ASSESSMENT</span>
            </h2>
            <div className="p-4 rounded-lg border-2 border-cyan-500/40 bg-cyan-500/5 dark:bg-cyan-500/10 space-y-2">
              <p className="font-mono-code text-xs sm:text-sm font-semibold text-slate-900 dark:text-slate-100 leading-relaxed">
                {actor.finalAssessment}
              </p>
            </div>
          </section>

          {/* SIGNATURE / TELEMETRY FOOTER */}
          <div className="pt-6 border-t border-slate-300 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-[10px] font-mono-code text-slate-400">
            <div>
              AUTHORIZED BY: DECyPHER FORENSIC ENGINE v2.4
            </div>
            <div>
              INTELLIGENCE HASH: 8f9b2c3d4e5a6f7...1a2b
            </div>
          </div>
        </article>
      </div>
    </div>
  );
};
