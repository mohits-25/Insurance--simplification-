const SEVERITY_STYLES = {
  high: "bg-red-50 border-red-200 text-red-700",
  medium: "bg-amber-50 border-amber-200 text-amber-700",
  low: "bg-slate-50 border-slate-200 text-slate-600",
};

export default function ClauseList({ items, emptyLabel = "None found in this policy." }) {
  if (!items || items.length === 0) {
    return <p className="text-sm text-slate-400 italic">{emptyLabel}</p>;
  }

  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <div key={i} className={`border rounded-xl p-4 ${SEVERITY_STYLES[item.severity] || SEVERITY_STYLES.low}`}>
          <div className="flex items-start justify-between gap-3">
            <p className="font-semibold">{item.title}</p>
            <span className="text-xs uppercase tracking-wide font-medium opacity-70 shrink-0">{item.severity}</span>
          </div>
          <p className="text-sm mt-1 opacity-90">{item.explanation}</p>
          {(item.page || item.section) && (
            <p className="text-xs mt-2 opacity-60">
              {item.section && <span>Section: {item.section}</span>}
              {item.section && item.page && <span> · </span>}
              {item.page && <span>Page {item.page}</span>}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
