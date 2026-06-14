const API_BASE = "http://localhost:8000";
const API_KEY  = "mme-secret-2024";

const headers = {
  "X-API-Key": API_KEY,
  "Content-Type": "application/json",
};

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function getMeetings() {
  const res = await fetch(`${API_BASE}/meetings`, { headers });
  return res.json();
}

export async function postQuery(question, { dateFrom, dateTo, topK = 3 } = {}) {
  const body = { question, top_k: topK };
  if (dateFrom) body.date_from = dateFrom;
  if (dateTo)   body.date_to   = dateTo;

  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  return res.json();
}

export async function postActionItems(question, { dateFrom, dateTo } = {}) {
  const body = { question };
  if (dateFrom) body.date_from = dateFrom;
  if (dateTo)   body.date_to   = dateTo;

  const res = await fetch(`${API_BASE}/action-items`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  return res.json();
}

export async function postEvaluate(question, answer, contexts) {
  const res = await fetch(`${API_BASE}/evaluate`, {
    method: "POST",
    headers,
    body: JSON.stringify({ question, answer, contexts }),
  });
  return res.json();
}

export async function postChat(question, history, { dateFrom, dateTo, topK = 3 } = {}) {
  const body = { question, history, top_k: topK };
  if (dateFrom) body.date_from = dateFrom;
  if (dateTo)   body.date_to   = dateTo;

  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  return res.json();
}

export async function getSummary(meetingDate) {
  const res = await fetch(`${API_BASE}/summary/${meetingDate}`, { headers });
  return res.json();
}

export async function postTranscribe(file, meetingTitle, meetingDate) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("meeting_title", meetingTitle);
  if (meetingDate) formData.append("meeting_date", meetingDate);
  formData.append("auto_ingest", "true");

  const res = await fetch(`${API_BASE}/transcribe`, {
    method: "POST",
    headers: { "X-API-Key": API_KEY },
    body: formData,
  });
  return res.json();
}

export async function postIngest() {
  const res = await fetch(`${API_BASE}/ingest`, {
    method: "POST",
    headers,
  });
  return res.json();
}