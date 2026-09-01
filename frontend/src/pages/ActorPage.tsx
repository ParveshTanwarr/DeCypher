import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getActorProfile, getActorMiniGraphData, MOCK_NODES } from '../data/mockGraph';
import { RiskBadge, ConfidenceScore, CategoryBadge } from '../components/ui/Badge';
import { RelationshipGraph } from '../components/graph/RelationshipGraph';
import { useChat } from '../context/ChatContext';
import { FilterState } from '../types/graph';
import { 
  ShieldAlert, 
  ArrowLeft, 
  FileText, 
  Network, 
  Fingerprint, 
  Clock, 
  AtSign, 
  Wallet, 
  ExternalLink,
  ChevronRight,
  Sparkles,
  Layers,
  ArrowDown,
  Bot
} from 'lucide-react';

export const ActorPage: React.FC = () => {
  const { actorId = 'A00001' } = useParams<{ actorId: string }>();
  const navigate = useNavigate();
  const { sendMessage, setIsOpen, setActiveContext } = useChat();

  const actor = getActorProfile(actorId);
  const miniGraphData = getActorMiniGraphData(actorId);

  // Set active context for Gemini
  useEffect(() => {
    if (actor) {
      setActiveContext({
        currentPage: `/actors/${actor.id}`,
        currentActorId: actor.id,
        currentActorData: {
          id: actor.id,
          name: actor.name,
          risk: actor.risk,
          confidence: actor.confidence,
          handles: actor.handles,
          wallets: actor.wallets,
          summary: actor.summary,
        },
      });
    }
  }, [actor, setActiveContext]);

  const handleAskGemini = () => {
    if (!actor) return;
    setIsOpen(true);
    sendMessage(`Please provide an in-depth threat intelligence analysis for Actor ${actor.id} (${actor.name}), evaluating attribution signals, cryptocurrency flow, and risk factors.`);
  };

  // Animated sequential timeline entrance
  const [revealedEvents, setRevealedEvents] = useState<number>(0);

  useEffect(() => {
    setRevealedEvents(0);
    if (!actor) return;

    const interval = setInterval(() => {
      setRevealedEvents((prev) => {
        if (prev < actor.timeline.length) {
          return prev + 1;
        }
        clearInterval(interval);
        return prev;
      });
    }, 280);

    return () => clearInterval(interval);
  }, [actorId, actor]);

  if (!actor) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center space-y-4">
        <h2 className="text-xl font-bold font-mono-code">Actor Identifier Not Found</h2>
        <p className="text-sm text-slate-500">The requested threat cluster was not recognized.</p>
        <Link to="/graph" className="inline-flex items-center gap-2 px-4 py-2 rounded bg-cyan-500 text-black font-mono-code text-xs font-bold">
          <ArrowLeft className="w-4 h-4" /> Back to Graph
        </Link>
      </div>
    );
  }

  const defaultFilters: FilterState = {
    nodeTypes: { actors: true, handles: true, wallets: true },
    riskLevels: { critical: true, high: true, medium: true, low: true },
    confidenceThreshold: 'all',
    searchTerm: '',
  };

  return (
    <div className="min-h-[calc(100vh-3.5rem)] bg-[#070b12] text-slate-100 cyber-grid font-sans pb-16">
      {/* TOP ANALYST BREADCRUMB & ACTIONS */}
      <div className="border-b border-slate-800 bg-[#0c121e]/90 backdrop-blur-md px-4 sm:px-6 lg:px-8 py-3">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs font-mono-code text-slate-400">
            <Link to="/graph" className="hover:text-cyan-400 flex items-center gap-1">
              <Network className="w-3.5 h-3.5" />
              <span>RELATIONSHIP GRAPH</span>
            </Link>
            <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
            <span className="text-cyan-400 font-bold">ACTOR INVESTIGATION</span>
            <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
            <span className="text-slate-200">{actor.id}</span>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={handleAskGemini}
              id="actor-ask-gemini-btn"
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-md border border-cyan-500/40 bg-cyan-500/10 hover:bg-cyan-500/20 text-xs font-mono-code text-cyan-300 font-semibold transition-all shadow-[0_0_12px_rgba(6,182,212,0.15)]"
            >
              <Bot className="w-3.5 h-3.5 text-cyan-400" />
              <span>Ask Gemini Copilot</span>
            </button>

            <button
              onClick={() => navigate('/graph')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-700 bg-slate-900/80 hover:bg-slate-800 text-xs font-mono-code text-slate-300 transition-colors"
            >
              <Network className="w-3.5 h-3.5 text-cyan-400" />
              <span>View In Full Graph</span>
            </button>

            <button
              id="view-report-btn"
              onClick={() => navigate(`/reports/${actor.id}`)}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono-code text-xs font-bold transition-all shadow-md hover:shadow-cyan-500/20"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Generate Investigation Report</span>
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 space-y-6">
        {/* ACTOR HERO HEADER */}
        <div className="p-6 rounded-xl border border-slate-800 bg-[#0c121e]/90 backdrop-blur-md shadow-soft flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono-code font-bold uppercase tracking-widest text-cyan-400">
                ACTOR INVESTIGATION WORKSPACE
              </span>
              <span className="text-slate-600">•</span>
              <span className="text-[11px] font-mono-code text-slate-400">
                FIRST SEEN: {actor.firstSeen}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl sm:text-3xl font-extrabold font-mono-code text-white tracking-tight">
                {actor.id}
              </h1>
              <span className="text-lg text-slate-400 font-mono-code font-light">/</span>
              <span className="text-base sm:text-lg text-slate-300 font-semibold">
                {actor.name}
              </span>
              <RiskBadge level={actor.risk} size="md" />
            </div>

            <p className="text-xs sm:text-sm text-slate-400 max-w-3xl leading-relaxed">
              {actor.summary}
            </p>
          </div>

          <div className="flex sm:flex-col items-end justify-between sm:justify-center border-t sm:border-t-0 sm:border-l border-slate-800 pt-3 sm:pt-0 sm:pl-6 space-y-1">
            <span className="text-[10px] font-mono-code uppercase text-slate-400 tracking-wider">
              OVERALL ATTRIBUTION
            </span>
            <div className="flex items-baseline gap-1">
              <span className="text-3xl sm:text-4xl font-extrabold font-mono-code text-cyan-400">
                {Math.round(actor.confidence * 100)}%
              </span>
              <span className="text-xs font-mono-code text-slate-500">CONFIDENCE</span>
            </div>
            <span className="text-[10px] font-mono-code text-emerald-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> MULTI-SOURCE VERIFIED
            </span>
          </div>
        </div>

        {/* 4 OVERVIEW METRICS CARDS */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl border border-slate-800 bg-[#0c121e]/70">
            <span className="text-[10px] font-mono-code uppercase tracking-wider text-slate-400 block mb-1">
              IDENTITY
            </span>
            <div className="font-mono-code font-bold text-base text-white">
              {actor.clusterId}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {actor.handles.length} Linked Handles
            </div>
          </div>

          <div className="p-4 rounded-xl border border-slate-800 bg-[#0c121e]/70">
            <span className="text-[10px] font-mono-code uppercase tracking-wider text-slate-400 block mb-1">
              RISK LEVEL
            </span>
            <div className="flex items-center gap-2 mt-0.5">
              <RiskBadge level={actor.risk} size="md" />
            </div>
            <div className="text-[11px] text-rose-400/90 mt-1 font-mono-code">
              High Severity Threat
            </div>
          </div>

          <div className="p-4 rounded-xl border border-slate-800 bg-[#0c121e]/70">
            <span className="text-[10px] font-mono-code uppercase tracking-wider text-slate-400 block mb-1">
              CONFIDENCE
            </span>
            <div className="font-mono-code font-bold text-base text-cyan-400">
              {Math.round(actor.confidence * 100)}%
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Probabilistic Bayes Match
            </div>
          </div>

          <div className="p-4 rounded-xl border border-slate-800 bg-[#0c121e]/70">
            <span className="text-[10px] font-mono-code uppercase tracking-wider text-slate-400 block mb-1">
              RELATIONSHIPS
            </span>
            <div className="font-mono-code font-bold text-base text-white">
              {actor.handles.length + actor.wallets.length + 1} Connected Entities
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Cross-Platform Infrastructure
            </div>
          </div>
        </div>

        {/* 2-COLUMN SPLIT: EVIDENCE SIGNALS + MINI GRAPH & TIMELINE */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          {/* LEFT COLUMN: EVIDENCE & SIGNALS (7 Cols) */}
          <div className="lg:col-span-7 space-y-6">
            
            {/* EVIDENCE SIGNALS CONTAINER */}
            <div className="p-5 rounded-xl border border-slate-800 bg-[#0c121e]/90 backdrop-blur-md space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Fingerprint className="w-4 h-4 text-cyan-400" />
                  <h3 className="font-mono-code font-bold text-xs uppercase tracking-wider text-white">
                    CORRELATED EVIDENCE & SIGNALS
                  </h3>
                </div>
                <span className="text-[10px] font-mono-code text-slate-400">
                  {actor.signals.length} VERIFIED INDICATORS
                </span>
              </div>

              <div className="space-y-3">
                {actor.signals.map((sig) => (
                  <div
                    key={sig.id}
                    className="p-3.5 rounded-lg border border-slate-800/80 bg-slate-900/60 hover:border-slate-700 transition-colors space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono-code font-bold uppercase tracking-wider text-cyan-400 px-1.5 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30">
                            {sig.type}
                          </span>
                          <span className="font-mono-code font-bold text-xs text-white">
                            {sig.description}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 font-mono-code text-xs">
                        <span className="text-[10px] text-slate-500 uppercase">Confidence</span>
                        <span className="font-bold text-cyan-400">{Math.round(sig.confidence * 100)}%</span>
                      </div>
                    </div>

                    {sig.details && (
                      <p className="text-xs text-slate-400 leading-relaxed font-sans pl-1">
                        {sig.details}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* CHRONOLOGICAL TIMELINE */}
            <div className="p-5 rounded-xl border border-slate-800 bg-[#0c121e]/90 backdrop-blur-md space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-cyan-400" />
                  <h3 className="font-mono-code font-bold text-xs uppercase tracking-wider text-white">
                    CHRONOLOGICAL IDENTITY TIMELINE
                  </h3>
                </div>
                <span className="text-[10px] font-mono-code text-slate-400">
                  REVEALING SEQUENTIALLY
                </span>
              </div>

              <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-[2px] before:bg-gradient-to-b before:from-cyan-500 before:via-indigo-500 before:to-emerald-500">
                {actor.timeline.map((event, idx) => {
                  const isVisible = idx < revealedEvents;
                  return (
                    <div
                      key={event.id}
                      className={`relative transition-all duration-500 ${
                        isVisible
                          ? 'opacity-100 translate-y-0'
                          : 'opacity-0 translate-y-4 pointer-events-none'
                      }`}
                    >
                      {/* Timeline node marker */}
                      <span className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.9)] ring-4 ring-[#0c121e]" />

                      <div className="p-3.5 rounded-lg border border-slate-800 bg-slate-900/70 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-mono-code text-[11px] font-bold text-cyan-400">
                            {event.date}
                          </span>
                          <span className="text-[10px] font-mono-code text-slate-400 px-1.5 py-0.2 rounded bg-slate-800">
                            Confidence: {Math.round(event.confidence * 100)}%
                          </span>
                        </div>

                        <h4 className="font-mono-code font-bold text-xs uppercase tracking-wider text-white">
                          {event.title}
                        </h4>

                        <p className="text-xs text-slate-300 leading-relaxed font-sans">
                          {event.description}
                        </p>
                      </div>

                      {idx < actor.timeline.length - 1 && (
                        <div className="flex justify-start pl-4 py-1 text-slate-600">
                          <ArrowDown className="w-3 h-3" />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN: ACTOR GRAPH MINI-VIEW & INFRASTRUCTURE DETAILS (5 Cols) */}
          <div className="lg:col-span-5 space-y-6">
            
            {/* MINI GRAPH PREVIEW */}
            <div className="p-5 rounded-xl border border-slate-800 bg-[#0c121e]/90 backdrop-blur-md space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Network className="w-4 h-4 text-cyan-400" />
                  <h3 className="font-mono-code font-bold text-xs uppercase tracking-wider text-white">
                    LOCAL RELATIONSHIP CLUSTER
                  </h3>
                </div>
                <button
                  onClick={() => navigate('/graph')}
                  className="text-[10px] font-mono-code text-cyan-400 hover:underline flex items-center gap-1"
                >
                  <span>Full Graph</span>
                  <ExternalLink className="w-3 h-3" />
                </button>
              </div>

              <div className="h-64 rounded-lg border border-slate-800 bg-[#070b12] overflow-hidden relative">
                <RelationshipGraph
                  data={miniGraphData}
                  filters={defaultFilters}
                  onSelectNode={(node) => {
                    if (node.category === 'ACTOR') {
                      navigate(`/actors/${node.id}`);
                    }
                  }}
                  selectedNode={MOCK_NODES.find((n) => n.id === actor.id) || null}
                />
              </div>

              <p className="text-[11px] text-slate-400 leading-relaxed">
                Direct cluster diagram showing {actor.id} controls over handles ({actor.handles.join(', ')}) routing into cryptocurrency endpoints.
              </p>
            </div>

            {/* CONNECTED IDENTIFIERS LIST */}
            <div className="p-5 rounded-xl border border-slate-800 bg-[#0c121e]/90 backdrop-blur-md space-y-4">
              <h3 className="font-mono-code font-bold text-xs uppercase tracking-wider text-white pb-2 border-b border-slate-800 flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                <span>IDENTIFIERS & WALLETS</span>
              </h3>

              {/* Handles */}
              <div className="space-y-2">
                <span className="text-[10px] font-mono-code uppercase text-slate-400 flex items-center gap-1.5 font-semibold">
                  <AtSign className="w-3 h-3 text-indigo-400" /> Controlled Handles
                </span>
                {actor.handles.map((h) => (
                  <div key={h} className="p-2.5 rounded-lg border border-indigo-500/20 bg-indigo-500/10 flex items-center justify-between font-mono-code text-xs">
                    <span className="text-indigo-300 font-bold">{h}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300">
                      Correlated
                    </span>
                  </div>
                ))}
              </div>

              {/* Wallets */}
              <div className="space-y-2 pt-2 border-t border-slate-800">
                <span className="text-[10px] font-mono-code uppercase text-slate-400 flex items-center gap-1.5 font-semibold">
                  <Wallet className="w-3 h-3 text-emerald-400" /> Linked Cryptographic Wallets
                </span>
                {actor.wallets.map((w) => (
                  <div key={w.address} className="p-2.5 rounded-lg border border-emerald-500/20 bg-emerald-500/10 space-y-1 font-mono-code text-xs">
                    <div className="flex items-center justify-between">
                      <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold text-[10px]">
                        {w.currency}
                      </span>
                      <span className="text-slate-200 font-bold">{w.address}</span>
                    </div>
                    <p className="text-[10px] text-slate-400 font-sans">
                      {w.role}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* PROMPT ACTION TO REPORT */}
            <div className="p-4 rounded-xl border border-cyan-500/30 bg-gradient-to-br from-cyan-950/30 to-[#0c121e] space-y-3">
              <div className="flex items-center gap-2 text-cyan-400">
                <Sparkles className="w-4 h-4" />
                <span className="font-mono-code text-xs font-bold uppercase tracking-wider">
                  ANALYST BRIEFING READY
                </span>
              </div>
              <p className="text-xs text-slate-300">
                Compile comprehensive forensic evidence, stylometry scoring, and final attribution assessment.
              </p>
              <button
                onClick={() => navigate(`/reports/${actor.id}`)}
                className="w-full py-2 px-3 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono-code text-xs font-bold transition-colors flex items-center justify-center gap-2"
              >
                <span>View Full Investigation Report</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
