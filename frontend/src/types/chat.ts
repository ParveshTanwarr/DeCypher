export type ChatRole = 'user' | 'model';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: string;
  modelUsed?: string;
  isError?: boolean;
}

export type GeminiModelId = 
  | 'gemini-3.7-flash'
  | 'gemini-3.5-flash'
  | 'gemini-3.1-pro-preview'
  | 'gemini-3.1-flash-lite';

export interface ModelOption {
  id: GeminiModelId;
  name: string;
  shortName: string;
  description: string;
  tag: 'Recommended' | 'Standard' | 'Deep Reasoning' | 'Ultra Fast';
  badgeColor: string;
}

export type PersonaId = 'general_analyst' | 'blockchain_forensics' | 'graph_navigator' | 'threat_hunter';

export interface PersonaOption {
  id: PersonaId;
  title: string;
  description: string;
  iconName: string;
  systemInstruction: string;
}
