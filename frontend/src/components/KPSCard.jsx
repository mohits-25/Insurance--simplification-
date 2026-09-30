import { useState } from "react";
import { Info, Gauge } from "lucide-react";

const COMPONENT_LABELS = {
  coverageUnderstanding: "Coverage Understanding",
  exclusionUnderstanding: "Exclusion Understanding",
  conditionUnderstanding: "Conditions & Limits",
  sourceTraceability: "Source Traceability",
  plainLanguage: "Plain Language",
  attentionDetection: "Attention Detection",
};

const COMPONENT_ORDER = [
  "coverageUnderstanding",
  "exclusionUnderstanding",
  "conditionUnderstanding",
  "sourceTraceability",
  "plainLanguage",
  "attentionDetection",
];

function barColor(score) {
  if (score >= 90) return "bg-emerald-500";
  if (score >= 80) return "bg-teal-500";
  if (score >= 70) return "bg-amber-500";
  return "bg-red-500";
}

function ringColor(score) {
  if (score >= 90) return "text-emerald-600";
  if (score >= 80) return "text-teal-600";
  if (score >= 70) return "text-amber-600";
  return "text-red-600";
}

export default function KPSCard({ kps }) {
  const [showInfo, setShowInfo] = useState(false);

  if (!kps) return null;

  const { overallScore, target, components, label } = kps;
  const metTarget = overallScore >= target;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 relative">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <Gauge size={18} className="text-teal-600" />
          <h3 className="font-semibold text-slate-800">KPS Rating</h3>
        </div>
        <button
          onClick={() => setShowInfo((v) => !v)}
          onBlur={() => setShowInfo(false)}
          className="text-slate-400 hover:text-slate-600"
          aria-label="What is KPS?"
        >
          <Info size={16} />
        </button>
        {showInfo && (
          <div className="absolute right-4 top-11 z-10 w-64 bg-slate-800 text-white text-xs rounded-lg p-3 shadow-lg leading-relaxed">
            <strong>KPS (Key Policy Understanding)</strong> measures how effectively
            PolicyLens extracts, explains, traces and simplifies important
            information from an insurance policy.
          </div>
        )}
      </div>

      <div className="flex flex-col items-center py-3">
        <p className={`text-4xl font-bold ${ringColor(overallScore)}`}>{overallScore}%</p>
        <div className="w-full max-w-xs mt-3">
          <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${barColor(overallScore)} transition-all duration-700`}
              style={{ width: `${Math.min(100, overallScore)}%` }}
            />
          </div>
        </div>
        <div className="flex items-center justify-between w-full max-w-xs mt-2 text-xs text-slate-400">
          <span>Target: {target}%</span>
          <span className={metTarget ? "text-emerald-600 font-medium" : "text-slate-400"}>
            {metTarget ? "Target met" : `${target - overallScore}% to target`}
          </span>
        </div>
        <p className={`text-sm font-medium mt-2 ${ringColor(overallScore)}`}>{label}</p>
      </div>

      <div className="border-t border-slate-100 pt-4 mt-2 space-y-2.5">
        {COMPONENT_ORDER.map((key) => (
          <div key={key} className="flex items-center gap-3">
            <span className="text-xs text-slate-500 w-36 shrink-0">{COMPONENT_LABELS[key]}</span>
            <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${barColor(components[key])}`}
                style={{ width: `${Math.min(100, components[key])}%` }}
              />
            </div>
            <span className="text-xs font-medium text-slate-600 w-9 text-right">{components[key]}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
