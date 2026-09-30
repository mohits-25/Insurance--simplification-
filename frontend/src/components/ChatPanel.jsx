import { useState, useRef, useEffect } from "react";
import { Send, MessageCircle, Loader2, AlertTriangle } from "lucide-react";
import { askPolicy } from "../api";

const SUGGESTED_QUESTIONS = [
  "Is hospitalization covered?",
  "What are the major exclusions?",
  "What is the waiting period?",
  "What documents are required for a claim?",
  "What is the coverage limit?",
];

export default function ChatPanel({ documentId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function send(question) {
    if (!question.trim() || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: question }]);
    setLoading(true);
    try {
      const res = await askPolicy(documentId, question);
      setMessages((m) => [...m, {
        role: "assistant",
        text: res.answer,
        sources: res.sources,
        fallbackUsed: res.fallbackUsed,
      }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", text: err.message || "Something went wrong.", error: true }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col h-[560px]">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
        <MessageCircle size={18} className="text-teal-600" />
        <h3 className="font-semibold text-slate-800">Ask Your Policy</h3>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        {messages.length === 0 && (
          <div>
            <p className="text-sm text-slate-400 mb-3">Try asking:</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => send(q)}
                  className="text-sm bg-teal-50 text-teal-700 border border-teal-200 rounded-full px-3 py-1.5 hover:bg-teal-100 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-xl px-4 py-2.5 text-sm ${
              m.role === "user"
                ? "bg-teal-600 text-white"
                : m.error
                ? "bg-red-50 text-red-700 border border-red-200"
                : "bg-slate-100 text-slate-700"
            }`}>
              {m.error && <AlertTriangle size={14} className="inline mr-1.5 -mt-0.5" />}
              {m.text}
              {m.sources && m.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-slate-200 text-xs text-slate-500 space-y-0.5">
                  {m.sources.map((s, si) => (
                    <div key={si}>Source: {s.section} · Page {s.page}</div>
                  ))}
                </div>
              )}
              {m.fallbackUsed && (
                <div className="mt-1.5 text-xs text-amber-600">Gemini unavailable — response generated using Grok fallback.</div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-100 rounded-xl px-4 py-2.5">
              <Loader2 size={16} className="animate-spin text-slate-400" />
            </div>
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); send(input); }}
        className="border-t border-slate-100 p-3 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your policy…"
          className="flex-1 text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="bg-teal-600 hover:bg-teal-700 disabled:opacity-40 text-white rounded-lg px-3.5 py-2 transition-colors"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
