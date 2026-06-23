import { useState } from "react";

import ChatWindow from "./components/ChatWindow";
import PdfUpload from "./components/PdfUpload";

export default function App() {
  const [documentReady, setDocumentReady] = useState(false);
  const [statusLine, setStatusLine] = useState<string | null>(null);

  function handleIndexed(chunks: number, filename: string) {
    setDocumentReady(true);
    setStatusLine(`${filename} — ${chunks} chunks indexed`);
  }

  return (
    <div className="mx-auto flex h-screen max-w-5xl flex-col p-6">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-slate-900">LRDA</h1>
        <p className="text-sm text-slate-500">
          Offline PDF Question Answering.
        </p>
        {statusLine && <p className="mt-1 text-xs text-emerald-600">{statusLine}</p>}
      </header>

      <div className="grid flex-1 grid-cols-1 gap-6 overflow-hidden md:grid-cols-3">
        <div className="md:col-span-1">
          <PdfUpload onIndexed={handleIndexed} />
        </div>
        <div className="md:col-span-2">
          <ChatWindow documentReady={documentReady} />
        </div>
      </div>
    </div>
  );
}
