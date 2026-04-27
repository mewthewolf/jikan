import "./styles.css";

const BACKEND_URL = window.__JIKAN_BACKEND_URL__ || "http://127.0.0.1:8000";

const state = {
  status: "Idle",
  error: "",
  latestReport: null,
  activeSessionId: null,
};

const app = document.querySelector("#app");

app.innerHTML = `
  <main class="shell">
    <section class="hero">
      <div>
        <p class="eyebrow">Local ActivityWatch Controller</p>
        <h1>Jikan</h1>
        <p class="subtitle">Start a session, stop it when you are done, and review the generated work report without leaving your main editor.</p>
      </div>
      <div class="status-card">
        <span class="status-label">Status</span>
        <span id="status-pill" class="status-pill status-idle">Idle</span>
      </div>
    </section>

    <section class="panel controls-panel">
      <div class="controls">
        <button id="start-button" class="primary-button">Start</button>
        <button id="stop-button" class="secondary-button">Stop</button>
      </div>
      <div class="meta-row">
        <span id="backend-url">${BACKEND_URL}</span>
        <span id="session-label">No active session</span>
      </div>
      <p id="error-message" class="error-message" hidden></p>
    </section>

    <section class="panel report-panel">
      <div class="report-header">
        <div>
          <p class="eyebrow">Latest Report</p>
          <h2>Session Summary</h2>
        </div>
        <div id="report-timestamp" class="timestamp">No report yet</div>
      </div>
      <pre id="report-content" class="report-content">Start and stop a session to generate your first report.</pre>
    </section>
  </main>
`;

const startButton = document.querySelector("#start-button");
const stopButton = document.querySelector("#stop-button");
const statusPill = document.querySelector("#status-pill");
const errorMessage = document.querySelector("#error-message");
const sessionLabel = document.querySelector("#session-label");
const reportTimestamp = document.querySelector("#report-timestamp");
const reportContent = document.querySelector("#report-content");

startButton.addEventListener("click", () => runAction(startSession));
stopButton.addEventListener("click", () => runAction(stopSession));

void bootstrap();

async function bootstrap() {
  await refreshState();
  render();
}

async function runAction(action) {
  state.error = "";
  render();
  try {
    await action();
  } catch (error) {
    state.status = "Error";
    state.error = error instanceof Error ? error.message : String(error);
    render();
  }
}

async function startSession() {
  state.status = "Tracking";
  render();
  const response = await request("/sessions/start", { method: "POST" });
  state.activeSessionId = response.session_id;
  await refreshState();
}

async function stopSession() {
  state.status = "Processing";
  render();
  const response = await request("/sessions/stop", { method: "POST" });
  await pollForLatestReport(response.report_id);
  state.activeSessionId = null;
  await refreshState();
}

async function refreshState() {
  const [active, latestReport] = await Promise.all([
    request("/sessions/active"),
    request("/reports/latest"),
  ]);

  state.latestReport = latestReport;
  if (active.active_session) {
    state.activeSessionId = active.active_session.id;
    state.status = active.active_session.status === "processing" ? "Processing" : "Tracking";
    if (active.active_session.status === "error") {
      state.status = "Error";
      state.error = active.active_session.error_message || "Session processing failed.";
    }
  } else if (state.status !== "Error") {
    state.activeSessionId = null;
    state.status = "Idle";
  }
  render();
}

async function pollForLatestReport(expectedReportId) {
  for (let attempt = 0; attempt < 10; attempt += 1) {
    const latest = await request("/reports/latest");
    if (latest && (!expectedReportId || latest.id === expectedReportId)) {
      state.latestReport = latest;
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
}

async function request(path, options = {}) {
  const response = await fetch(`${BACKEND_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  const text = await response.text();
  if (!text || text.trim() === "null") {
    return null;
  }
  return JSON.parse(text);
}

function render() {
  const statusSlug = state.status.toLowerCase();
  statusPill.textContent = state.status;
  statusPill.className = `status-pill status-${statusSlug}`;

  errorMessage.hidden = !state.error;
  errorMessage.textContent = state.error;

  startButton.disabled = state.status === "Tracking" || state.status === "Processing";
  stopButton.disabled = state.status !== "Tracking";

  sessionLabel.textContent = state.activeSessionId ? `Session #${state.activeSessionId}` : "No active session";

  if (state.latestReport) {
    reportTimestamp.textContent = new Date(state.latestReport.created_at).toLocaleString();
    reportContent.textContent = state.latestReport.markdown;
  } else {
    reportTimestamp.textContent = "No report yet";
    reportContent.textContent = "Start and stop a session to generate your first report.";
  }
}
