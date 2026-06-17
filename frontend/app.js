const state = {
  settings: null,
  commands: [],
  currentPlan: null,
  currentIntent: null,
  apiReady: false,
  liveReady: false,
  poller: null,
};

const $ = (id) => document.getElementById(id);

function writeOutput(text, mode = "info") {
  const output = $("output");
  const prefix = mode === "error" ? "[ERROR]" : mode === "ok" ? "[OK]" : mode === "cmd" ? "PS >" : "[INFO]";
  output.textContent += `${prefix} ${text}\n`;
  output.scrollTop = output.scrollHeight;
}

function appendRaw(text) {
  if (!text) return;
  const output = $("output");
  output.textContent += text;
  output.scrollTop = output.scrollHeight;
}

function setStatus(text, type = "") {
  const pill = $("statusPill");
  pill.textContent = text;
  pill.className = `status-pill ${type}`.trim();
}

function setPlan(plan, preview, intent) {
  state.currentPlan = plan;
  state.currentIntent = intent;
  if (!plan) {
    $("planBox").textContent = "Enter: ارسال مستقیم به PowerShell | Ctrl+Enter: تشخیص فارسی";
    $("runBtn").disabled = true;
    return;
  }
  $("cwdLabel").textContent = plan.project_path || ".";
  $("planBox").innerHTML = `<strong>${escapeHtml(plan.title_fa)}</strong><span> · ریسک: ${escapeHtml(plan.risk)}</span><code dir="ltr">${escapeHtml(preview)}</code><span>${escapeHtml(plan.explanation_fa || "")}</span>`;
  $("runBtn").disabled = false;
}

function escapeHtml(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

function pyApi() {
  return window.pywebview && window.pywebview.api ? window.pywebview.api : null;
}

async function boot() {
  const api = pyApi();
  if (!api) {
    setStatus("Waiting API", "warn");
    return;
  }
  state.apiReady = true;
  setStatus("Loading", "warn");
  try {
    const data = await api.get_bootstrap();
    state.settings = data.settings;
    state.commands = data.commands || [];
    hydrateSettings(data.settings);
    renderCommands(state.commands);
    if (!data.ok) {
      writeOutput(data.catalog_error || "خطای catalog", "error");
      setStatus("Catalog Error", "error");
      return;
    }
    await startLive();
    setPlan(null);
    writeOutput("FaCoderTerminal آماده است.", "ok");
    writeOutput("Enter دستور را مستقیم داخل PowerShell داخلی اجرا می‌کند.");
    writeOutput("Ctrl+Enter دستور فارسی را با FaCoder تحلیل می‌کند.");
    setStatus("Ready", "ok");
    $("requestInput").focus();
  } catch (error) {
    writeOutput(`خطای شروع برنامه: ${error}`, "error");
    setStatus("Boot Error", "error");
  }
}

async function startLive() {
  const api = pyApi();
  const result = await api.live_start($("projectPath").value.trim());
  if (!result.ok) {
    writeOutput(result.message_fa || "راه‌اندازی PowerShell داخلی ناموفق بود.", "error");
    if (result.technical) writeOutput(result.technical, "error");
    setStatus("PTY Error", "error");
    return;
  }
  state.liveReady = true;
  if (result.cwd) $("cwdLabel").textContent = result.cwd;
  if (state.poller) clearInterval(state.poller);
  state.poller = setInterval(pollLive, 120);
}

async function pollLive() {
  const api = pyApi();
  if (!api || !state.liveReady) return;
  try {
    const result = await api.live_read();
    if (result.ok && result.output) appendRaw(result.output);
  } catch (_) {}
}

function hydrateSettings(settings) {
  if (!settings) return;
  $("baseUrl").value = settings.llm?.base_url || "";
  $("apiKey").value = settings.llm?.api_key || "";
  $("modelName").value = settings.llm?.model || "";
  $("llmEnabled").checked = Boolean(settings.llm?.enabled);
  $("projectPath").value = settings.default_project_path || "";
  $("githubRepoUrl").value = settings.github?.repo_url || "";
  $("githubBranch").value = settings.github?.default_branch || "main";
  $("serverName").value = settings.server?.name || "production";
  $("serverHost").value = settings.server?.host || "";
  $("serverPort").value = settings.server?.port || 22;
  $("serverUser").value = settings.server?.username || "";
  $("serverProjectPath").value = settings.server?.project_path || "";
  $("serverKeyPath").value = settings.server?.key_path || "";
  $("cwdLabel").textContent = settings.default_project_path || ".";
}

function collectSettings() {
  const previous = state.settings || {};
  return {
    ...previous,
    default_project_path: $("projectPath").value.trim(),
    github: { ...(previous.github || {}), repo_url: $("githubRepoUrl").value.trim(), default_branch: $("githubBranch").value.trim() || "main", use_gh_cli: true },
    server: { ...(previous.server || {}), name: $("serverName").value.trim() || "production", host: $("serverHost").value.trim(), port: Number($("serverPort").value.trim() || 22), username: $("serverUser").value.trim(), project_path: $("serverProjectPath").value.trim(), key_path: $("serverKeyPath").value.trim(), auth_note: "password is not stored" },
    llm: { ...(previous.llm || {}), provider_type: "openai_compatible", base_url: $("baseUrl").value.trim(), api_key: $("apiKey").value.trim(), model: $("modelName").value.trim(), temperature: 0, enabled: $("llmEnabled").checked },
  };
}

function renderCommands(commands) {
  const box = $("commandsList");
  box.innerHTML = "";
  commands.forEach((command) => {
    const item = document.createElement("button");
    item.className = "command-item";
    item.innerHTML = `<strong>${escapeHtml(command.title_fa)}</strong><span>${escapeHtml(command.id)} · ${escapeHtml(command.risk)}</span>`;
    item.addEventListener("click", async () => {
      $("requestInput").value = command.aliases_fa?.[0] || command.title_fa;
      hideModal("commandsModal");
      await parseRequest();
    });
    box.appendChild(item);
  });
}

async function saveSettings() {
  const api = pyApi();
  if (!api) return;
  const result = await api.save_settings(collectSettings());
  if (result.ok) {
    state.settings = result.settings;
    hydrateSettings(result.settings);
    writeOutput("تنظیمات ذخیره شد.", "ok");
    setStatus("Saved", "ok");
    hideModal("settingsModal");
  }
}

async function testLlm() {
  const api = pyApi();
  if (!api) return;
  await saveSettings();
  const result = await api.test_llm();
  writeOutput(result.message_fa, result.ok ? "ok" : "error");
  setStatus(result.ok ? "LLM OK" : "LLM Error", result.ok ? "ok" : "error");
}

async function makeKeypair() {
  const api = pyApi();
  if (!api) return;
  await saveSettings();
  const result = await api.make_keypair();
  writeOutput(result.message_fa || JSON.stringify(result), result.ok ? "ok" : "error");
  if (result.key_path) {
    $("serverKeyPath").value = result.key_path;
    writeOutput(`Key: ${result.key_path}`, "ok");
  }
}

async function refreshSync() {
  const api = pyApi();
  if (!api) return;
  await saveSettings();
  showModal("syncModal");
  $("syncOutput").textContent = "در حال بررسی هماهنگی...";
  const result = await api.sync_health();
  $("syncOutput").textContent = JSON.stringify(result, null, 2);
  writeOutput("هماهنگی Local/GitHub/Server بررسی شد.", result.ok ? "ok" : "error");
}

async function parseRequest() {
  const api = pyApi();
  if (!api) return;
  const text = $("requestInput").value.trim();
  if (!text) return;
  writeOutput(text, "cmd");
  setStatus("Parsing", "warn");
  setPlan(null);
  const result = await api.parse_request(text, $("projectPath").value.trim());
  if (!result.ok) {
    writeOutput(result.message_fa || "تشخیص ناموفق بود.", "error");
    setStatus("Parse Error", "error");
    return;
  }
  setPlan(result.plan, result.command_preview, result.intent);
  writeOutput(`تشخیص: ${result.plan.command_id} (${result.intent.source})`, "ok");
  setStatus("Parsed", "ok");
}

async function sendToLive() {
  const api = pyApi();
  if (!api || !state.liveReady) return;
  const text = $("requestInput").value;
  if (!text.trim()) return;
  await api.live_send(text + "\r");
  $("requestInput").value = "";
}

async function runCurrent(confirmed = false) {
  const api = pyApi();
  if (!api || !state.currentPlan) return;
  if (state.currentPlan.requires_confirmation && !confirmed) {
    showConfirm();
    return;
  }
  const commandLine = state.currentPlan.argv.join(" ");
  await api.live_send(commandLine + "\r");
  writeOutput(`ارسال به PowerShell داخلی: ${commandLine}`, "ok");
  $("requestInput").value = "";
  setStatus("Sent", "ok");
}

function showConfirm() { $("confirmText").textContent = state.currentPlan.explanation_fa || "این عملیات نیازمند تأیید است."; $("confirmCommand").textContent = state.currentPlan.argv.join(" "); showModal("confirmModal"); }
function showModal(id) { $(id).classList.remove("hidden"); }
function hideModal(id) { $(id).classList.add("hidden"); }

function wireEvents() {
  $("parseBtn").addEventListener("click", parseRequest);
  $("runBtn").addEventListener("click", () => runCurrent(false));
  $("saveSettingsBtn").addEventListener("click", saveSettings);
  $("testLlmBtn").addEventListener("click", testLlm);
  $("makeKeyBtn").addEventListener("click", makeKeypair);
  $("refreshSyncBtn").addEventListener("click", refreshSync);
  $("syncBtn").addEventListener("click", refreshSync);
  $("settingsBtn").addEventListener("click", () => showModal("settingsModal"));
  $("commandsBtn").addEventListener("click", () => showModal("commandsModal"));
  $("closeSettings").addEventListener("click", () => hideModal("settingsModal"));
  $("closeCommands").addEventListener("click", () => hideModal("commandsModal"));
  $("closeSync").addEventListener("click", () => hideModal("syncModal"));
  $("cancelConfirm").addEventListener("click", () => hideModal("confirmModal"));
  $("acceptConfirm").addEventListener("click", async () => { hideModal("confirmModal"); await runCurrent(true); });
  $("requestInput").addEventListener("keydown", async (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      if (event.ctrlKey) await parseRequest();
      else await sendToLive();
    }
  });
}

window.addEventListener("DOMContentLoaded", () => { wireEvents(); setStatus("Waiting API", "warn"); writeOutput("در حال آماده‌سازی رابط برنامه..."); if (pyApi()) boot(); });
window.addEventListener("pywebviewready", boot);
