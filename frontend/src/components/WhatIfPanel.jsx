import { useState } from "react";
import { Sparkles, Loader2, AlertTriangle } from "lucide-react";
import { runWhatIf } from "../api";

const EXAMPLE_SCENARIOS = [
  "What if I am hospitalized for 5 days?",
  "What if I need surgery?",
  "What if my treatment costs ₹3 lakh?",
  "What if I make a claim during the waiting period?",
  "What if the treatment is listed under exclusions?",
];

export default function WhatIfPanel({ documentId }) {
  const [scenario, setScenario] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [fallbackUsed, setFallbackUsed] = useState(false);
  const [error, setError] = useState("");

  async function runScenario(text) {
    if (!text.trim() || loading) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await runWhatIf(documentId, text);
      setResult(res.result);
      setFallbackUsed(res.fallbackUsed);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles size={18} className="text-teal-600" />
        <h3 className="font-semibold text-slate-800">What-If Policy Simulator</h3>
      </div>

      <form onSubmit={(e) => { e.preventDefault(); runScenario(scenario); }} className="flex gap-2 mb-3">
        <input
          value={scenario}
          onChange={(e) => setScenario(e.target.value)}
          placeholder="e.g. What if I am hospitalized for 5 days?"
          className="flex-1 text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-teal-500"
        />
        <button
          type="submit"
          disabled={loading || !scenario.trim()}
          className="bg-teal-600 hover:bg-teal-700 disabled:opacity-40 text-white font-medium rounded-lg px-4 py-2.5 text-sm transition-colors"
        >
          Simulate
        </button>
      </form>

      <div className="flex flex-wrap gap-2 mb-5">
        {EXAMPLE_SCENARIOS.map((s) => (
          <button
            key={s}
            onClick={() => { setScenario(s); runScenario(s); }}
            className="text-xs bg-slate-50 text-slate-600 border border-slate-200 rounded-full px-3 py-1 hover:bg-slate-100 transition-colors"
          >
            {s}
          </button>
        ))}
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-slate-400 text-sm py-6 justify-center">
          <Loader2 size={18} className="animate-spin" /> Analyzing scenario against your policy…
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm flex items-start gap-2">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" /> {error}
        </div>
      )}

      {result && !loading && (
        <div className="space-y-4">
          <div className="bg-teal-50 border border-teal-200 rounded-xl p-4">
            <p className="text-sm text-teal-900">{result.explanation}</p>
          </div>

          {result.conditions?.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase text-slate-400 mb-1.5">Potential Conditions</p>
              <ul className="text-sm text-slate-600 space-y-1 list-disc list-inside">
                {result.conditions.map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </div>
          )}

          {result.limits?.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase text-slate-400 mb-1.5">Limits That May Apply</p>
              <ul className="text-sm text-slate-600 space-y-1 list-disc list-inside">
                {result.limits.map((l, i) => <li key={i}>{l}</li>)}
              </ul>
            </div>
          )}

          {result.attentionPoints?.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase text-amber-500 mb-1.5">Attention Points</p>
              <ul className="text-sm text-amber-700 space-y-1 list-disc list-inside">
                {result.attentionPoints.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            </div>
          )}

          {result.relevantClauses?.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase text-slate-400 mb-1.5">Relevant Policy Clauses</p>
              <div className="space-y-2">
                {result.relevantClauses.map((c, i) => (
                  <div key={i} className="text-sm bg-slate-50 border border-slate-200 rounded-lg p-3">
                    <p className="text-slate-600">{c.text}</p>
                    <p className="text-xs text-slate-400 mt-1">{c.section} · Page {c.page}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {fallbackUsed && (
            <p className="text-xs text-amber-600">Gemini unavailable — response generated using Grok fallback.</p>
          )}
        </div>
      )}
    </div>
  );
}
