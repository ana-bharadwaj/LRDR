import { useState } from "react";

import { askQuestion, type AskResponse } from "../lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  meta?: Pick<AskResponse, "model_used" | "sources" | "processing_time_seconds">;
}

interface Props {
  documentReady: boolean;
}

export default function ChatWindow({ documentReady }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isAsking, setIsAsking] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || isAsking) return;

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setIsAsking(true);

    try {
      const res = await askQuestion(question);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          meta: {
            model_used: res.model_used,
            sources: res.sources,
            processing_time_seconds: res.processing_time_seconds,
          },
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: err instanceof Error ? `Error: ${err.message}` : "Something went wrong.",
        },
      ]);
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex-1 space-y-4 overflow-y-auto p-6">
        {messages.length === 0 && (
          <p className="text-sm text-slate-400">
            {documentReady
              ? "Ask anything about the uploaded document."
              : "Upload a PDF to start asking questions."}
          </p>
        )}

        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <div
              className={
                m.role === "user"
                  ? "inline-block max-w-[80%] rounded-lg bg-slate-900 px-4 py-2 text-sm text-white"
                  : "inline-block max-w-[80%] rounded-lg bg-slate-100 px-4 py-2 text-sm text-slate-800"
              }
            >
              {m.content}
            </div>
            {m.meta && (
              <div className="mt-1 text-[11px] text-slate-400">
                {m.meta.model_used} · {m.meta.processing_time_seconds.toFixed(1)}s
                {m.meta.sources.length > 0 &&
                  ` · pages: ${m.meta.sources.map((s) => s.page).join(", ")}`}
              </div>
            )}
          </div>
        ))}

        {isAsking && <p className="text-sm text-slate-400">Thinking…</p>}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 border-t border-slate-200 p-4">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={!documentReady || isAsking}
          placeholder={documentReady ? "Ask a question about the document…" : "Upload a PDF first"}
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500 disabled:bg-slate-50"
        />
        <button
          type="submit"
          disabled={!documentReady || isAsking || !input.trim()}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
