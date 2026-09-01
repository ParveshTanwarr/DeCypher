import React, { useState, useMemo } from 'react';
import { RelationshipGraph } from '../components/graph/RelationshipGraph';
import { GraphSidebar } from '../components/graph/GraphSidebar';
import { GraphLegend } from '../components/graph/GraphLegend';
import { ActorInvestigationDrawer } from '../components/graph/ActorInvestigationDrawer';
import { getGraphData } from '../data/mockGraph';
import { GraphNode, FilterState } from '../types/graph';
import { Network, Shield, AtSign, Wallet, Activity, SlidersHorizontal } from 'lucide-react';

export const GraphPage: React.FC = () => {
  const [graphData] = useState(() => getGraphData());
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Filter state
  const [filters, setFilters] = useState<FilterState>({
    nodeTypes: {
      actors: true,
      handles: true,
      wallets: true,
    },
    riskLevels: {
      critical: true,
      high: true,
      medium: true,
      low: true,
    },
    confidenceThreshold: 'all',
    searchTerm: '',
  });

  // Calculate active/filtered summary counts dynamically
  const metrics = useMemo(() => {
    const activeNodes = graphData.nodes.filter((node) => {
      if (node.category === 'ACTOR' && !filters.nodeTypes.actors) return false;
      if (node.category === 'HANDLE' && !filters.nodeTypes.handles) return false;
      if (node.category === 'WALLET' && !filters.nodeTypes.wallets) return false;

      if (node.risk) {
        if (node.risk === 'critical' && !filters.riskLevels.critical) return false;
        if (node.risk === 'high' && !filters.riskLevels.high) return false;
        if (node.risk === 'medium' && !filters.riskLevels.medium) return false;
        if (node.risk === 'low' && !filters.riskLevels.low) return false;
      }

      if (filters.confidenceThreshold === 'high' && node.confidence < 0.85) return false;
      if (filters.confidenceThreshold === 'medium' && node.confidence < 0.75) return false;
      if (filters.confidenceThreshold === 'low' && node.confidence < 0.65) return false;

      if (filters.searchTerm.trim()) {
        const query = filters.searchTerm.toLowerCase();
        const matchLabel = node.label.toLowerCase().includes(query);
        const matchSub = node.subLabel?.toLowerCase().includes(query) || false;
        const matchAddr = node.fullAddress?.toLowerCase().includes(query) || false;
        if (!matchLabel && !matchSub && !matchAddr) return false;
      }

      return true;
    });

    const activeNodeIds = new Set(activeNodes.map((n) => n.id));

    const activeLinks = graphData.links.filter((link) => {
      const sourceId = typeof link.source === 'object' ? (link.source as GraphNode).id : link.source;
      const targetId = typeof link.target === 'object' ? (link.target as GraphNode).id : link.target;
      return activeNodeIds.has(sourceId) && activeNodeIds.has(targetId);
    });

    const actorCount = activeNodes.filter((n) => n.category === 'ACTOR').length;
    const handleCount = activeNodes.filter((n) => n.category === 'HANDLE').length;
    const walletCount = activeNodes.filter((n) => n.category === 'WALLET').length;
    const linkCount = activeLinks.length;

    return {
      actors: actorCount,
      handles: handleCount,
      wallets: walletCount,
      relationships: linkCount,
    };
  }, [graphData, filters]);

  const handleResetFilters = () => {
    setFilters({
      nodeTypes: {
        actors: true,
        handles: true,
        wallets: true,
      },
      riskLevels: {
        critical: true,
        high: true,
        medium: true,
        low: true,
      },
      confidenceThreshold: 'all',
      searchTerm: '',
    });
  };

  const handleFocusNode = (node: GraphNode) => {
    setSelectedNode(node);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] overflow-hidden font-sans">
      {/* GRAPH HEADER BAR */}
      <header className="border-b border-slate-800/80 bg-[#0d1117]/80 backdrop-blur-xl px-4 sm:px-6 py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 z-10 shadow-[0_4px_20px_rgba(0,0,0,0.3)]">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono-code font-bold uppercase tracking-widest text-cyan-400">
              DECyPHER • RELATIONSHIP INTELLIGENCE
            </span>
          </div>
          <h1 className="text-base sm:text-lg font-bold font-mono-code text-white tracking-tight flex items-center gap-2">
            <Network className="w-4 h-4 text-cyan-400" />
            <span>Relationship Graph</span>
          </h1>
          <p className="text-[11px] text-slate-400">
            Explore correlated identities, infrastructure and behavioral signals.
          </p>
        </div>

        {/* DYNAMIC REAL-TIME METRICS */}
        <div className="flex items-center gap-2 sm:gap-4 font-mono-code text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-cyan-500/10 border border-cyan-500/25 text-cyan-300 backdrop-blur-md">
            <Shield className="w-3.5 h-3.5" />
            <span className="font-bold">{metrics.actors}</span>
            <span className="text-[10px] uppercase">ACTORS</span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-indigo-500/10 border border-indigo-500/25 text-indigo-300 backdrop-blur-md">
            <AtSign className="w-3.5 h-3.5" />
            <span className="font-bold">{metrics.handles}</span>
            <span className="text-[10px] uppercase">HANDLES</span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 backdrop-blur-md">
            <Wallet className="w-3.5 h-3.5" />
            <span className="font-bold">{metrics.wallets}</span>
            <span className="text-[10px] uppercase">WALLETS</span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900/70 border border-slate-700/40 text-slate-300 backdrop-blur-md">
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            <span className="font-bold">{metrics.relationships}</span>
            <span className="text-[10px] uppercase text-slate-400">CORRELATIONS</span>
          </div>

          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="md:hidden p-1.5 rounded border border-slate-700/60 bg-slate-900/80 text-slate-300 hover:text-white"
            title="Toggle filter controls"
          >
            <SlidersHorizontal className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* GRAPH WORKSPACE CANVAS */}
      <main className="relative flex-1 w-full h-full overflow-hidden bg-[#05070a] sleek-radial-bg">
        <RelationshipGraph
          data={graphData}
          filters={filters}
          onSelectNode={(node) => setSelectedNode(node)}
          selectedNode={selectedNode}
        />

        {/* SIDEBAR FILTER CONTROLS */}
        <GraphSidebar
          filters={filters}
          onFilterChange={setFilters}
          onResetFilters={handleResetFilters}
          onResetZoom={() => {}}
          isOpen={sidebarOpen}
          onToggleOpen={() => setSidebarOpen(!sidebarOpen)}
        />

        {/* COMPACT LEGEND */}
        <GraphLegend />

        {/* INVESTIGATION SLIDE-OUT PANEL */}
        <ActorInvestigationDrawer
          selectedNode={selectedNode}
          onClose={() => setSelectedNode(null)}
          onFocusNode={handleFocusNode}
        />
      </main>
    </div>
  );
};
