import React from 'react';
import { useNavigate } from 'react-router-dom';
import { GraphNode } from '../../types/graph';
import { getActorProfile, getDirectConnections, getGraphData } from '../../data/mockGraph';
import { RiskBadge, ConfidenceScore } from '../ui/Badge';
import { useChat } from '../../context/ChatContext';
import { 
  Shield, 
  AtSign, 
  Wallet, 
  ExternalLink, 
  Focus, 
  X, 
  Activity, 
  ArrowRight,
  Fingerprint,
  Bot
} from 'lucide-react';

interface ActorInvestigationDrawerProps {
  selectedNode: GraphNode | null;
  onClose: () => void;
  onFocusNode: (node: GraphNode) => void;
}

export const ActorInvestigationDrawer: React.FC<ActorInvestigationDrawerProps> = ({
  selectedNode,
  onClose,
  onFocusNode,
}) => {
  const navigate = useNavigate();
  const { sendMessage, setIsOpen, setActiveContext } = useChat();

  if (!selectedNode) return null;

  const isActor = selectedNode.category === 'ACTOR';
  const actorProfile = isActor ? getActorProfile(selectedNode.id) : null;
  const directConnections = getDirectConnections(selectedNode.id, getGraphData());

  const handleAskGemini = () => {
    setIsOpen(true);
    setActiveContext({
      currentPage: '/graph',
      currentActorId: selectedNode.id,
      selectedNodeData: selectedNode,
    });
    sendMessage(
      `Please analyze the graph entity "${selectedNode.label}" (Category: ${selectedNode.category}, ID: ${selectedNode.id}) and explain its connections and threat intelligence relevance in DECyPHER.`
    );
  };

  return (
    <div 
      aria-label="Investigation Details Drawer"
      className="absolute top-4 right-4 bottom-4 z-30 w-80 md:w-96 rounded-xl border border-slate-700/60 bg-[#0d1117]/85 backdrop-blur-xl shadow-[0_8px_36px_rgba(0,0,0,0.75)] ring-1 ring-white/5 p-5 flex flex-col font-sans text-xs overflow-y-auto animate-in slide-in-from-right-5 duration-200"
    >
      {/* HEADER BAR */}
      <div className="flex items-start justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            {selectedNode.category === 'ACTOR' && <Shield className="w-5 h-5" />}
            {selectedNode.category === 'HANDLE' && <AtSign className="w-5 h-5" />}
            {selectedNode.category === 'WALLET' && <Wallet className="w-5 h-5" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono-code font-bold text-sm text-white">
                {selectedNode.label}
              </span>
              {selectedNode.risk && <RiskBadge level={selectedNode.risk} size="sm" />}
            </div>
            <p className="text-[11px] font-mono-code text-slate-400">
              {selectedNode.subLabel || selectedNode.category}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          id="close-drawer-btn"
          aria-label="Close panel"
          className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* BODY CONTENT */}
      <div className="flex-1 py-4 space-y-4 overflow-y-auto">
        {/* KEY METRICS GRID */}
        <div className="grid grid-cols-2 gap-2">
          <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800">
            <span className="text-[9px] font-mono-code uppercase tracking-wider text-slate-500 font-semibold">
              CONFIDENCE
            </span>
            <div className="mt-1 flex items-center gap-1.5">
              <ConfidenceScore value={selectedNode.confidence} size="md" />
              <span className="text-[10px] text-slate-400 font-mono">Attribution</span>
            </div>
          </div>

          <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800">
            <span className="text-[9px] font-mono-code uppercase tracking-wider text-slate-500 font-semibold">
              CONNECTED NODES
            </span>
            <div className="mt-1 text-sm font-mono-code font-bold text-white">
              {directConnections.count} Entities
            </div>
          </div>
        </div>

        {/* ACTOR SPECIFIC SECTIONS */}
        {isActor && actorProfile ? (
          <>
            {/* CONNECTED HANDLES */}
            <div>
              <div className="flex items-center justify-between mb-1.5 text-[10px] font-mono-code uppercase tracking-widest text-slate-400 font-semibold">
                <span className="flex items-center gap-1.5">
                  <AtSign className="w-3.5 h-3.5 text-indigo-400" /> Connected Handles
                </span>
                <span className="text-slate-500">{actorProfile.handles.length}</span>
              </div>
              <div className="space-y-1.5">
                {actorProfile.handles.map((handle) => (
                  <div
                    key={handle}
                    className="p-2 rounded border border-indigo-500/20 bg-indigo-500/5 flex items-center justify-between font-mono-code text-[11px]"
                  >
                    <span className="text-indigo-300 font-semibold">{handle}</span>
                    <span className="text-[10px] text-slate-500">Primary Persona</span>
                  </div>
                ))}
              </div>
            </div>

            {/* CONNECTED WALLETS */}
            <div>
              <div className="flex items-center justify-between mb-1.5 text-[10px] font-mono-code uppercase tracking-widest text-slate-400 font-semibold">
                <span className="flex items-center gap-1.5">
                  <Wallet className="w-3.5 h-3.5 text-emerald-400" /> Connected Wallets
                </span>
                <span className="text-slate-500">{actorProfile.wallets.length}</span>
              </div>
              <div className="space-y-1.5">
                {actorProfile.wallets.map((wallet) => (
                  <div
                    key={wallet.address}
                    className="p-2 rounded border border-emerald-500/20 bg-emerald-500/5 flex items-center justify-between font-mono-code text-[11px]"
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] px-1 py-0.2 rounded bg-emerald-500/20 text-emerald-400 font-bold">
                        {wallet.currency}
                      </span>
                      <span className="text-slate-200">{wallet.address}</span>
                    </div>
                    <span className="text-[10px] text-slate-400 truncate max-w-[100px] text-right">
                      {wallet.role.split(' ')[0]}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* RELATIONSHIP SIGNALS */}
            <div>
              <div className="flex items-center gap-1.5 mb-1.5 text-[10px] font-mono-code uppercase tracking-widest text-slate-400 font-semibold">
                <Fingerprint className="w-3.5 h-3.5 text-cyan-400" /> Relationship Signals
              </div>
              <div className="space-y-1.5">
                {actorProfile.signals.slice(0, 3).map((signal) => (
                  <div
                    key={signal.id}
                    className="p-2 rounded border border-slate-800 bg-slate-900/60"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono-code text-[10px] font-bold text-slate-200">
                        {signal.title}
                      </span>
                      <span className="text-[10px] font-mono-code text-cyan-400">
                        {Math.round(signal.confidence * 100)}%
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                      {signal.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          /* HANDLE OR WALLET CONTEXTUAL DETAILS */
          <div className="space-y-3">
            <div className="p-3 rounded border border-slate-800 bg-slate-900/60">
              <span className="text-[10px] font-mono-code uppercase tracking-wider text-slate-500 font-semibold">
                IDENTIFIER CONTEXT
              </span>
              <p className="font-mono-code text-xs text-slate-200 mt-1 break-all">
                {selectedNode.fullAddress || selectedNode.label}
              </p>
              {selectedNode.platform && (
                <div className="mt-2 text-[11px] text-slate-400">
                  Origin Platform: <strong className="text-slate-200">{selectedNode.platform}</strong>
                </div>
              )}
            </div>

            <div>
              <span className="text-[10px] font-mono-code uppercase tracking-widest text-slate-400 font-semibold mb-1.5 block">
                Directly Correlated In Graph ({directConnections.nodes.length - 1} Entities)
              </span>
              <div className="space-y-1">
                {directConnections.nodes
                  .filter((n) => n.id !== selectedNode.id)
                  .map((node) => (
                    <div
                      key={node.id}
                      className="p-1.5 rounded border border-slate-800 bg-slate-900/40 flex items-center justify-between text-[11px] font-mono-code"
                    >
                      <span className="text-slate-300">{node.label}</span>
                      <span className="text-[10px] text-cyan-400 uppercase">{node.category}</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* FOOTER ACTIONS */}
      <div className="pt-3 border-t border-slate-800 space-y-2">
        <button
          id="drawer-ask-gemini-btn"
          onClick={handleAskGemini}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded border border-cyan-500/40 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 font-mono-code text-xs font-semibold tracking-wide transition-all shadow-[0_0_12px_rgba(6,182,212,0.15)]"
        >
          <Bot className="w-3.5 h-3.5 text-cyan-400" />
          <span>Ask Gemini About Entity</span>
        </button>

        {isActor ? (
          <button
            id="open-full-investigation-btn"
            onClick={() => navigate(`/actors/${selectedNode.id}`)}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono-code text-xs font-bold uppercase tracking-wider transition-colors shadow-lg hover:shadow-cyan-500/20"
          >
            <span>Open Full Investigation</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        ) : (
          selectedNode.actorId && (
            <button
              onClick={() => navigate(`/actors/${selectedNode.actorId}`)}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-mono-code text-xs font-semibold uppercase tracking-wider transition-colors"
            >
              <span>Investigate Controlling Actor</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          )
        )}

        <div className="flex items-center gap-2">
          <button
            id="focus-actor-btn"
            onClick={() => onFocusNode(selectedNode)}
            className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded border border-slate-700 bg-slate-800/80 text-slate-300 hover:bg-slate-700 font-mono-code text-[11px] transition-colors"
          >
            <Focus className="w-3 h-3 text-cyan-400" />
            <span>Focus Entity</span>
          </button>

          <button
            id="close-panel-btn"
            onClick={onClose}
            className="py-1.5 px-3 rounded border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 font-mono-code text-[11px] transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
