import React, { useState, useRef, useEffect } from 'react';
import { 
  Bot, 
  Send, 
  X, 
  Maximize2, 
  Minimize2, 
  Trash2, 
  Sparkles, 
  Copy, 
  Check, 
  RotateCw, 
  ChevronDown, 
  Shield, 
  Wallet, 
  Compass, 
  Fingerprint,
  Cpu,
  HelpCircle,
  ExternalLink
} from 'lucide-react';
import Markdown from 'react-markdown';
import { useChat, GEMINI_MODELS, PERSONAS } from '../../context/ChatContext';
import { GeminiModelId, PersonaId } from '../../types/chat';

const QUICK_PROMPTS = [
  {
    label: 'Explain Cluster A00001',
    prompt: 'Can you provide a comprehensive attribution breakdown for Threat Cluster A00001, including handles nyxinhex99 and vexatrace?',
    icon: Shield,
  },
  {
    label: 'Trace Shared ETH Wallet',
    prompt: 'Explain the shared Ethereum wallet 0x7e...870 and how it links Cluster A00001 to Cluster A00042.',
    icon: Wallet,
  },
  {
    label: 'How Stylometry Works',
    prompt: 'How does DECyPHER calculate NLP stylometry similarity between different cybercrime handles?',
    icon: Fingerprint,
  },
  {
    label: 'Guide: Using the Graph',
    prompt: 'How do I use the relationship graph, filter by confidence thresholds, and inspect actor clusters?',
    icon: Compass,
  },
];

export const GeminiChatDrawer: React.FC = () => {
  const {
    isOpen,
    setIsOpen,
    toggleChat,
    isMaximized,
    toggleMaximize,
    messages,
    sendMessage,
    retryLastMessage,
    clearMessages,
    selectedModel,
    setSelectedModel,
    selectedPersona,
    setSelectedPersona,
    isLoading,
    unreadCount,
  } = useChat();

  const [inputPrompt, setInputPrompt] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showModelMenu, setShowModelMenu] = useState(false);
  const [showPersonaMenu, setShowPersonaMenu] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom of message thread
  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen, isLoading]);

  // Focus input when drawer opens
  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputPrompt.trim() || isLoading) return;

    const query = inputPrompt;
    setInputPrompt('');
    await sendMessage(query);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const activeModelObj = GEMINI_MODELS.find((m) => m.id === selectedModel) || GEMINI_MODELS[0];
  const activePersonaObj = PERSONAS.find((p) => p.id === selectedPersona) || PERSONAS[0];

  const getPersonaIcon = (iconName: string) => {
    switch (iconName) {
      case 'Shield': return <Shield className="w-4 h-4 text-cyan-400" />;
      case 'Wallet': return <Wallet className="w-4 h-4 text-emerald-400" />;
      case 'Compass': return <Compass className="w-4 h-4 text-amber-400" />;
      case 'Fingerprint': return <Fingerprint className="w-4 h-4 text-indigo-400" />;
      default: return <Bot className="w-4 h-4 text-cyan-400" />;
    }
  };

  return (
    <>
      {/* FLOATING LAUNCHER BUTTON */}
      {!isOpen && (
        <button
          onClick={toggleChat}
          id="open-gemini-chat-btn"
          aria-label="Open Gemini Intelligence Copilot"
          className="fixed bottom-6 right-6 z-40 group flex items-center gap-2.5 px-4 py-3 rounded-full bg-[#0d1117]/90 hover:bg-[#161b22] border border-cyan-500/40 text-cyan-300 backdrop-blur-xl shadow-[0_8px_32px_rgba(6,182,212,0.25)] hover:shadow-[0_8px_40px_rgba(6,182,212,0.4)] transition-all duration-200 transform hover:scale-105"
        >
          <div className="relative">
            <Bot className="w-5 h-5 text-cyan-400 animate-pulse" />
            <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.8)]" />
          </div>
          <span className="font-mono-code text-xs font-bold tracking-wider uppercase">
            Gemini Copilot
          </span>
          {unreadCount > 0 && (
            <span className="ml-1 px-1.5 py-0.5 rounded-full bg-cyan-500 text-slate-950 font-mono-code text-[10px] font-bold">
              {unreadCount}
            </span>
          )}
        </button>
      )}

      {/* CHAT DRAWER / WORKSTATION WINDOW */}
      {isOpen && (
        <div
          aria-label="DECyPHER Gemini Copilot Drawer"
          className={`fixed z-50 flex flex-col font-sans transition-all duration-300 ease-out border border-slate-700/70 bg-[#0d1117]/95 backdrop-blur-2xl shadow-[0_16px_60px_rgba(0,0,0,0.85)] ring-1 ring-cyan-500/20 ${
            isMaximized
              ? 'inset-3 sm:inset-6 rounded-2xl'
              : 'bottom-4 right-4 sm:right-6 w-[calc(100vw-2rem)] sm:w-[460px] h-[640px] max-h-[calc(100vh-2rem)] rounded-2xl'
          }`}
        >
          {/* HEADER BAR */}
          <div className="p-3.5 border-b border-slate-800/90 flex items-center justify-between gap-2 bg-[#090d13]/80 rounded-t-2xl">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                <Bot className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="font-mono-code font-bold text-xs uppercase tracking-wider text-white flex items-center gap-1.5">
                    DECyPHER Copilot
                  </h2>
                  <span className="px-1.5 py-0.2 rounded text-[9px] font-mono-code font-bold bg-cyan-500/15 border border-cyan-500/30 text-cyan-300">
                    GEMINI
                  </span>
                </div>
                <p className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>{activePersonaObj.title}</span>
                </p>
              </div>
            </div>

            {/* HEADER CONTROLS */}
            <div className="flex items-center gap-1">
              <button
                onClick={clearMessages}
                title="Clear conversation history"
                aria-label="Clear chat history"
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800/60 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={toggleMaximize}
                title={isMaximized ? 'Restore window size' : 'Maximize window'}
                aria-label={isMaximized ? 'Minimize chat' : 'Maximize chat'}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
              >
                {isMaximized ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              </button>

              <button
                onClick={toggleChat}
                title="Close chat"
                aria-label="Close chat"
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* SUB-HEADER: MODEL & ROLE SELECTORS */}
          <div className="px-3.5 py-2 border-b border-slate-800/70 bg-slate-900/40 flex items-center justify-between gap-2 text-[11px] font-mono-code">
            {/* MODEL SELECTOR DROPDOWN */}
            <div className="relative">
              <button
                onClick={() => {
                  setShowModelMenu(!showModelMenu);
                  setShowPersonaMenu(false);
                }}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[11px] transition-colors ${activeModelObj.badgeColor}`}
              >
                <Cpu className="w-3 h-3" />
                <span className="font-semibold">{activeModelObj.shortName}</span>
                <ChevronDown className="w-3 h-3 opacity-70" />
              </button>

              {showModelMenu && (
                <div className="absolute top-full left-0 mt-1.5 w-64 rounded-xl border border-slate-700/80 bg-[#0d1117] backdrop-blur-2xl shadow-2xl p-2 z-50 space-y-1 text-xs">
                  <div className="px-2 py-1 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                    Select Gemini Model
                  </div>
                  {GEMINI_MODELS.map((model) => (
                    <button
                      key={model.id}
                      onClick={() => {
                        setSelectedModel(model.id as GeminiModelId);
                        setShowModelMenu(false);
                      }}
                      className={`w-full text-left p-2 rounded-lg flex flex-col gap-0.5 transition-colors ${
                        selectedModel === model.id
                          ? 'bg-cyan-500/10 border border-cyan-500/30 text-white'
                          : 'hover:bg-slate-800/70 text-slate-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-[11px] text-cyan-300">{model.name}</span>
                        <span className={`text-[9px] px-1.5 py-0.2 rounded border ${model.badgeColor}`}>
                          {model.tag}
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-400 line-clamp-1">{model.description}</p>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* PERSONA / ROLE SELECTOR DROPDOWN */}
            <div className="relative">
              <button
                onClick={() => {
                  setShowPersonaMenu(!showPersonaMenu);
                  setShowModelMenu(false);
                }}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-700/60 bg-slate-800/60 hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
              >
                {getPersonaIcon(activePersonaObj.iconName)}
                <span className="truncate max-w-[130px] font-semibold">{activePersonaObj.title.split(' ')[0]} Role</span>
                <ChevronDown className="w-3 h-3 opacity-70" />
              </button>

              {showPersonaMenu && (
                <div className="absolute top-full right-0 mt-1.5 w-72 rounded-xl border border-slate-700/80 bg-[#0d1117] backdrop-blur-2xl shadow-2xl p-2 z-50 space-y-1 text-xs">
                  <div className="px-2 py-1 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                    Copilot Specialized Role
                  </div>
                  {PERSONAS.map((persona) => (
                    <button
                      key={persona.id}
                      onClick={() => {
                        setSelectedPersona(persona.id as PersonaId);
                        setShowPersonaMenu(false);
                      }}
                      className={`w-full text-left p-2 rounded-lg flex items-start gap-2.5 transition-colors ${
                        selectedPersona === persona.id
                          ? 'bg-indigo-500/10 border border-indigo-500/30 text-white'
                          : 'hover:bg-slate-800/70 text-slate-300'
                      }`}
                    >
                      <div className="mt-0.5">{getPersonaIcon(persona.iconName)}</div>
                      <div className="flex-1">
                        <div className="font-bold text-[11px] text-indigo-300">{persona.title}</div>
                        <p className="text-[10px] text-slate-400 leading-tight">{persona.description}</p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* SCROLLABLE MESSAGE THREAD */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 font-sans text-xs">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'model' && (
                  <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mt-0.5">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`relative max-w-[85%] rounded-xl p-3.5 transition-all ${
                    msg.role === 'user'
                      ? 'bg-indigo-600/90 text-white rounded-br-none shadow-[0_4px_16px_rgba(79,70,229,0.3)]'
                      : msg.isError
                      ? 'bg-rose-950/40 border border-rose-800/80 text-rose-200 rounded-bl-none shadow-lg'
                      : 'bg-slate-900/80 border border-slate-800 text-slate-200 rounded-bl-none shadow-lg backdrop-blur-md'
                  }`}
                >
                  {/* MESSAGE HEADER (FOR AI ONLY) */}
                  {msg.role === 'model' && (
                    <div className="flex items-center justify-between pb-1.5 mb-2 border-b border-slate-800/80 text-[10px] font-mono-code text-slate-400">
                      <span className="font-semibold text-cyan-400">
                        {msg.modelUsed || selectedModel}
                      </span>
                      <div className="flex items-center gap-2">
                        <span>{msg.timestamp}</span>
                        <button
                          onClick={() => handleCopy(msg.content, msg.id)}
                          title="Copy text"
                          className="text-slate-500 hover:text-slate-300 transition-colors"
                        >
                          {copiedId === msg.id ? (
                            <Check className="w-3 h-3 text-emerald-400" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* MESSAGE CONTENT */}
                  {msg.role === 'user' ? (
                    <p className="whitespace-pre-wrap font-sans text-xs leading-relaxed">
                      {msg.content}
                    </p>
                  ) : (
                    <div className="markdown-body text-xs leading-relaxed space-y-2 prose prose-invert max-w-none text-slate-200">
                      <Markdown>{msg.content}</Markdown>
                    </div>
                  )}

                  {/* USER TIMESTAMP */}
                  {msg.role === 'user' && (
                    <div className="text-[9px] font-mono text-indigo-200/70 text-right mt-1">
                      {msg.timestamp}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* TYPING / THINKING INDICATOR */}
            {isLoading && (
              <div className="flex gap-3 justify-start items-center">
                <div className="w-7 h-7 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                  <Bot className="w-4 h-4 animate-spin" />
                </div>
                <div className="rounded-xl rounded-bl-none p-3 bg-slate-900/80 border border-slate-800 text-slate-300 flex items-center gap-2 font-mono-code text-xs">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                  <span className="text-cyan-300 font-semibold">Gemini is reasoning...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* QUICK PROMPT SUGGESTIONS (when few messages or idle) */}
          <div className="px-3.5 py-2 border-t border-slate-800/70 bg-slate-900/30 flex items-center gap-1.5 overflow-x-auto no-scrollbar">
            <span className="text-[10px] font-mono-code uppercase text-slate-500 font-semibold flex items-center gap-1 flex-shrink-0">
              <Sparkles className="w-3 h-3 text-cyan-400" /> Prompts:
            </span>
            {QUICK_PROMPTS.map((qp, idx) => {
              const IconComp = qp.icon;
              return (
                <button
                  key={idx}
                  onClick={() => sendMessage(qp.prompt)}
                  disabled={isLoading}
                  className="flex-shrink-0 flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-slate-700/60 bg-slate-800/40 hover:bg-cyan-500/10 hover:border-cyan-500/40 text-slate-300 hover:text-cyan-300 font-mono-code text-[10px] transition-colors"
                >
                  <IconComp className="w-3 h-3 text-cyan-400" />
                  <span>{qp.label}</span>
                </button>
              );
            })}
          </div>

          {/* INPUT FORM CONTAINER */}
          <form
            onSubmit={handleSubmit}
            className="p-3 border-t border-slate-800/90 bg-[#090d13] rounded-b-2xl"
          >
            <div className="relative flex items-center rounded-xl border border-slate-700/70 bg-slate-900/80 focus-within:border-cyan-500/60 focus-within:ring-1 focus-within:ring-cyan-500/30 transition-all">
              <textarea
                ref={inputRef}
                value={inputPrompt}
                onChange={(e) => setInputPrompt(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                placeholder="Ask Gemini about threat clusters, wallets, stylometry, or platform help..."
                className="w-full px-3.5 py-2.5 bg-transparent text-slate-100 placeholder-slate-500 font-sans text-xs focus:outline-none resize-none max-h-28"
              />

              <div className="flex items-center gap-1 pr-2">
                {messages.length > 1 && (
                  <button
                    type="button"
                    onClick={retryLastMessage}
                    disabled={isLoading}
                    title="Retry last query"
                    className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors disabled:opacity-40"
                  >
                    <RotateCw className="w-3.5 h-3.5" />
                  </button>
                )}

                <button
                  type="submit"
                  disabled={!inputPrompt.trim() || isLoading}
                  aria-label="Send message"
                  className="p-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 disabled:bg-slate-800 text-slate-950 disabled:text-slate-600 font-bold transition-all shadow-md hover:shadow-cyan-500/20"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="mt-1.5 flex items-center justify-between px-1 text-[9px] font-mono text-slate-500">
              <span>Press <kbd className="px-1 py-0.2 rounded bg-slate-800 text-slate-400">Enter</kbd> to send, <kbd className="px-1 py-0.2 rounded bg-slate-800 text-slate-400">Shift+Enter</kbd> for newline</span>
              <span>Model: <strong className="text-cyan-400">{activeModelObj.name}</strong></span>
            </div>
          </form>
        </div>
      )}
    </>
  );
};
