import { ShieldCheck, Lock, EyeOff } from "lucide-react";

export default function PrivacyGuardCard({ privacy }) {
  if (!privacy) return null;

  return (
    <div className="bg-gradient-to-br from-teal-600 to-blue-800 text-white rounded-2xl p-5 shadow-lg">
      <div className="flex items-center gap-2 font-semibold mb-4">
        <ShieldCheck size={20} />
        PRIVACY GUARD ACTIVE
      </div>
      <div className="space-y-2.5 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-teal-100 flex items-center gap-1.5"><Lock size={14} /> Original document</span>
          <span className="font-medium bg-white/15 px-2 py-0.5 rounded">LOCAL ONLY</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-teal-100">PII detected</span>
          <span className="font-medium bg-white/15 px-2 py-0.5 rounded">{privacy.piiDetected ? "YES" : "NO"}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-teal-100">Fields masked</span>
          <span className="font-medium bg-white/15 px-2 py-0.5 rounded">{privacy.fieldsMasked}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-teal-100 flex items-center gap-1.5"><EyeOff size={14} /> LLM receives</span>
          <span className="font-medium bg-white/15 px-2 py-0.5 rounded">SANITIZED TEXT</span>
        </div>
      </div>
    </div>
  );
}
