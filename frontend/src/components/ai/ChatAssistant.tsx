import { FormEvent, useMemo, useState } from "react";
import { Bot, ChevronDown, Loader2, MessageCircle, Send, Shield, Sparkles, X } from "lucide-react";
import { chatWithAI, type ChatMessage } from "../../api/client";

interface ChatAssistantProps { actorId?: string; }
interface UIMessage { role: "user" | "assistant"; content: string; }

export default function ChatAssistant({ actorId }: ChatAssistantProps) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [error, setError] = useState("");
  const suggestions = useMemo(
    () => actorId ? ["Summarize this actor", "What evidence supports this profile?", "Explain the strongest relationships"] : ["What can DeCypher investigate?", "How should I interpret priority?", "Explain the evidence model"],
    [actorId],
  );

  async function sendMessage(event?: FormEvent) {
    event?.preventDefault();
    const text = input.trim();
    if (!text || sending) return;
    const next = [...messages, { role: "user" as const, content: text }];
    setMessages(next); setInput(""); setError(""); setSending(true);
    try {
      const history: ChatMessage[] = next.slice(-10).map((item) => ({ role: item.role, content: item.content }));
      const response = await chatWithAI(text, actorId, history);
      setMessages((current) => [...current, { role: "assistant", content: response.answer }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Copilot is unavailable.");
    } finally { setSending(false); }
  }

  return <>
    {!open && <button className="ai-fab" onClick={() => setOpen(true)} aria-label="Open DeCypher Copilot"><span className="ai-fab-glow" /><Sparkles size={18} /><span>Copilot</span></button>}
    {open && <section className="ai-copilot" aria-label="DeCypher Copilot">
      <header className="ai-copilot-header">
        <div className="ai-title-wrap"><div className="ai-avatar"><Bot size={17} /></div><div><strong>DeCypher Copilot</strong><span>{actorId ? "Scoped to " + actorId : "Investigation assistant"}</span></div></div>
        <div className="ai-header-actions"><button onClick={() => setMessages([])} title="Clear conversation" aria-label="Clear conversation"><ChevronDown size={15} /></button><button onClick={() => setOpen(false)} title="Close copilot" aria-label="Close copilot"><X size={15} /></button></div>
      </header>
      <div className="ai-context-strip"><Shield size={13} /><span>Grounded in DeCypher data · no invented evidence</span></div>
      <div className="ai-messages">
        {messages.length === 0 && <div className="ai-empty"><div className="ai-empty-icon"><Sparkles size={18} /></div><strong>Ask your investigation copilot</strong><p>Query the current intelligence context in plain English.</p><div className="ai-suggestions">{suggestions.map((suggestion) => <button key={suggestion} onClick={() => setInput(suggestion)}>{suggestion}</button>)}</div></div>}
        {messages.map((message, index) => <div className={"ai-message " + message.role} key={message.role + "-" + index}>{message.role === "assistant" && <div className="ai-mini-avatar"><Bot size={12} /></div>}<div className="ai-bubble">{message.content}</div></div>)}
        {sending && <div className="ai-message assistant"><div className="ai-mini-avatar"><Bot size={12} /></div><div className="ai-bubble ai-thinking"><Loader2 size={13} /> Analyzing evidence…</div></div>}
        {error && <div className="ai-error">{error}</div>}
      </div>
      <form className="ai-composer" onSubmit={sendMessage}><input value={input} onChange={(event) => setInput(event.target.value)} placeholder={actorId ? "Ask about this actor…" : "Ask DeCypher…"} maxLength={4000} /><button type="submit" disabled={!input.trim() || sending} aria-label="Send message"><Send size={15} /></button></form>
      <footer className="ai-footer"><MessageCircle size={11} /> Gemini-powered · context stays server-side</footer>
    </section>}
  </>;
}