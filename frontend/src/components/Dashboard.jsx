import { useState } from "react";
import { FileText, ShieldCheck, AlertCircle, BookOpen, Sparkles, MessageCircle, LayoutDashboard } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from "recharts";
import PrivacyGuardCard from "./PrivacyGuardCard";
import ClauseList from "./ClauseList";
import ChatPanel from "./ChatPanel";
import WhatIfPanel from "./WhatIfPanel";

const TABS = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "simplified", label: "Simplified Policy", icon: BookOpen },
  { id: "coverage", label: "Coverage & Exclusions", icon: ShieldCheck },
  { id: "attention", label: "Attention Points", icon: AlertCircle },
  { id: "whatif", label: "What-If Simulator", icon: Sparkles },
  { id: "chat", label: "Ask Your Policy", icon: MessageCircle },
];

function MetricCard({ label, value, suffix = "" }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
      <p className="text-xs text-slate-400 font-medium uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-slate-800 mt-1">{value}{suffix}</p>
    </div>
  );
}

export default function Dashboard({ documentId, uploadResult, analysis, onReset }) {
  const [tab, setTab] = useState("overview");

  const result = analysis.analysis;
  const readability = analysis.readability || {};
  const privacy = uploadResult.privacy;

  const readabilityData = [
    { name: "Before", score: readability.before ?? 0 },
    { name: "After", score: readability.after ?? 0 },
  ];

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="font-bold text-lg text-slate-900">
            Policy<span className="text-teal-600">Lens</span> AI
          </div>
          <span className="text-slate-300">|</span>
          <div className="flex items-center gap-1.5 text-sm text-slate-500">
            <FileText size={14} /> {uploadResult.filename}
          </div>
        </div>
        <button onClick={onReset} className="text-sm text-slate-500 hover:text-slate-700">
          Upload a different policy
        </button>
      </header>

      <div className="flex">
        <nav className="w-56 border-r border-slate-200 bg-white min-h-[calc(100vh-57px)] py-4">
          {TABS.map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`w-full flex items-center gap-2.5 px-5 py-2.5 text-sm font-medium transition-colors ${
                  tab === t.id ? "bg-teal-50 text-teal-700 border-r-2 border-teal-600" : "text-slate-500 hover:bg-slate-50"
                }`}
              >
                <Icon size={16} /> {t.label}
              </button>
            );
          })}
        </nav>

        <main className="flex-1 p-6 max-w-6xl">
          {analysis.fallbackUsed && (
            <div className="mb-4 bg-amber-50 border border-amber-200 text-amber-700 text-sm rounded-lg px-4 py-2.5">
              Gemini unavailable — response generated using Grok fallback.
            </div>
          )}

          {tab === "overview" && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricCard label="Policy Complexity" value={complexityScore(result)} suffix="/100" />
                <MetricCard label="Coverage Clauses" value={result.coverage.length} />
                <MetricCard label="Exclusions" value={result.exclusions.length} />
                <MetricCard label="Attention Points" value={result.attentionPoints.length} />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                  <h3 className="font-semibold text-slate-800 mb-2">Summary</h3>
                  <p className="text-sm text-slate-600 leading-relaxed">{result.summary || "No summary available."}</p>

                  <h3 className="font-semibold text-slate-800 mt-6 mb-3">5 Things You Must Know</h3>
                  <FiveThings result={result} />
                </div>
                <PrivacyGuardCard privacy={privacy} />
              </div>

              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                <h3 className="font-semibold text-slate-800 mb-4">Readability (Flesch Reading Ease)</h3>
                <div className="flex items-center gap-8">
                  <div className="text-center">
                    <p className="text-xs text-slate-400">BEFORE</p>
                    <p className="text-3xl font-bold text-slate-400">{readability.before ?? "—"}<span className="text-base">/100</span></p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-400">AFTER (AI Summary)</p>
                    <p className="text-3xl font-bold text-teal-600">{readability.after ?? "—"}<span className="text-base">/100</span></p>
                  </div>
                  <div className="flex-1 h-32">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={readabilityData}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="name" fontSize={12} />
                        <YAxis domain={[0, 100]} fontSize={12} />
                        <Tooltip />
                        <Bar dataKey="score" fill="#0d9488" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          )}

          {tab === "simplified" && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
              <h3 className="font-semibold text-slate-800 mb-3">Simplified Policy Summary</h3>
              <p className="text-slate-600 leading-relaxed mb-6">{result.summary}</p>

              <h4 className="font-semibold text-slate-700 mb-2">Important Clauses</h4>
              <ClauseList items={result.importantClauses} />
            </div>
          )}

          {tab === "coverage" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                <h3 className="font-semibold text-slate-800 mb-3">Coverage</h3>
                <ClauseList items={result.coverage} />
              </div>
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                <h3 className="font-semibold text-slate-800 mb-3">Exclusions</h3>
                <ClauseList items={result.exclusions} />
              </div>
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                <h3 className="font-semibold text-slate-800 mb-3">Waiting Periods</h3>
                <ClauseList items={result.waitingPeriods} />
              </div>
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                <h3 className="font-semibold text-slate-800 mb-3">Deductibles & Limits</h3>
                <ClauseList items={[...result.deductibles, ...result.limits]} />
              </div>
            </div>
          )}

          {tab === "attention" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                <h3 className="font-semibold text-slate-800 mb-3">Attention Points</h3>
                <ClauseList items={result.attentionPoints} />
              </div>
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                <h3 className="font-semibold text-slate-800 mb-3">Claim Conditions</h3>
                <ClauseList items={result.claimConditions} />
              </div>
            </div>
          )}

          {tab === "whatif" && <WhatIfPanel documentId={documentId} />}
          {tab === "chat" && <ChatPanel documentId={documentId} />}
        </main>
      </div>
    </div>
  );
}

function complexityScore(result) {
  const exclusions = result.exclusions?.length || 0;
  const attention = result.attentionPoints?.length || 0;
  const coverage = result.coverage?.length || 0;
  return Math.min(100, exclusions * 8 + attention * 10 + coverage * 3);
}

function FiveThings({ result }) {
  const items = [
    ...(result.attentionPoints || []).slice(0, 3),
    ...(result.exclusions || []).slice(0, 2),
  ].slice(0, 5);

  if (items.length === 0) {
    return <p className="text-sm text-slate-400 italic">Not enough information to generate highlights.</p>;
  }

  return (
    <ul className="space-y-2">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
          <span className="text-teal-600 font-bold mt-0.5">{i + 1}.</span> {item.title}
        </li>
      ))}
    </ul>
  );
}
