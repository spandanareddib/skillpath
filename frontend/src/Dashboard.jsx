import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import Results from "./Results";

const EMPTY_JOB = { title: "", company: "", description: "" };

export default function Dashboard({ token, user, onLogout }) {
  const [resumes, setResumes] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [resumeId, setResumeId] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [jobForm, setJobForm] = useState(EMPTY_JOB);
  const [result, setResult] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  // A 401 means the token expired: go back to the login page. Anything else is shown to the user.
  const fail = useCallback(
    (err) => {
      if (err.status === 401) onLogout("Your session expired. Please log in again.");
      else setError(err.message);
    },
    [onLogout],
  );

  const refresh = useCallback(async () => {
    try {
      const [r, j] = await Promise.all([api.resumes(token), api.jobs(token)]);
      setResumes(r);
      setJobs(j);
      setResumeId((current) => current ?? r.find((x) => x.status === "parsed")?.id ?? null);
      setJobId((current) => current ?? j[0]?.id ?? null);
    } catch (err) {
      fail(err);
    }
  }, [token, fail]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function uploadResume(e) {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;
    setError("");
    setMessage("");
    setBusy("upload");
    try {
      const created = await api.uploadResume(token, file);
      await refresh();
      if (created.status === "parsed") {
        setResumeId(created.id);
        setResult(null);
      } else {
        setError(`Could not read ${created.filename}: ${created.error}`);
      }
    } catch (err) {
      fail(err);
    } finally {
      setBusy("");
    }
  }

  async function addJob(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    setBusy("job");
    try {
      const created = await api.createJob(token, jobForm);
      setJobForm(EMPTY_JOB);
      await refresh();
      setJobId(created.id);
      setResult(null);
      setMessage(`Found ${created.skills.length} skills in "${created.title}".`);
    } catch (err) {
      fail(err);
    } finally {
      setBusy("");
    }
  }

  async function removeJob(id) {
    if (!window.confirm("Delete this job?")) return;
    setError("");
    try {
      await api.deleteJob(token, id);
      if (jobId === id) {
        setJobId(null);
        setResult(null);
      }
      await refresh();
    } catch (err) {
      fail(err);
    }
  }

  async function analyze() {
    setError("");
    setMessage("");
    setBusy("analyze");
    try {
      setResult(await api.gap(token, jobId, resumeId));
    } catch (err) {
      setResult(null);
      fail(err);
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="page">
      <header>
        <h1>SkillPath</h1>
        <div>
          <span className="muted">{user.full_name || user.email}</span>
          <button className="link" onClick={() => onLogout()}>
            Log out
          </button>
        </div>
      </header>

      {error && <p className="error banner">{error}</p>}
      {message && <p className="notice banner">{message}</p>}

      <div className="grid">
        <section className="card">
          <h2>1. Your resume</h2>
          <label className="upload">
            {busy === "upload" ? "Reading resume..." : "Upload a PDF or DOCX"}
            <input type="file" accept=".pdf,.docx" onChange={uploadResume} disabled={busy === "upload"} />
          </label>
          <ul className="list">
            {resumes.length === 0 && <li className="muted">No resumes yet.</li>}
            {resumes.map((r) => (
              <li key={r.id}>
                <button
                  className={`item ${r.id === resumeId ? "selected" : ""}`}
                  disabled={r.status !== "parsed"}
                  onClick={() => {
                    setResumeId(r.id);
                    setResult(null);
                  }}
                >
                  <span>{r.filename}</span>
                  <span className={`badge ${r.status}`}>{r.status}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="card">
          <h2>2. A job you want</h2>
          <form onSubmit={addJob}>
            <label>
              Job title
              <input required value={jobForm.title} onChange={(e) => setJobForm({ ...jobForm, title: e.target.value })} />
            </label>
            <label>
              Company (optional)
              <input value={jobForm.company} onChange={(e) => setJobForm({ ...jobForm, company: e.target.value })} />
            </label>
            <label>
              Paste the job description
              <textarea
                required
                rows={7}
                minLength={30}
                value={jobForm.description}
                onChange={(e) => setJobForm({ ...jobForm, description: e.target.value })}
                placeholder={"Requirements:\n- Python and FastAPI\n\nNice to have:\n- Docker"}
              />
            </label>
            <button className="primary" disabled={busy === "job"}>
              {busy === "job" ? "Saving..." : "Save job"}
            </button>
          </form>
          <ul className="list">
            {jobs.map((j) => (
              <li key={j.id} className="row">
                <button
                  className={`item ${j.id === jobId ? "selected" : ""}`}
                  onClick={() => {
                    setJobId(j.id);
                    setResult(null);
                  }}
                >
                  <span>
                    {j.title}
                    {j.company && <span className="muted"> at {j.company}</span>}
                  </span>
                </button>
                <button className="link danger" onClick={() => removeJob(j.id)}>
                  Delete
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="actions">
        <button className="primary big" disabled={!resumeId || !jobId || busy === "analyze"} onClick={analyze}>
          {busy === "analyze" ? "Analyzing..." : "3. Analyze my fit"}
        </button>
        {(!resumeId || !jobId) && <span className="muted">Select a parsed resume and a job first.</span>}
      </div>

      {result && <Results data={result} />}
    </div>
  );
}
