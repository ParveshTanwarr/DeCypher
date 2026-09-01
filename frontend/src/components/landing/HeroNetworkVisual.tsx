import React, { useEffect, useRef, useState } from 'react';
import { useTheme } from '../../context/ThemeContext';
import { Shield, AtSign, Wallet, ArrowUpRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface NetworkNode {
  id: string;
  name: string;
  type: 'ACTOR' | 'HANDLE' | 'WALLET';
  role: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  baseX: number;
  baseY: number;
  radius: number;
  color: string;
  risk?: string;
  confidence: number;
}

interface NetworkEdge {
  from: string;
  to: string;
  label: string;
  confidence: number;
}

export const HeroNetworkVisual: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const { theme } = useTheme();
  const navigate = useNavigate();
  const [hoveredNode, setHoveredNode] = useState<NetworkNode | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = container.clientWidth || 500;
    let height = container.clientHeight || 420;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    const isDark = theme === 'dark';

    // Hierarchical simplified intelligence graph representing:
    // Actor A00001 (Center Top) -> Handles nyxinhex99, vexatrace (Middle) -> Wallets XMR, ETH (Bottom)
    const nodes: NetworkNode[] = [
      {
        id: 'A00001',
        name: 'ACTOR A00001',
        type: 'ACTOR',
        role: 'Threat Cluster Primary',
        x: width * 0.48,
        y: height * 0.22,
        baseX: width * 0.48,
        baseY: height * 0.22,
        vx: 0.15,
        vy: 0.1,
        radius: 28,
        color: isDark ? '#06b6d4' : '#0284c7',
        risk: 'CRITICAL',
        confidence: 0.92,
      },
      {
        id: 'H1',
        name: 'nyxinhex99',
        type: 'HANDLE',
        role: 'Darknet Market Handle',
        x: width * 0.22,
        y: height * 0.54,
        baseX: width * 0.22,
        baseY: height * 0.54,
        vx: -0.12,
        vy: 0.14,
        radius: 20,
        color: isDark ? '#6366f1' : '#4f46e5',
        confidence: 0.88,
      },
      {
        id: 'H2',
        name: 'vexatrace',
        type: 'HANDLE',
        role: 'Telegram Rebrand Handle',
        x: width * 0.74,
        y: height * 0.52,
        baseX: width * 0.74,
        baseY: height * 0.52,
        vx: 0.14,
        vy: -0.12,
        radius: 20,
        color: isDark ? '#6366f1' : '#4f46e5',
        confidence: 0.86,
      },
      {
        id: 'W1',
        name: 'XMR · 4b5U...aoX',
        type: 'WALLET',
        role: 'Monero Escrow Vault',
        x: width * 0.25,
        y: height * 0.84,
        baseX: width * 0.25,
        baseY: height * 0.84,
        vx: -0.09,
        vy: -0.1,
        radius: 16,
        color: isDark ? '#10b981' : '#059669',
        confidence: 0.94,
      },
      {
        id: 'W2',
        name: 'ETH · 0x7e...870',
        type: 'WALLET',
        role: 'Ethereum Cashout Contract',
        x: width * 0.72,
        y: height * 0.84,
        baseX: width * 0.72,
        baseY: height * 0.84,
        vx: 0.1,
        vy: 0.08,
        radius: 16,
        color: isDark ? '#10b981' : '#059669',
        confidence: 0.82,
      },
    ];

    const edges: NetworkEdge[] = [
      { from: 'A00001', to: 'H1', label: 'controls (92%)', confidence: 0.92 },
      { from: 'A00001', to: 'H2', label: 'controls (86%)', confidence: 0.86 },
      { from: 'H1', to: 'W1', label: 'uses wallet (94%)', confidence: 0.94 },
      { from: 'H2', to: 'W2', label: 'uses wallet (82%)', confidence: 0.82 },
      { from: 'H1', to: 'H2', label: 'stylometry & rebrand (91%)', confidence: 0.91 },
    ];

    let t = 0;

    const render = () => {
      t += 0.015;
      ctx.clearRect(0, 0, width, height);

      // Subtle float motion around base positions
      nodes.forEach((node, idx) => {
        node.x = node.baseX + Math.sin(t + idx * 1.5) * 6;
        node.y = node.baseY + Math.cos(t * 0.8 + idx * 2.0) * 5;
      });

      // Draw Connection lines with animated signal particles
      edges.forEach((edge) => {
        const source = nodes.find((n) => n.id === edge.from);
        const target = nodes.find((n) => n.id === edge.to);
        if (!source || !target) return;

        // Base line
        ctx.beginPath();
        ctx.moveTo(source.x, source.y);
        ctx.lineTo(target.x, target.y);
        ctx.strokeStyle = isDark
          ? `rgba(56, 189, 248, ${0.15 + edge.confidence * 0.25})`
          : `rgba(2, 132, 199, ${0.2 + edge.confidence * 0.25})`;
        ctx.lineWidth = 1.5 + edge.confidence * 1.5;
        if (edge.label.includes('stylometry')) {
          ctx.setLineDash([4, 4]);
        } else {
          ctx.setLineDash([]);
        }
        ctx.stroke();
        ctx.setLineDash([]);

        // Animated traveling particle along high confidence lines
        const particleProgress = (t * 0.4 + (edge.confidence * 10)) % 1;
        const px = source.x + (target.x - source.x) * particleProgress;
        const py = source.y + (target.y - source.y) * particleProgress;

        ctx.beginPath();
        ctx.arc(px, py, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = isDark ? '#38bdf8' : '#0284c7';
        ctx.shadowColor = isDark ? '#38bdf8' : '#0284c7';
        ctx.shadowBlur = 6;
        ctx.fill();
        ctx.shadowBlur = 0;

        // Draw Edge Label pill midway
        const midX = (source.x + target.x) / 2;
        const midY = (source.y + target.y) / 2;
        ctx.font = '9px "JetBrains Mono", monospace';
        const labelText = edge.label;
        const textWidth = ctx.measureText(labelText).width;

        ctx.fillStyle = isDark ? 'rgba(12, 18, 30, 0.85)' : 'rgba(255, 255, 255, 0.9)';
        ctx.strokeStyle = isDark ? 'rgba(56, 189, 248, 0.2)' : 'rgba(2, 132, 199, 0.2)';
        ctx.lineWidth = 1;
        ctx.fillRect(midX - textWidth / 2 - 4, midY - 7, textWidth + 8, 14);
        ctx.strokeRect(midX - textWidth / 2 - 4, midY - 7, textWidth + 8, 14);

        ctx.fillStyle = isDark ? '#94a3b8' : '#475569';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(labelText, midX, midY);
      });

      // Draw Nodes
      nodes.forEach((node) => {
        // Critical / High Risk Glow Halo for Actor
        if (node.type === 'ACTOR') {
          const pulse = (Math.sin(t * 2) + 1) / 2;
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.radius + 6 + pulse * 4, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(244, 63, 94, ${0.35 + pulse * 0.35})`;
          ctx.lineWidth = 2;
          ctx.stroke();

          // Outer dashed radar orbit
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.radius + 14, 0, Math.PI * 2);
          ctx.strokeStyle = isDark ? 'rgba(56, 189, 248, 0.2)' : 'rgba(2, 132, 199, 0.2)';
          ctx.setLineDash([3, 5]);
          ctx.stroke();
          ctx.setLineDash([]);
        }

        // Node fill
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = isDark ? '#0e1526' : '#ffffff';
        ctx.fill();
        ctx.strokeStyle = node.color;
        ctx.lineWidth = node.type === 'ACTOR' ? 3 : 2;
        ctx.shadowColor = node.color;
        ctx.shadowBlur = isDark ? (node.type === 'ACTOR' ? 14 : 8) : 4;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Inner category indicator dot or ring
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius * 0.45, 0, Math.PI * 2);
        ctx.fillStyle = node.color;
        ctx.fill();

        // Node Title Text
        ctx.font = node.type === 'ACTOR' 
          ? 'bold 11px "JetBrains Mono", monospace' 
          : '10px "JetBrains Mono", monospace';
        ctx.fillStyle = isDark ? '#f8fafc' : '#0f172a';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(node.name, node.x, node.y + node.radius + 12);

        // Sublabel
        ctx.font = '8.5px "Plus Jakarta Sans", sans-serif';
        ctx.fillStyle = isDark ? '#64748b' : '#64748b';
        ctx.fillText(node.type, node.x, node.y + node.radius + 23);
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    // Mouse move hover detector
    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const found = nodes.find((n) => {
        const dx = n.x - mouseX;
        const dy = n.y - mouseY;
        return Math.sqrt(dx * dx + dy * dy) <= n.radius + 6;
      });

      setHoveredNode(found || null);
    };

    const handleCanvasClick = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const found = nodes.find((n) => {
        const dx = n.x - mouseX;
        const dy = n.y - mouseY;
        return Math.sqrt(dx * dx + dy * dy) <= n.radius + 6;
      });

      if (found) {
        if (found.type === 'ACTOR') {
          navigate('/actors/A00001');
        } else {
          navigate('/graph');
        }
      }
    };

    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('click', handleCanvasClick);

    return () => {
      cancelAnimationFrame(animationFrameId);
      canvas.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('click', handleCanvasClick);
    };
  }, [theme, navigate]);

  return (
    <div 
      ref={containerRef}
      className="relative w-full h-[420px] rounded-xl border border-slate-200 dark:border-slate-800 bg-gradient-to-b from-slate-50/80 to-white/90 dark:from-[#0c121e]/90 dark:to-[#070b12]/95 backdrop-blur-md overflow-hidden shadow-soft"
    >
      {/* Top bar with telemetry status */}
      <div className="absolute top-3 left-4 right-4 flex items-center justify-between pointer-events-none z-10">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
          <span className="text-[10px] font-mono-code tracking-wider text-cyan-600 dark:text-cyan-400 font-semibold uppercase">
            CORRELATION GRAPH PREVIEW
          </span>
        </div>
        <div className="text-[10px] font-mono-code text-slate-400 dark:text-slate-500">
          NODE DENSITY: 5 | CONFIDENCE: 92%
        </div>
      </div>

      <canvas 
        ref={canvasRef} 
        className="w-full h-full cursor-pointer block"
      />

      {/* Floating hover inspection tooltip */}
      {hoveredNode && (
        <div 
          className="absolute bottom-4 left-4 right-4 p-3 rounded-lg border border-cyan-500/30 bg-white/95 dark:bg-[#0e1526]/95 backdrop-blur-md shadow-lg flex items-center justify-between text-xs animate-in fade-in zoom-in-95 duration-150 z-20 pointer-events-auto"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
              {hoveredNode.type === 'ACTOR' && <Shield className="w-4 h-4" />}
              {hoveredNode.type === 'HANDLE' && <AtSign className="w-4 h-4" />}
              {hoveredNode.type === 'WALLET' && <Wallet className="w-4 h-4" />}
            </div>
            <div>
              <div className="font-mono-code font-bold text-slate-900 dark:text-white flex items-center gap-2">
                {hoveredNode.name}
                {hoveredNode.risk && (
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-500 font-bold border border-rose-500/40">
                    {hoveredNode.risk}
                  </span>
                )}
              </div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400">
                {hoveredNode.role} • Confidence: {Math.round(hoveredNode.confidence * 100)}%
              </div>
            </div>
          </div>

          <button
            onClick={() => navigate(hoveredNode.type === 'ACTOR' ? '/actors/A00001' : '/graph')}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-cyan-500 text-slate-950 font-mono-code text-[11px] font-semibold hover:bg-cyan-400 transition-colors"
          >
            Inspect <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
};
