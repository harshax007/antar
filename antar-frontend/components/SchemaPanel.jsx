/**
 * SchemaPanel.jsx — Official Karnataka Police ER Schema Explorer (Phase L2 & L6)
 * Renders the ER tables as cards with real row counts, fill rate bars, column counts,
 * and clear SCRB extract integrity notes.
 */
import React, { useState, useEffect } from "react";

export default function SchemaPanel({ kn = false }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedTable, setSelectedTable] = useState(null);

  useEffect(() => {
    fetch("/api/schema/er")
      .then((res) => res.json())
      .then((d) => {
        setData(d);
        if (d.tables && d.tables.length > 0) {
          setSelectedTable(d.tables[0].table_name);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="py-8 text-center text-xs text-muted-foreground animate-pulse">
        {kn ? "ಅಧಿಕೃತ ER ರಚನೆಯನ್ನು ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ..." : "Loading official ER schema..."}
      </div>
    );
  }

  if (!data || !data.available) {
    return (
      <div className="rounded-lg border border-border/40 bg-card/60 p-6 text-center text-xs text-muted-foreground">
        {kn ? "ಅಧಿಕೃತ ER ಕೋಷ್ಟಕಗಳು ಲ್ಯಾಬ್ ಆವೃತ್ತಿಯಲ್ಲಿ ಲಭ್ಯವಿದೆ." : "Official ER tables are active in Antar Lab edition."}
      </div>
    );
  }

  const currentTbl = data.tables?.find((t) => t.table_name === selectedTable);
  const fillRateMap = {};
  data.fill_rates?.forEach((fr) => {
    fillRateMap[fr.table_name] = fr;
  });

  return (
    <div className="space-y-6 text-left">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/40 pb-3">
        <div>
          <h4 className="text-sm font-bold text-foreground">
            {kn ? "ಕರ್ನಾಟಕ ಪೊಲೀಸ್ ಅಧಿಕೃತ ER ರಚನೆ" : "Karnataka Police Official ER Schema Tables"}
          </h4>
          <p className="text-xs text-muted-foreground">
            {kn
              ? "ನೈಜ FIR ದಾಖಲೆಗಳಿಂದ ಪಡೆಯಲಾದ ಕೋಷ್ಟಕಗಳು, ಪ್ರಾಮಾಣಿಕ ಭರ್ತಿ ದರಗಳು ಮತ್ತು ವಿದೇಶಿ ಕೀ ಸಮಗ್ರತೆ."
              : "Derived directly from the SCRB extract: real CaseMaster (2.04M rows), act-sections, and honest unpopulated person tables."}
          </p>
        </div>
        <div className="text-xs font-mono text-primary font-semibold">
          {data.table_count} {kn ? "ಕೋಷ್ಟಕಗಳು" : "Tables"}
        </div>
      </div>

      {/* Tables Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
        {data.tables?.map((t) => {
          const fr = fillRateMap[t.table_name];
          const pct = fr ? fr.filled_pct : 100.0;
          const isSelected = selectedTable === t.table_name;
          const isZero = t.rows === 0;

          return (
            <button
              key={t.table_name}
              onClick={() => setSelectedTable(t.table_name)}
              className={`rounded-lg border p-2.5 text-left transition-all ${
                isSelected
                  ? "border-primary bg-primary/10 shadow-sm"
                  : "border-border/40 bg-card/40 hover:border-border/80"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-foreground truncate">{t.table_name}</span>
                {isZero && (
                  <span className="rounded bg-amber-500/10 px-1 py-0.2 text-[9px] font-semibold text-amber-400">
                    0 rows
                  </span>
                )}
              </div>
              <div className="mt-1 flex items-center justify-between text-[11px] text-muted-foreground">
                <span>{t.rows.toLocaleString()} rows</span>
                <span>{t.column_count} cols</span>
              </div>
              {/* Fill bar */}
              <div className="mt-2 h-1 w-full rounded-full bg-border/40 overflow-hidden">
                <div
                  className={`h-full ${pct > 80 ? "bg-emerald-400" : pct > 0 ? "bg-sky-400" : "bg-muted-foreground/30"}`}
                  style={{ width: `${Math.max(4, pct)}%` }}
                />
              </div>
            </button>
          );
        })}
      </div>

      {/* Selected Table Detail */}
      {currentTbl && (
        <div className="rounded-xl border border-border/60 bg-background/60 p-4 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/30 pb-3">
            <div>
              <span className="font-mono text-sm font-bold text-primary">{currentTbl.table_name}</span>
              {fillRateMap[currentTbl.table_name] && (
                <span className="ml-2 text-xs text-muted-foreground">
                  — {fillRateMap[currentTbl.table_name].note} ({fillRateMap[currentTbl.table_name].source})
                </span>
              )}
            </div>
            <div className="text-xs font-mono text-muted-foreground">
              {currentTbl.rows.toLocaleString()} {kn ? "ಸಾಲುಗಳು" : "rows"} · {currentTbl.column_count} {kn ? "ಅಂಕಣಗಳು" : "columns"}
            </div>
          </div>

          {/* Columns Tag Cloud / Table */}
          <div className="overflow-x-auto max-h-48 overflow-y-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="text-muted-foreground border-b border-border/20">
                  <th className="py-1.5 px-2">CID</th>
                  <th className="py-1.5 px-2">Column Name</th>
                  <th className="py-1.5 px-2">Type</th>
                  <th className="py-1.5 px-2 text-right">PK</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/10">
                {currentTbl.columns?.map((c) => (
                  <tr key={c.cid} className="hover:bg-card/30">
                    <td className="py-1 px-2 text-muted-foreground">{c.cid}</td>
                    <td className="py-1 px-2 text-foreground font-semibold">{c.name}</td>
                    <td className="py-1 px-2 text-sky-400">{c.type || "ANY"}</td>
                    <td className="py-1 px-2 text-right text-emerald-400">{c.pk ? "✓ PK" : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Extract Reality Notes */}
      {data.notes && data.notes.length > 0 && (
        <div className="border-t border-border/40 pt-4">
          <h5 className="text-xs font-bold text-foreground mb-2">
            {kn ? "ದತ್ತಾಂಶ ವಾಸ್ತವತೆ ಮತ್ತು ಮಿತಿಗಳ ಟಿಪ್ಪಣಿಗಳು" : "Extract Reality & Schema Integrity Notes"}
          </h5>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            {data.notes.map((n) => (
              <div key={n.note_id} className="rounded-lg bg-card/40 border border-border/30 p-2.5">
                <span className="font-semibold text-primary">{n.topic}: </span>
                <span className="text-muted-foreground">{n.note}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
