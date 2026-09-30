const API_BASE = "http://localhost:8000/api";

async function handleResponse(res) {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data.detail) detail = data.detail;
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
  return handleResponse(res);
}

export async function analyzeDocument(documentId) {
  const res = await fetch(`${API_BASE}/analyze/${documentId}`, { method: "POST" });
  return handleResponse(res);
}

export async function getDashboard(documentId) {
  const res = await fetch(`${API_BASE}/dashboard/${documentId}`);
  return handleResponse(res);
}

export async function askPolicy(documentId, question) {
  const res = await fetch(`${API_BASE}/chat/${documentId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return handleResponse(res);
}

export async function runWhatIf(documentId, scenario) {
  const res = await fetch(`${API_BASE}/whatif/${documentId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
  });
  return handleResponse(res);
}

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return handleResponse(res);
}
