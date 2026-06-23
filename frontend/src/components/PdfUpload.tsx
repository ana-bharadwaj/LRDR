import { useRef, useState } from "react";

import { uploadPdf } from "../lib/api";

interface Props {
  onIndexed: (chunks: number, filename: string) => void;
}

export default function PdfUpload({ onIndexed }: Props) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File | null) {
    if (!file) return;
    setError(null);
    setIsUploading(true);
    try {
      const result = await uploadPdf(file);
      onIndexed(result.chunks_indexed, result.filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-700">Document</h2>
      <p className="mt-1 text-xs text-slate-500">
        Upload a PDF. It's chunked and embedded locally via Ollama — nothing leaves your machine.
      </p>

      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
        className="mt-4 w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isUploading ? "Indexing…" : "Choose PDF"}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
      />

      {error && <p className="mt-3 text-xs text-red-600">{error}</p>}
    </div>
  );
}
