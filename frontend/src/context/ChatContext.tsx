import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { ChatMessage, GeminiModelId, ModelOption, PersonaId, PersonaOption } from '../types/chat';

export const GEMINI_MODELS: ModelOption[] = [
  {
    id: 'gemini-3.7-flash',
    name: 'Gemini 3.7 Flash',
    shortName: '3.7 Flash',
    description: 'Next-gen speed and advanced reasoning for cyber threat intelligence',
    tag: 'Recommended',
    badgeColor: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
  },
  {
    id: 'gemini-3.5-flash',
    name: 'Gemini 3.5 Flash',
    shortName: '3.5 Flash',
    description: 'Balanced general intelligence and responsive threat analysis',
    tag: 'Standard',
    badgeColor: 'bg-sky-500/20 text-sky-300 border-sky-500/40',
  },
  {
    id: 'gemini-3.1-pro-preview',
    name: 'Gemini 3.1 Pro',
    shortName: '3.1 Pro',
    description: 'Complex multi-hop reasoning and deep forensic threat correlation',
    tag: 'Deep Reasoning',
    badgeColor: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
  },
  {
    id: 'gemini-3.1-flash-lite',
    name: 'Gemini 3.1 Flash Lite',
    shortName: '3.1 Flash Lite',
    description: 'Ultra-low latency for rapid OSINT queries and lookups',
    tag: 'Ultra Fast',
    badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
  },
];

export const PERSONAS: PersonaOption[] = [
  {
    id: 'general_analyst',
    title: 'Threat Intelligence Analyst',
    description: 'Holistic threat actor profiling, threat tiering, and strategic assessment.',
    iconName: 'Shield',
    systemInstruction: `You are DECyPHER's Senior Threat Intelligence Analyst. Your role is to explain threat actor clusters, evaluate attribution confidence levels, synthesize timeline events, and provide strategic assessments in clear, user-friendly language.`,
  },
  {
    id: 'blockchain_forensics',
    title: 'Blockchain & Financial Forensics',
    description: 'Cryptocurrency tracing, Monero/ETH mixer correlation, and cashout flow analysis.',
    iconName: 'Wallet',
    systemInstruction: `You are DECyPHER's Lead Blockchain Forensic Investigator. Your specialty is cryptocurrency tracing across Bitcoin (BTC), Ethereum (ETH), and Monero (XMR), identifying shared deposit contracts, money laundering conduits, tumbler hops, and cashout patterns.`,
  },
  {
    id: 'graph_navigator',
    title: 'Platform Guide & Copilot',
    description: 'Guides users through DECyPHER UI, relationship graphs, filters, and metrics.',
    iconName: 'Compass',
    systemInstruction: `You are the DECyPHER Platform Navigator. Your main goal is to make the platform simple, intuitive, and user-friendly. You guide users on how to interpret force-directed graph links, how to adjust confidence threshold sliders, how to inspect actor dossiers, and how to export reports.`,
  },
  {
    id: 'threat_hunter',
    title: 'Stylometry & Technical Hunter',
    description: 'De-anonymization via NLP stylometry, temporal UTC windows, and exploit brokers.',
    iconName: 'Fingerprint',
    systemInstruction: `You are DECyPHER's Tactical Stylometric & OSINT Hunter. You specialize in de-anonymization through authorial NLP stylometry (spelling idiosyncrasies, syntax, vocabulary), temporal timezone analysis, and PGP key correlation.`,
  },
];

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: 'welcome-msg',
    role: 'model',
    content: `👋 **Welcome to DECyPHER Intelligence Copilot!**

I am your AI assistant for cyber threat attribution, de-anonymization, and relationship graph intelligence.

**What I can do for you:**
- 🔍 **Attribution Breakdown**: Explain how Cluster **A00001** connects to handles \`nyxinhex99\` & \`vexatrace\`.
- 💰 **Cryptocurrency Analysis**: Trace shared wallets (e.g., Ethereum contract \`0x7e...870\` between **A00001** & **A00042**).
- 🧠 **Stylometry & Signals**: Break down NLP stylometric scoring, dormancy-rebrand cycles, and PGP fingerprint matches.
- 🧭 **Platform Help**: Guide you through exploring nodes, adjusting confidence filters, and generating intelligence reports.

Select a prompt below or ask me anything!`,
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    modelUsed: 'gemini-3.7-flash',
  },
];

interface ChatContextType {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  toggleChat: () => void;
  isMaximized: boolean;
  setIsMaximized: (max: boolean) => void;
  toggleMaximize: () => void;
  messages: ChatMessage[];
  sendMessage: (content: string, contextOverride?: Record<string, any>) => Promise<void>;
  retryLastMessage: () => Promise<void>;
  clearMessages: () => void;
  selectedModel: GeminiModelId;
  setSelectedModel: (model: GeminiModelId) => void;
  selectedPersona: PersonaId;
  setSelectedPersona: (persona: PersonaId) => void;
  isLoading: boolean;
  error: string | null;
  activeContext: Record<string, any>;
  setActiveContext: React.Dispatch<React.SetStateAction<Record<string, any>>>;
  unreadCount: number;
  resetUnreadCount: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

const CHAT_STORAGE_KEY = 'decypher_gemini_chat_messages_v1';

export const ChatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [selectedModel, setSelectedModel] = useState<GeminiModelId>('gemini-3.7-flash');
  const [selectedPersona, setSelectedPersona] = useState<PersonaId>('general_analyst');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeContext, setActiveContext] = useState<Record<string, any>>({});
  const [unreadCount, setUnreadCount] = useState(0);

  // Initialize messages from localStorage or defaults
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    try {
      const saved = localStorage.getItem(CHAT_STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch (e) {
      console.warn('Failed to load chat messages from localStorage:', e);
    }
    return INITIAL_MESSAGES;
  });

  // Save messages to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
    } catch (e) {
      console.warn('Failed to save chat messages to localStorage:', e);
    }
  }, [messages]);

  const toggleChat = () => {
    setIsOpen((prev) => {
      if (!prev) {
        setUnreadCount(0);
      }
      return !prev;
    });
  };

  const toggleMaximize = () => {
    setIsMaximized((prev) => !prev);
  };

  const resetUnreadCount = () => {
    setUnreadCount(0);
  };

  const sendMessage = async (content: string, contextOverride?: Record<string, any>) => {
    if (!content.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setIsLoading(true);
    setError(null);

    const activePersonaObj = PERSONAS.find((p) => p.id === selectedPersona) || PERSONAS[0];
    const combinedContext = { ...activeContext, ...(contextOverride || {}) };

    try {
      // Prepare multi-turn messages array for backend
      const payloadMessages = newMessages
        .filter((m) => !m.isError)
        .map((m) => ({
          role: m.role,
          content: m.content,
        }));

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: payloadMessages,
          model: selectedModel,
          systemInstruction: activePersonaObj.systemInstruction,
          context: combinedContext,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.error || errorData.message || `Server returned status ${res.status}`);
      }

      const data = await res.json();

      const aiMessage: ChatMessage = {
        id: `ai-${Date.now()}`,
        role: 'model',
        content: data.content || 'No response generated.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        modelUsed: data.modelUsed || selectedModel,
      };

      setMessages((prev) => [...prev, aiMessage]);

      if (!isOpen) {
        setUnreadCount((prev) => prev + 1);
      }
    } catch (err: any) {
      console.error('Chat error:', err);
      const errorMessage = err.message || 'Failed to communicate with Gemini API.';
      setError(errorMessage);

      const errorAiMessage: ChatMessage = {
        id: `err-${Date.now()}`,
        role: 'model',
        content: `⚠️ **Intelligence Service Error**\n\n${errorMessage}\n\n*If your API key is missing or needs setup, please ensure \`GEMINI_API_KEY\` is configured in the AI Studio Settings.*`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        modelUsed: selectedModel,
        isError: true,
      };

      setMessages((prev) => [...prev, errorAiMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const retryLastMessage = async () => {
    // Find last user message
    const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user');
    if (lastUserMsg) {
      await sendMessage(lastUserMsg.content);
    }
  };

  const clearMessages = () => {
    setMessages(INITIAL_MESSAGES);
    setError(null);
    try {
      localStorage.removeItem(CHAT_STORAGE_KEY);
    } catch (e) {
      console.warn('Error removing chat messages:', e);
    }
  };

  return (
    <ChatContext.Provider
      value={{
        isOpen,
        setIsOpen,
        toggleChat,
        isMaximized,
        setIsMaximized,
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
        error,
        activeContext,
        setActiveContext,
        unreadCount,
        resetUnreadCount,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};
