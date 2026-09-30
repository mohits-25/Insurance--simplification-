import { useState } from "react";
import { Upload, FileText, Loader2, ShieldCheck, AlertTriangle } from "lucide-react";
import { uploadDocument, analyzeDocument } from "../api";

export default function UploadScreen({ onReady }) {
  const [dragOver, setDragOver] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | uploading | analyzing | error
  const [error, setError] = useState("");
  const [uploadResult, setUploadResult] = useState(null);

  async function processFile(file) {
    setError("");
    setUploadResult(null);
    setStatus("uploading");
    try {
      const result = await uploadDocument(file);
      setUploadResult(result);
      setStatus("analyzing");
      const analysis = await analyzeDocument(result.documentId);
      onReady({ documentId: result.documentId, uploadResult: result, analysis });
    } catch (err) {
      setError(err.message || "Something went wrong.");
      setStatus("error");
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  }

  function handleFileInput(e) {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  }

  const isBusy = status === "uploading" || status === "analyzing";

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6">
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 text-teal-700 font-semibold text-sm mb-3 bg-teal-50 px-3 py-1 rounded-full">
          <ShieldCheck size={16} /> Privacy-aware AI for understanding insurance policies
        </div>
        <h1 className="text-4xl font-bold text-slate-900 tracking-tight">
          Policy<span className="text-teal-600">Lens</span> AI
        </h1>
        <p className="text-slate-500 mt-2 max-w-md mx-auto">
          Upload your insurance policy. We'll redact personal data locally, then
          analyze coverage, exclusions, and risks in plain language.
        </p>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`w-full max-w-lg border-2 border-dashed rounded-2xl p-10 text-center transition-colors
          ${dragOver ? "border-teal-500 bg-teal-50" : "border-slate-300 bg-white"}`}
      >
        {!isBusy && (
          <>
            <Upload className="mx-auto text-teal-600 mb-4" size={40} />
            <p className="font-medium text-slate-700 mb-1">Upload Insurance Policy</p>
            <p className="text-sm text-slate-400 mb-4">PDF or image (PNG/JPG) &middot; up to 20MB</p>
            <label className="inline-block cursor-pointer bg-teal-600 hover:bg-teal-700 text-white font-medium px-5 py-2.5 rounded-lg transition-colors">
              Choose File
              <input type="file" accept=".pdf,.png,.jpg,.jpeg,.bmp,.tiff" className="hidden" onChange={handleFileInput} />
            </label>
            <p className="text-xs text-slate-400 mt-4">or drag and drop here</p>
          </>
        )}

        {isBusy && (
          <div className="py-4">
            <Loader2 className="mx-auto text-teal-600 animate-spin mb-4" size={36} />
            <p className="font-medium text-slate-700">
              {status === "uploading" ? "Extracting text & redacting PII…" : "Analyzing policy with AI…"}
            </p>
            {uploadResult && (
              <div className="mt-4 text-sm text-slate-500 space-y-1 text-left inline-block">
                <div className="flex items-center gap-2"><FileText size={14} /> {uploadResult.filename}</div>
                <div>Document type: <span className="font-medium text-slate-700">{uploadResult.documentType}</span></div>
                <div>OCR: <span className="font-medium text-slate-700">{uploadResult.ocrUsed ? "Used" : "Not Used"}</span></div>
                <div>Pages: <span className="font-medium text-slate-700">{uploadResult.pageCount}</span></div>
                <div className="flex items-center gap-1 text-teal-700"><ShieldCheck size={14} /> PII masked: {uploadResult.privacy.fieldsMasked}</div>
              </div>
            )}
          </div>
        )}
      </div>

      {status === "error" && (
        <div className="mt-6 max-w-lg w-full bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-medium">Could not process document</p>
            <p className="text-sm text-red-600 mt-0.5">{error}</p>
            <button onClick={() => setStatus("idle")} className="text-sm underline mt-2">Try again</button>
          </div>
        </div>
      )}
    </div>
  );
}
