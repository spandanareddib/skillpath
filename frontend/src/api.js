// All communication with the FastAPI backend lives in this one file.
const BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

// FastAPI sends errors as {"detail": "text"} or, for validation errors, {"detail": [{"msg": ...}]}.
function messageFrom(body, fallback) {
  const detail = body && body.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join("; ");
  return fallback;
}

async function request(path, { method = "GET", token, json, form, body } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(json);
  } else if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload = new URLSearchParams(form);
  } else if (body) {
    payload = body; // FormData: the browser sets the multipart boundary itself
  }

  let res;
  try {
    res = await fetch(`${BASE}${path}`, { method, headers, body: payload });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Is the backend running on port 8000?");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, messageFrom(data, `Request failed (${res.status})`));
  return data;
}

export const api = {
  signup: (email, password, full_name) =>
    request("/auth/signup", { method: "POST", json: { email, password, full_name, role: "job_seeker" } }),
  // The login endpoint follows the OAuth2 form standard, so it takes form fields, not JSON.
  login: async (email, password) =>
    (await request("/auth/login", { method: "POST", form: { username: email, password } })).access_token,
  me: (token) => request("/auth/me", { token }),
  resumes: (token) => request("/resumes", { token }),
  uploadResume: (token, file) => {
    const data = new FormData();
    data.append("file", file);
    return request("/resumes", { method: "POST", token, body: data });
  },
  jobs: (token) => request("/jobs", { token }),
  createJob: (token, job) => request("/jobs", { method: "POST", token, json: job }),
  deleteJob: (token, id) => request(`/jobs/${id}`, { method: "DELETE", token }),
  gap: (token, jobId, resumeId) => request(`/jobs/${jobId}/gap?resume_id=${resumeId}`, { token }),
};
