import React from 'react';
import { useNavigate } from 'react-router-dom';
import { HeroNetworkVisual } from '../components/landing/HeroNetworkVisual';
import { 
  Network, 
  ArrowRight, 
  ShieldAlert, 
  Link2, 
  Fingerprint, 
  Clock, 
  Terminal,
  Activity,
  Layers,
  Search
} from 'lucide-react';

export const HomePage: React.FC = () => {
  const navigate = useNavigate();

  const statistics = [
    { value: '3,000+', label: 'ACTORS ANALYZED', description: 'De-anonymized entity clusters' },
    { value: '4,483', label: 'HANDLES MAPPED', description: 'Cross-platform identifier index' },
    { value: '550K+', label: 'POSTS PROCESSED', description: 'Underground forum & channel corpus' },
    { value: 'MULTI-SOURCE', label: 'CORRELATION', description: 'Heuristic & probabilistic graph engine' },
  ];

  const features = [
    {
      icon: Link2,
      title: 'IDENTITY CORRELATION',
      description: 'Connect fragmented handles and identities across platforms.',
      detail: 'Traverses PGP keys, forum metadata, Telegram handles, and darknet handles to cluster alias fragmentation.',
      tag: 'OSINT CORRELATION',
    },
    {
      icon: Layers,
      title: 'WALLET LINK ANALYSIS',
      description: 'Surface wallet reuse and shared financial infrastructure.',
      detail: 'Trace cryptocurrency deposit addresses, cashout tumblers, and shared smart contract interactions.',
      tag: 'BLOCKCHAIN TRACE',
    },
    {
      icon: Fingerprint,
      title: 'BEHAVIORAL SIGNALS',
      description: 'Use writing style and behavioral patterns as supporting evidence.',
      detail: 'Extract stylometric vocabulary fingerprints, punctuation habits, and timezone activity windows.',
      tag: 'NLP STYLOMETRY',
    },
    {
      icon: Clock,
      title: 'LIFECYCLE TRACKING',
      description: 'Visualize identity changes, dormancy and likely rebrands.',
      detail: 'Chronologically map tactical silence periods followed by rebrand emergence and persistent wallet usage.',
      tag: 'TIMELINE FORENSICS',
    },
  ];

  return (
    <div className="min-h-[calc(100vh-3.5rem)] flex flex-col justify-between cyber-grid font-sans">
      {/* HERO SECTION */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 sm:pt-14 pb-12 w-full">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-8 items-center">
          
          {/* LEFT: HERO COPY & ACTIONS */}
          <div className="lg:col-span-7 space-y-6">
            {/* System Status Pill */}
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 text-xs font-mono-code">
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500" />
              </span>
              <span className="font-semibold uppercase tracking-wider text-[11px]">
                CYBER INVESTIGATION PLATFORM
              </span>
            </div>

            {/* Headline */}
            <div className="space-y-2">
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-[1.1]">
                Trace the <span className="text-cyan-600 dark:text-cyan-400">hidden</span> connections.
              </h1>
              <p className="text-lg sm:text-xl font-medium text-slate-700 dark:text-slate-300 max-w-2xl leading-relaxed">
                Turn fragmented digital identities into an intelligence graph.
              </p>
            </div>

            {/* Supporting Copy */}
            <p className="text-sm sm:text-base text-slate-600 dark:text-slate-400 max-w-xl leading-relaxed">
              DECyPHER correlates actors, handles, wallets, infrastructure and behavioral evidence to reveal relationships that isolated data points cannot.
            </p>

            {/* CTA Buttons */}
            <div className="pt-2 flex flex-wrap items-center gap-3 sm:gap-4">
              <button
                id="launch-investigation-primary-btn"
                onClick={() => navigate('/graph')}
                className="flex items-center gap-2.5 px-6 py-3 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono-code font-bold text-sm tracking-wide transition-all shadow-md hover:shadow-cyan-500/25 focus:outline-none focus:ring-2 focus:ring-cyan-500 cursor-pointer"
              >
                <span>Launch Investigation</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                id="explore-graph-secondary-btn"
                onClick={() => navigate('/graph')}
                className="flex items-center gap-2 px-5 py-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200 font-mono-code font-medium text-sm transition-all shadow-sm focus:outline-none focus:ring-2 focus:ring-slate-400 cursor-pointer"
              >
                <Network className="w-4 h-4 text-cyan-500" />
                <span>Explore Relationship Graph</span>
              </button>
            </div>

            {/* SIH Live Demo Quick Targets */}
            <div className="pt-4 border-t border-slate-200 dark:border-slate-800/80">
              <div className="text-[11px] font-mono-code uppercase text-slate-500 dark:text-slate-400 mb-2 flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-cyan-500" />
                <span>DIRECT TARGET INVESTIGATION:</span>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={() => navigate('/actors/A00001')}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 font-mono-code text-xs font-semibold transition-colors"
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>Target A00001 (Critical Risk • 92%)</span>
                </button>

                <button
                  onClick={() => navigate('/actors/A00042')}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-orange-500/30 bg-orange-500/10 hover:bg-orange-500/20 text-orange-600 dark:text-orange-400 font-mono-code text-xs font-semibold transition-colors"
                >
                  <span>Target A00042 (Exploit Broker)</span>
                </button>
              </div>
            </div>
          </div>

          {/* RIGHT: INTERACTIVE ANIMATED NETWORK VISUAL */}
          <div className="lg:col-span-5">
            <HeroNetworkVisual />
          </div>
        </div>
      </section>

      {/* STATISTICS SUMMARY STRIP */}
      <section className="border-y border-slate-200/90 dark:border-slate-800/90 bg-white/70 dark:bg-[#0c121e]/80 backdrop-blur-md py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-4">
            {statistics.map((stat, i) => (
              <div key={i} className="flex flex-col space-y-1">
                <span className="text-2xl sm:text-3xl font-extrabold font-mono-code tracking-tight text-cyan-600 dark:text-cyan-400">
                  {stat.value}
                </span>
                <span className="text-xs font-mono-code uppercase tracking-wider font-bold text-slate-800 dark:text-slate-200">
                  {stat.label}
                </span>
                <span className="text-[11px] text-slate-500 dark:text-slate-400">
                  {stat.description}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FEATURE STRIP SECTION */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <span className="text-[10px] font-mono-code uppercase tracking-widest text-cyan-600 dark:text-cyan-400 font-bold">
              ANALYTICAL CAPABILITIES
            </span>
            <h2 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white">
              Multi-Layer Relationship Intelligence
            </h2>
          </div>
          <button
            onClick={() => navigate('/graph')}
            className="hidden sm:flex items-center gap-1 text-xs font-mono-code text-cyan-600 dark:text-cyan-400 hover:underline"
          >
            <span>Open Graph Engine</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((f, idx) => {
            const Icon = f.icon;
            return (
              <div
                key={idx}
                className="p-5 rounded-xl border border-slate-200/90 dark:border-slate-800/90 bg-white/80 dark:bg-[#0c121e]/70 backdrop-blur hover:border-cyan-500/40 dark:hover:border-cyan-500/50 transition-all group flex flex-col justify-between shadow-soft"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-900 text-cyan-600 dark:text-cyan-400 group-hover:bg-cyan-500/10 transition-colors">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[9px] font-mono-code px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800/80 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                      {f.tag}
                    </span>
                  </div>

                  <h3 className="font-mono-code font-bold text-sm text-slate-900 dark:text-white mb-1.5 tracking-tight">
                    {f.title}
                  </h3>

                  <p className="text-xs text-slate-700 dark:text-slate-300 font-medium mb-2 leading-relaxed">
                    {f.description}
                  </p>
                </div>

                <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-normal pt-2 border-t border-slate-100 dark:border-slate-800/60">
                  {f.detail}
                </p>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
};
