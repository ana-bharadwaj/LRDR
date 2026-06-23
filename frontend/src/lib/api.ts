const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface UploadResponse {
  filename: string;
  chunks_indexed: number;
  index_name: string;
}

export interface SourceSnippet {
  page: number | string;
  snippet: string;
}

export interface AskResponse {
  answer: string;
  model_used: string;
  sources: SourceSnippet[];
  processing_time_seconds: number;
}

export interface StatusResponse {
  index_name: string;
  indexed: boolean;
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed with status ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function uploadPdf(file: File, indexName = "default"): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/upload?index_name=${encodeURIComponent(indexName)}`, {
    method: "POST",
    body: formData,
  });
  return handle<UploadResponse>(res);
}

export async function askQuestion(
  question: string,
  indexName = "default",
  showSources = true,
): Promise<AskResponse> {
  const res = await fetch(`${API_BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, index_name: indexName, show_sources: showSources }),
  });
  return handle<AskResponse>(res);
}

export async function getStatus(indexName = "default"): Promise<StatusResponse> {
  const res = await fetch(`${API_BASE}/status?index_name=${encodeURIComponent(indexName)}`);
  return handle<StatusResponse>(res);
}
