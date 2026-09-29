import { Download, FileJson, FileSpreadsheet, FileText } from "lucide-react";
import { useState } from "react";
import { downloadExport } from "../../api/client";

export default function ExportMenu({ onExport }: { onExport?: (format: string) => void }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  async function exportFile(format: "pdf" | "csv" | "json") {
    setBusy(format); setError("");
    try {
      await downloadExport(format);
      onExport?.(format.toUpperCase());
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed.");
    } finally { setBusy(""); }
  }

  return (
    <div className="export-wrap">
      <button className="secondary-button export-button" onClick={() => setOpen((value) => !value)} disabled={!!busy}>
        <Download size={15} /> {busy ? "Preparing…" : "Export"}
      </button>
      {open && (
        <div className="export-menu">
          <button onClick={() => exportFile("pdf")}><FileText size={15} /><span><strong>PDF Report</strong><small>Formatted intelligence report</small></span></button>
          <button onClick={() => exportFile("csv")}><FileSpreadsheet size={15} /><span><strong>CSV</strong><small>Spreadsheet-ready actor data</small></span></button>
          <button onClick={() => exportFile("json")}><FileJson size={15} /><span><strong>JSON</strong><small>Machine-readable records</small></span></button>
          {error && <div className="export-error">{error}</div>}
        </div>
      )}
    </div>
  );
}
