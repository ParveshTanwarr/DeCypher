import { Download, FileJson, FileSpreadsheet, FileText } from "lucide-react";
import { useEffect, useState } from "react";
import { downloadExport } from "../../api/client";

type ExportFormat = "pdf" | "csv" | "json";

export default function ExportMenu({
  onExport,
}: {
  onExport?: (format: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<ExportFormat | "">("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: MouseEvent) {
      const target = event.target;
      if (target instanceof Node && !(target as HTMLElement).closest(".export-wrap")) {
        setOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  async function exportFile(format: ExportFormat) {
    if (busy) return;

    setBusy(format);
    setError("");

    try {
      await downloadExport(format);
      onExport?.(format.toUpperCase());
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="export-wrap">
      <button
        type="button"
        className="secondary-button export-button"
        onClick={() => {
          setError("");
          setOpen((value) => !value);
        }}
        disabled={!!busy}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <Download size={15} />
        {busy ? "Preparing…" : "Export"}
      </button>

      {open && (
        <div className="export-menu" role="menu" aria-label="Export formats">
          <button
            type="button"
            role="menuitem"
            onClick={() => exportFile("pdf")}
            disabled={!!busy}
          >
            <FileText size={15} />
            <span>
              <strong>{busy === "pdf" ? "Preparing PDF…" : "PDF Report"}</strong>
              <small>Formatted intelligence report</small>
            </span>
          </button>

          <button
            type="button"
            role="menuitem"
            onClick={() => exportFile("csv")}
            disabled={!!busy}
          >
            <FileSpreadsheet size={15} />
            <span>
              <strong>{busy === "csv" ? "Preparing CSV…" : "CSV"}</strong>
              <small>Spreadsheet-ready actor data</small>
            </span>
          </button>

          <button
            type="button"
            role="menuitem"
            onClick={() => exportFile("json")}
            disabled={!!busy}
          >
            <FileJson size={15} />
            <span>
              <strong>{busy === "json" ? "Preparing JSON…" : "JSON"}</strong>
              <small>Machine-readable records</small>
            </span>
          </button>

          {error && <div className="export-error" role="alert">{error}</div>}
        </div>
      )}
    </div>
  );
}
