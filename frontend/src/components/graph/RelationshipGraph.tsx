import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { forceCollide, forceManyBody, forceLink, forceCenter } from 'd3-force';
import { GraphData, GraphNode, GraphLink, FilterState } from '../../types/graph';
import { useTheme } from '../../context/ThemeContext';
import { 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  Sparkles, 
  Sliders, 
  Eye, 
  EyeOff, 
  RefreshCw,
  Layers,
  Crosshair
} from 'lucide-react';

interface RelationshipGraphProps {
  data: GraphData;
  filters: FilterState;
  onSelectNode: (node: GraphNode) => void;
  selectedNode: GraphNode | null;
  heightOffset?: number;
}

export type SpacingDensity = 'spacious' | 'balanced' | 'compact';

export const RelationshipGraph: React.FC<RelationshipGraphProps> = ({
  data,
  filters,
  onSelectNode,
  selectedNode,
}) => {
  const fgRef = useRef<ForceGraphMethods | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const { theme } = useTheme();

  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [hoveredLink, setHoveredLink] = useState<any | null>(null);
  
  // Visual & Spacing Controls
  const [spacingDensity, setSpacingDensity] = useState<SpacingDensity>('spacious');
  const [focusModeEnabled, setFocusModeEnabled] = useState(true);
  const [labelDensity, setLabelDensity] = useState<'smart' | 'all'>('smart');
  const [showParticles, setShowParticles] = useState(true);
  const [showToolbarDropdown, setShowToolbarDropdown] = useState(false);

  // ResizeObserver for dynamic viewport matching
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const updateDimensions = () => {
      if (container) {
        setDimensions({
          width: container.clientWidth || 800,
          height: container.clientHeight || 600,
        });
      }
    };

    updateDimensions();
    const observer = new ResizeObserver(updateDimensions);
    observer.observe(container);

    return () => observer.disconnect();
  }, []);

  // Filter nodes & links based on user controls
  const filteredData = useMemo(() => {
    const activeNodes = data.nodes.filter((node) => {
      // Node type filter
      if (node.category === 'ACTOR' && !filters.nodeTypes.actors) return false;
      if (node.category === 'HANDLE' && !filters.nodeTypes.handles) return false;
      if (node.category === 'WALLET' && !filters.nodeTypes.wallets) return false;

      // Risk level filter for actors
      if (node.risk) {
        if (node.risk === 'critical' && !filters.riskLevels.critical) return false;
        if (node.risk === 'high' && !filters.riskLevels.high) return false;
        if (node.risk === 'medium' && !filters.riskLevels.medium) return false;
        if (node.risk === 'low' && !filters.riskLevels.low) return false;
      }

      // Confidence threshold filter
      if (filters.confidenceThreshold === 'high' && node.confidence < 0.85) return false;
      if (filters.confidenceThreshold === 'medium' && node.confidence < 0.75) return false;
      if (filters.confidenceThreshold === 'low' && node.confidence < 0.65) return false;

      // Search term filter
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

    const activeLinks = data.links.filter((link) => {
      const sourceId = typeof link.source === 'object' ? (link.source as GraphNode).id : link.source;
      const targetId = typeof link.target === 'object' ? (link.target as GraphNode).id : link.target;
      return activeNodeIds.has(sourceId) && activeNodeIds.has(targetId);
    });

    return {
      nodes: activeNodes,
      links: activeLinks,
    };
  }, [data, filters]);

  // Compute connected neighbors for active (hovered or selected) node
  const activeFocusNode = hoveredNode || selectedNode;
  const connectedInfo = useMemo(() => {
    if (!activeFocusNode || !focusModeEnabled) {
      return { activeNodeId: null, neighborNodeIds: new Set<string>(), connectedLinkIds: new Set<string>() };
    }

    const neighborNodeIds = new Set<string>([activeFocusNode.id]);
    const connectedLinkIds = new Set<string>();

    filteredData.links.forEach((link: any) => {
      const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
      const targetId = typeof link.target === 'object' ? link.target.id : link.target;
      const linkId = link.id || `${sourceId}->${targetId}`;

      if (sourceId === activeFocusNode.id) {
        neighborNodeIds.add(targetId);
        connectedLinkIds.add(linkId);
      } else if (targetId === activeFocusNode.id) {
        neighborNodeIds.add(sourceId);
        connectedLinkIds.add(linkId);
      }
    });

    return {
      activeNodeId: activeFocusNode.id,
      neighborNodeIds,
      connectedLinkIds,
    };
  }, [activeFocusNode, focusModeEnabled, filteredData.links]);

  // Configure D3 Force Physics for spacious, uncluttered layout
  useEffect(() => {
    if (!fgRef.current) return;

    const spacingMultipliers = {
      spacious: { charge: -900, linkDist: 1.5, collide: 48 },
      balanced: { charge: -600, linkDist: 1.15, collide: 38 },
      compact: { charge: -400, linkDist: 0.85, collide: 28 },
    };

    const config = spacingMultipliers[spacingDensity];

    // Charge force (strong negative repulsion to prevent clumping)
    fgRef.current.d3Force(
      'charge',
      forceManyBody().strength((node: any) => {
        if (node.category === 'ACTOR') return config.charge * 1.5;
        if (node.category === 'HANDLE') return config.charge * 0.9;
        return config.charge * 0.75;
      })
    );

    // Link force (custom link distances to keep clusters distinctly spaced)
    fgRef.current.d3Force(
      'link',
      forceLink().distance((link: any) => {
        const isCrossCluster = link.type === 'shared wallet signal' || link.type === 'wallet reuse';
        const base = isCrossCluster ? 240 : 130;
        return base * config.linkDist;
      }).strength(0.45)
    );

    // Collision force (strictly prevents node and label overlap)
    fgRef.current.d3Force(
      'collide',
      forceCollide((node: any) => {
        const r = node.category === 'ACTOR' ? config.collide * 1.25 : config.collide;
        return r;
      }).iterations(3)
    );

    fgRef.current.d3ReheatSimulation();
  }, [spacingDensity, filteredData]);

  // Center & zoom on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      if (fgRef.current) {
        fgRef.current.zoomToFit(500, 70);
      }
    }, 350);
    return () => clearTimeout(timer);
  }, []);

  const handleZoomIn = () => {
    if (fgRef.current) {
      fgRef.current.zoom(fgRef.current.zoom() * 1.35, 300);
    }
  };

  const handleZoomOut = () => {
    if (fgRef.current) {
      fgRef.current.zoom(fgRef.current.zoom() / 1.35, 300);
    }
  };

  const handleResetZoom = () => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(400, 70);
    }
  };

  const handleReheatLayout = () => {
    if (fgRef.current) {
      fgRef.current.d3ReheatSimulation();
    }
  };

  // Canvas Node Painter with High Contrast, Smart LOD & Dimming
  const paintNode = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const isDark = theme === 'dark';
      const isSelected = selectedNode?.id === node.id;
      const isHovered = hoveredNode?.id === node.id;

      // Check if node is dimmed by Focus Mode
      const isFocusedNeighborhood =
        !connectedInfo.activeNodeId || connectedInfo.neighborNodeIds.has(node.id);
      const alpha = isFocusedNeighborhood ? 1.0 : 0.14;

      ctx.save();
      ctx.globalAlpha = alpha;

      const x = node.x || 0;
      const y = node.y || 0;

      // Base radius calculation
      let radius = 7;
      if (node.category === 'ACTOR') radius = 15;
      else if (node.category === 'HANDLE') radius = 10;
      else if (node.category === 'WALLET') radius = 8;

      // 1. RISK OR ATTRIBUTION HALO (FOR ACTORS)
      if (node.category === 'ACTOR') {
        const riskColor = 
          node.risk === 'critical' ? '#f43f5e' :
          node.risk === 'high' ? '#f97316' :
          node.risk === 'medium' ? '#f59e0b' : '#10b981';

        // Outer ambient glow ring
        ctx.beginPath();
        ctx.arc(x, y, radius + 5, 0, 2 * Math.PI, false);
        ctx.strokeStyle = riskColor;
        ctx.lineWidth = isSelected ? 3 : 2;
        if (isDark) {
          ctx.shadowColor = riskColor;
          ctx.shadowBlur = isSelected ? 16 : 8;
        }
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Tactical dashed radar orbit for critical or selected
        if (isSelected || node.risk === 'critical' || isHovered) {
          ctx.beginPath();
          ctx.arc(x, y, radius + 10, 0, 2 * Math.PI, false);
          ctx.strokeStyle = isDark ? 'rgba(56, 189, 248, 0.5)' : 'rgba(2, 132, 199, 0.4)';
          ctx.lineWidth = 1.2;
          ctx.setLineDash([3, 4]);
          ctx.stroke();
          ctx.setLineDash([]);
        }
      }

      // Selection halo for non-actors
      if (isSelected && node.category !== 'ACTOR') {
        ctx.beginPath();
        ctx.arc(x, y, radius + 5, 0, 2 * Math.PI, false);
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 2.5;
        if (isDark) {
          ctx.shadowColor = '#38bdf8';
          ctx.shadowBlur = 12;
        }
        ctx.stroke();
        ctx.shadowBlur = 0;
      }

      // 2. MAIN NODE BODY WITH CATEGORY THEMING
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, 2 * Math.PI, false);

      let strokeColor = '#38bdf8';
      let fillColor = isDark ? '#0c1a2e' : '#e0f2fe';

      if (node.category === 'ACTOR') {
        fillColor = isDark ? '#091322' : '#e0f2fe';
        strokeColor = isDark ? '#38bdf8' : '#0284c7';
        ctx.lineWidth = 2.5;
      } else if (node.category === 'HANDLE') {
        fillColor = isDark ? '#11142e' : '#ede9fe';
        strokeColor = isDark ? '#818cf8' : '#6366f1';
        ctx.lineWidth = 2;
      } else {
        // WALLET
        fillColor = isDark ? '#081c17' : '#dcfce7';
        strokeColor = isDark ? '#34d399' : '#10b981';
        ctx.lineWidth = 2;
      }

      ctx.fillStyle = fillColor;
      ctx.strokeStyle = strokeColor;
      ctx.fill();
      ctx.stroke();

      // 3. CENTER GLYPH / PIP
      ctx.beginPath();
      ctx.arc(x, y, radius * 0.38, 0, 2 * Math.PI, false);
      ctx.fillStyle = strokeColor;
      ctx.fill();

      // 4. SMART LEVEL OF DETAIL (LOD) FOR LABELS
      // Show labels if:
      // - It is an ACTOR (always important hub)
      // - OR labelDensity === 'all'
      // - OR node is Selected / Hovered
      // - OR node is a connected neighbor of active node
      // - OR scale is sufficiently zoomed in (globalScale > 0.85)
      const shouldDrawLabel =
        node.category === 'ACTOR' ||
        labelDensity === 'all' ||
        isSelected ||
        isHovered ||
        (connectedInfo.activeNodeId && connectedInfo.neighborNodeIds.has(node.id)) ||
        globalScale >= 0.85;

      if (shouldDrawLabel && isFocusedNeighborhood) {
        const label = node.label || node.id;
        const fontSize = Math.max(9 / globalScale, 3.2);
        ctx.font = `600 ${fontSize}px "JetBrains Mono", monospace`;

        const textWidth = ctx.measureText(label).width;
        const labelY = y + radius + fontSize + 3;
        const paddingX = 4;
        const paddingY = 2;

        // Draw refined rounded pill behind text
        ctx.fillStyle = isDark ? 'rgba(9, 14, 23, 0.92)' : 'rgba(255, 255, 255, 0.95)';
        ctx.strokeStyle = isSelected || isHovered
          ? strokeColor
          : (isDark ? 'rgba(51, 65, 85, 0.6)' : 'rgba(203, 213, 225, 0.8)');
        ctx.lineWidth = 1;

        const rectX = x - textWidth / 2 - paddingX;
        const rectY = labelY - fontSize + 1 - paddingY;
        const rectW = textWidth + paddingX * 2;
        const rectH = fontSize + paddingY * 2;
        const rectRadius = 3;

        // Draw pill with rounded corners
        ctx.beginPath();
        ctx.roundRect 
          ? ctx.roundRect(rectX, rectY, rectW, rectH, rectRadius)
          : ctx.rect(rectX, rectY, rectW, rectH);
        ctx.fill();
        ctx.stroke();

        // Render text
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = isSelected
          ? '#38bdf8'
          : (isDark ? '#f8fafc' : '#0f172a');
        ctx.fillText(label, x, labelY + 1);

        // Sublabel only when zoomed in or selected
        if ((globalScale > 1.3 || isSelected || isHovered) && node.subLabel) {
          const subFontSize = Math.max(7.5 / globalScale, 2.8);
          ctx.font = `${subFontSize}px "Plus Jakarta Sans", sans-serif`;
          ctx.fillStyle = isDark ? '#94a3b8' : '#64748b';
          ctx.fillText(node.subLabel, x, labelY + fontSize + 4);
        }
      }

      ctx.restore();
    },
    [theme, selectedNode, hoveredNode, connectedInfo, labelDensity]
  );

  // Canvas Link Painter with Clutter Reduction & Highlight Glow
  const paintLink = useCallback(
    (link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const source = link.source;
      const target = link.target;
      if (typeof source !== 'object' || typeof target !== 'object') return;

      const isDark = theme === 'dark';
      const confidence = link.confidence || 0.7;

      const sourceId = source.id;
      const targetId = target.id;
      const linkId = link.id || `${sourceId}->${targetId}`;

      const isLinkConnected =
        !connectedInfo.activeNodeId || connectedInfo.connectedLinkIds.has(linkId);
      const isLinkHovered = hoveredLink?.id === link.id;

      const alpha = isLinkConnected ? (isLinkHovered ? 1.0 : 0.7 + confidence * 0.3) : 0.08;

      ctx.save();
      ctx.globalAlpha = alpha;

      // Draw connection line
      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);

      const isCrossCluster = link.type === 'shared wallet signal' || link.type === 'wallet reuse';

      if (isCrossCluster) {
        ctx.strokeStyle = isDark
          ? `rgba(249, 115, 22, ${isLinkConnected ? 0.9 : 0.2})`
          : `rgba(234, 88, 12, ${isLinkConnected ? 0.9 : 0.2})`;
        ctx.setLineDash([4, 4]);
        ctx.lineWidth = isLinkConnected ? 2.5 : 1.2;
      } else {
        ctx.strokeStyle = isDark
          ? `rgba(56, 189, 248, ${isLinkConnected ? 0.75 : 0.15})`
          : `rgba(2, 132, 199, ${isLinkConnected ? 0.75 : 0.15})`;
        ctx.setLineDash([]);
        ctx.lineWidth = isLinkConnected ? 1.8 + confidence * 1.2 : 1;
      }

      if (isLinkHovered && isDark) {
        ctx.shadowColor = ctx.strokeStyle as string;
        ctx.shadowBlur = 10;
      }

      ctx.stroke();
      ctx.setLineDash([]);
      ctx.shadowBlur = 0;

      // DRAW EDGE LABELS ONLY WHEN HOVERED OR ON CLOSE ZOOM TO PREVENT TEXT CLUTTER
      const shouldDrawEdgeLabel =
        isLinkHovered ||
        (isLinkConnected && connectedInfo.activeNodeId && globalScale > 1.2) ||
        globalScale > 1.8;

      if (shouldDrawEdgeLabel && isLinkConnected) {
        const midX = (source.x + target.x) / 2;
        const midY = (source.y + target.y) / 2;
        const label = `${link.type} · ${Math.round(confidence * 100)}%`;
        const fontSize = Math.max(7.5 / globalScale, 2.8);

        ctx.font = `600 ${fontSize}px "JetBrains Mono", monospace`;
        const textWidth = ctx.measureText(label).width;

        ctx.fillStyle = isDark ? 'rgba(12, 18, 30, 0.92)' : 'rgba(255, 255, 255, 0.95)';
        ctx.strokeStyle = isCrossCluster ? 'rgba(249, 115, 22, 0.6)' : 'rgba(56, 189, 248, 0.6)';
        ctx.lineWidth = 1;

        const rectX = midX - textWidth / 2 - 3;
        const rectY = midY - fontSize / 2 - 2;
        const rectW = textWidth + 6;
        const rectH = fontSize + 4;

        ctx.beginPath();
        ctx.roundRect
          ? ctx.roundRect(rectX, rectY, rectW, rectH, 3)
          : ctx.rect(rectX, rectY, rectW, rectH);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = isCrossCluster ? '#fb923c' : (isDark ? '#e2e8f0' : '#1e293b');
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(label, midX, midY);
      }

      ctx.restore();
    },
    [theme, connectedInfo, hoveredLink]
  );

  return (
    <div 
      ref={containerRef} 
      className="relative w-full h-full flex-1 overflow-hidden select-none bg-[#05070a]"
    >
      {/* BACKGROUND GRID MATRIX */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-20"
        style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, rgba(56, 189, 248, 0.35) 1px, transparent 0)`,
          backgroundSize: '32px 32px',
        }}
      />

      <ForceGraph2D
        ref={fgRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={filteredData}
        nodeCanvasObject={paintNode}
        nodePointerAreaPaint={(node: any, color, ctx) => {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, 22, 0, 2 * Math.PI, false);
          ctx.fill();
        }}
        linkCanvasObjectMode={() => 'after'}
        linkCanvasObject={paintLink}
        linkDirectionalParticles={showParticles ? (link: any) => {
          const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
          const targetId = typeof link.target === 'object' ? link.target.id : link.target;
          const linkId = link.id || `${sourceId}->${targetId}`;
          if (connectedInfo.activeNodeId) {
            return connectedInfo.connectedLinkIds.has(linkId) ? 2 : 0;
          }
          return link.confidence > 0.8 ? 1 : 0;
        } : 0}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleSpeed={(link: any) => (link.confidence || 0.7) * 0.005}
        linkDirectionalParticleColor={(link: any) => {
          if (link.type === 'shared wallet signal' || link.type === 'wallet reuse') return '#f97316';
          return theme === 'dark' ? '#38bdf8' : '#0284c7';
        }}
        backgroundColor="transparent"
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.28}
        cooldownTicks={140}
        onNodeClick={(node: any) => onSelectNode(node as GraphNode)}
        onNodeHover={(node: any) => setHoveredNode((node as GraphNode) || null)}
        onLinkHover={(link: any) => setHoveredLink(link || null)}
        enableNodeDrag={true}
        enableZoomInteraction={true}
        enablePanInteraction={true}
      />

      {/* FLOATING VIEWPORT & SPACING CONTROLS TOOLSTRIP */}
      <div className="absolute bottom-4 right-4 z-20 flex flex-col gap-2 p-1.5 rounded-2xl border border-slate-700/60 bg-[#0d1117]/90 backdrop-blur-2xl shadow-[0_12px_40px_rgba(0,0,0,0.8)] ring-1 ring-white/10">
        <button
          onClick={handleZoomIn}
          aria-label="Zoom in graph"
          title="Zoom In"
          className="p-2 rounded-xl hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={handleZoomOut}
          aria-label="Zoom out graph"
          title="Zoom Out"
          className="p-2 rounded-xl hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={handleResetZoom}
          aria-label="Fit View to Screen"
          title="Fit View"
          className="p-2 rounded-xl hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
        >
          <Maximize2 className="w-4 h-4" />
        </button>

        <div className="h-px w-full bg-slate-800 my-0.5" />

        {/* REHEAT LAYOUT PHYSICS */}
        <button
          onClick={handleReheatLayout}
          aria-label="Re-layout & Untangle Graph"
          title="Reheat Simulation & Untangle"
          className="p-2 rounded-xl hover:bg-slate-800 text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
        </button>

        {/* TOGGLE SPACING MENU */}
        <div className="relative">
          <button
            onClick={() => setShowToolbarDropdown(!showToolbarDropdown)}
            aria-label="Layout Spacing & Density Settings"
            title="Graph Density & Layout"
            className={`p-2 rounded-xl transition-colors ${
              showToolbarDropdown ? 'bg-cyan-500/20 text-cyan-300' : 'hover:bg-slate-800 text-slate-300 hover:text-white'
            }`}
          >
            <Sliders className="w-4 h-4" />
          </button>

          {/* SPACING & DENSITY FLYOUT POPOVER */}
          {showToolbarDropdown && (
            <div className="absolute bottom-0 right-full mr-2.5 w-64 rounded-xl border border-slate-700/80 bg-[#0d1117]/95 backdrop-blur-2xl p-3 shadow-2xl z-30 font-sans text-xs space-y-3">
              <div className="flex items-center justify-between pb-1.5 border-b border-slate-800">
                <span className="font-mono-code font-bold text-[10px] uppercase text-cyan-400 tracking-wider">
                  Visual Density Controls
                </span>
                <span className="text-[9px] font-mono text-slate-500">Physics & LOD</span>
              </div>

              {/* SPACING DENSITY BUTTONS */}
              <div>
                <label className="block text-[10px] font-mono-code uppercase text-slate-400 mb-1.5 font-semibold">
                  Cluster Spacing
                </label>
                <div className="grid grid-cols-3 gap-1 bg-slate-900/80 p-1 rounded-lg border border-slate-800 font-mono-code text-[10px]">
                  {(['spacious', 'balanced', 'compact'] as SpacingDensity[]).map((mode) => (
                    <button
                      key={mode}
                      onClick={() => setSpacingDensity(mode)}
                      className={`py-1 rounded capitalize transition-all ${
                        spacingDensity === mode
                          ? 'bg-cyan-500 text-slate-950 font-bold shadow-md'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>

              {/* FOCUS MODE TOGGLE */}
              <div className="flex items-center justify-between pt-1 border-t border-slate-800/80">
                <div>
                  <span className="font-mono-code text-[10px] font-semibold text-slate-200 block">Focus Dimming</span>
                  <span className="text-[9px] text-slate-400 block">Dims unselected nodes</span>
                </div>
                <button
                  onClick={() => setFocusModeEnabled(!focusModeEnabled)}
                  className={`px-2 py-1 rounded font-mono-code text-[10px] border transition-colors ${
                    focusModeEnabled
                      ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-300'
                      : 'bg-slate-800 border-slate-700 text-slate-400'
                  }`}
                >
                  {focusModeEnabled ? 'Enabled' : 'Off'}
                </button>
              </div>

              {/* LABEL DENSITY TOGGLE */}
              <div className="flex items-center justify-between pt-1 border-t border-slate-800/80">
                <div>
                  <span className="font-mono-code text-[10px] font-semibold text-slate-200 block">Label LOD</span>
                  <span className="text-[9px] text-slate-400 block">Smart Zoom vs All</span>
                </div>
                <button
                  onClick={() => setLabelDensity(labelDensity === 'smart' ? 'all' : 'smart')}
                  className={`px-2 py-1 rounded font-mono-code text-[10px] border transition-colors ${
                    labelDensity === 'smart'
                      ? 'bg-indigo-500/15 border-indigo-500/40 text-indigo-300'
                      : 'bg-slate-800 border-slate-700 text-slate-400'
                  }`}
                >
                  {labelDensity === 'smart' ? 'Smart LOD' : 'All Labels'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* TOP NOTIFICATION / ACTIVE FOCUS INDICATOR */}
      {connectedInfo.activeNodeId && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2 px-3 py-1.5 rounded-full border border-cyan-500/40 bg-[#0d1117]/85 backdrop-blur-xl shadow-lg font-mono-code text-[11px] text-slate-200 pointer-events-none animate-in fade-in slide-in-from-top-2">
          <Crosshair className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
          <span>Focusing Neighborhood of <strong className="text-cyan-300">{activeFocusNode?.label}</strong> ({connectedInfo.neighborNodeIds.size - 1} connected)</span>
        </div>
      )}

      {/* REAL-TIME HOVER TOOLTIP CARD */}
      {hoveredNode && (!selectedNode || selectedNode.id !== hoveredNode.id) && (
        <div 
          className="absolute top-4 right-4 z-20 w-64 rounded-xl border border-cyan-500/40 bg-[#0d1117]/95 backdrop-blur-xl p-3.5 shadow-[0_8px_32px_rgba(0,0,0,0.85)] ring-1 ring-cyan-500/20 font-mono-code text-xs pointer-events-none animate-in fade-in zoom-in-95 duration-150"
        >
          <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
            <span className="text-[10px] uppercase text-cyan-400 font-bold tracking-widest">
              {hoveredNode.category}
            </span>
            <span className="text-[11px] font-bold text-white">
              {hoveredNode.label}
            </span>
          </div>

          <div className="mt-2.5 space-y-1.5 text-[11px]">
            {hoveredNode.risk && (
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Risk Assessment</span>
                <span className="font-bold uppercase text-rose-400">{hoveredNode.risk}</span>
              </div>
            )}

            <div className="flex items-center justify-between">
              <span className="text-slate-400">Attribution Score</span>
              <span className="text-cyan-400 font-bold">
                {Math.round(hoveredNode.confidence * 100)}%
              </span>
            </div>

            {hoveredNode.signals && (
              <div className="pt-2 border-t border-slate-800 text-[10px] text-slate-300">
                <span className="text-slate-500 uppercase tracking-wider block mb-1">Key Signals</span>
                <div className="flex flex-wrap gap-1">
                  {hoveredNode.signals.slice(0, 2).map((s) => (
                    <span key={s} className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300 text-[9px]">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
