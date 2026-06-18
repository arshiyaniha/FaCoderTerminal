const state = {
  settings: null,
  commands: [],
  currentPlan: null,
  currentIntent: null,
  apiReady: false,
  liveReady: false,
  poller: null,
  term: null,
  fitAddon: null,
};

const $ = (id) => document.getElementById(id);

async function uiLog(level, area, message, data = {}) {
  try {
    const api = pyApi();
    if (api && api.temp_log) await api.temp_log(level, area, String(message || ""), data || {});
  } catch (_) {}
}

function setUiMessage(text, mode = "info") {
  const box = $("planBox");
  if (!box) return;
  const prefix = mode === "error" ? "خطا: " : mode === "ok" ? "انجام شد: " : mode === "cmd" ? "FaCoder: " : "";
  box.textContent = `${prefix}${text}`;
}

function terminalWrite(text) {
  if (state.term) state.term.write(String(text ?? ""));
}

function setStatus(text, type = "") {
  const pill = $("statusPill");
  if (!pill) return;
  pill.textContent = text;
  pill.className = `status-pill ${type}`.trim();
}

function setPlan(plan, preview, intent) {
  state.currentPlan = plan;
  state.currentIntent = intent;
  if (!plan) {
    setUiMessage("Enter برای اجرا هوشمند؛ Ctrl+Enter فقط تشخیص؛ تایپ مستقیم داخل ترمینال برای PowerShell.");
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

function quotePowerShellArg(arg) {
  const value = String(arg ?? "");
  if (value === "") return "''";
  if (/^[A-Za-z0-9_@%+=:,./\\-]+$/.test(value)) return value;
  return "'" + value.replaceAll("'", "''") + "'";
}

function argvToPowerShell(argv) {
  return (argv || []).map(quotePowerShellArg).join(" ");
}

function pyApi() {
  return window.pywebview && window.pywebview.api ? window.pywebview.api : null;
}

function initTerminal() {
  if (state.term) return;
  if (typeof Terminal === "undefined") {
    setStatus("XTerm Missing", "error");
    uiLog("error", "ui.xterm", "Terminal global is undefined. xterm.js probably failed to load.", {
      scripts: Array.from(document.scripts).map((script) => script.src || "inline"),
      online: navigator.onLine,
    });
    const fallback = $("terminal");
    if (fallback) fallback.textContent = "xterm.js لود نشد. احتمالاً CDN در دسترس نیست. لاگ را بررسی کنید.";
    throw new Error("Terminal global is undefined");
  }

  state.term = new Terminal({
    cursorBlink: true,
    convertEol: false,
    fontFamily: "Cascadia Mono, Consolas, monospace",
    fontSize: 13,
    theme: {
      background: "#0c0c0c",
      foreground: "#e6e6e6",
      cursor: "#ffffff",
      selectionBackground: "#264f78",
      black: "#000000",
      red: "#cd3131",
      green: "#0dbc79",
      yellow: "#e5e510",
      blue: "#2472c8",
      magenta: "#bc3fbc",
      cyan: "#11a8cd",
      white: "#e5e5e5",
    },
    scrollback: 5000,
  });

  if (window.FitAddon) {
    state.fitAddon = new FitAddon.FitAddon();
    state.term.loadAddon(state.fitAddon);
  } else {
    uiLog("warn", "ui.xterm", "FitAddon missing. Terminal will work without auto-fit.");
  }

  state.term.open($("terminal"));
  fitTerminal();
  state.term.onData(async (data) => {
    const api = pyApi();
    if (api && state.liveReady) await api.live_send(data);
  });
  window.addEventListener("resize", fitTerminal);
  uiLog("info", "ui.xterm", "xterm initialized");
}

async function fitTerminal() {
  if (!state.term) return;
  try {
    if (state.fitAddon) state.fitAddon.fit();
    const api = pyApi();
    if (api && state.term.cols && state.term.rows) await api.live_resize(state.term.cols, state.term.rows);
  } catch (error) {
    uiLog("error", "ui.fit", error?.message || String(error), { stack: error?.stack });
  }
}

async function boot() {
  const api = pyApi();
  if (!api) {
    setStatus("Waiting API", "warn");
    return;
  }
  await uiLog("info", "ui.boot", "boot started");
  try {
    initTerminal();
    state.apiReady = true;
    setStatus("Loading", "warn");
    const data = await api.get_bootstrap();
    await uiLog("info", "ui.boot", "bootstrap received", { ok: data.ok, log_path: data.log_path });
    state.settings = data.settings;
    state.commands = data.commands || [];
    hydrateSettings(data.settings);
    renderCommands(state.commands);
    if (!data.ok) {
      setUiMessage(data.catalog_error || "خطای catalog", "error");
      setStatus("Catalog Error", "error");
      return;
    }
    await startLive();
    setPlan(null);
    setUiMessage("ترمینال زنده آماده است. Enter در نوار FaCoder یعنی تشخیص و اجرای خودکار.", "ok");
    setStatus("Ready", "ok");
    state.term.focus();
  } catch (error) {
    await uiLog("error", "ui.boot", error?.message || String(error), { stack: error?.stack });
    setUiMessage(`خطای شروع برنامه: ${error}`, "error");
    setStatus("Boot Error", "error");
  }
}

async function startLive() {
  const api = pyApi();
  await uiLog("info", "ui.live", "starting live session", { projectPath: $("projectPath")?.value?.trim() || "" });
  const result = await api.live_start($("projectPath").value.trim());
  await uiLog(result.ok ? "info" : "error", "ui.live", "live_start result", result);
  if (!result.ok) {
    setUiMessage(result.message_fa || "راه‌اندازی PowerShell داخلی ناموفق بود.", "error");
    setStatus("PTY Error", "error");
    return;
  }
  state.liveReady = true;
  if (result.cwd) $("cwdLabel").textContent = result.cwd;
  await fitTerminal();
  if (state.poller) clearInterval(state.poller);
  state.poller = setInterval(pollLive, 60);
}

async function pollLive() {
  const api = pyApi();
  if (!api || !state.liveReady) return;
  try {
    const result = await api.live_read();
    if (result.ok && result.output) terminalWrite(result.output);
  } catch (error) {
    uiLog("error", "ui.live_read", error?.message || String(error), { stack: error?.stack });
  }
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
      await smartRunRequest();
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
    setUiMessage("تنظیمات ذخیره شد.", "ok");
    setStatus("Saved", "ok");
    hideModal("settingsModal");
  } else {
    setUiMessage(result.message_fa || "ذخیره تنظیمات ناموفق بود.", "error");
  }
}

async function testLlm() {
  const api = pyApi();
  if (!api) return;
  await saveSettings();
  const result = await api.test_llm();
  setUiMessage(result.message_fa, result.ok ? "ok" : "error");
  setStatus(result.ok ? "LLM OK" : "LLM Error", result.ok ? "ok" : "error");
}

async function makeKeypair() {
  const api = pyApi();
  if (!api) return;
  await saveSettings();
  const result = await api.make_keypair();
  setUiMessage(result.message_fa || JSON.stringify(result), result.ok ? "ok" : "error");
  if (result.key_path) $("serverKeyPath").value = result.key_path;
}

async function refreshSync() {
  const api = pyApi();
  if (!api) return;
  await saveSettings();
  showModal("syncModal");
  $("syncOutput").textContent = "در حال بررسی هماهنگی...";
  const result = await api.sync_health();
  $("syncOutput").textContent = JSON.stringify(result, null, 2);
  setUiMessage("هماهنگی Local/GitHub/Server بررسی شد.", result.ok ? "ok" : "error");
}

async function parseRequest(options = {}) {
  const api = pyApi();
  if (!api) return null;
  const text = $("requestInput").value.trim();
  if (!text) return null;
  setUiMessage(text, "cmd");
  setStatus(options.autoRun ? "Smart Run" : "Parsing", "warn");
  setPlan(null);
  const result = await api.parse_request(text, $("projectPath").value.trim());
  if (!result.ok) {
    setUiMessage(result.message_fa || "تشخیص ناموفق بود.", "error");
    setStatus("Parse Error", "error");
    return null;
  }
  setPlan(result.plan, result.command_preview, result.intent);
  setStatus("Parsed", "ok");
  if (options.autoRun) await runCurrent(false);
  return result;
}

async function smartRunRequest() {
  await parseRequest({ autoRun: true });
}

async function sendToLive(text) {
  const api = pyApi();
  if (!api || !state.liveReady) return;
  await api.live_send(text);
}

async function runCurrent(confirmed = false) {
  if (!state.currentPlan) return;
  if (state.currentPlan.requires_confirmation && !confirmed) {
    showConfirm();
    return;
  }
  const commandLine = argvToPowerShell(state.currentPlan.argv);
  await sendToLive(commandLine + "\r");
  setUiMessage(`به ترمینال ارسال شد: ${commandLine}`, "ok");
  $("requestInput").value = "";
  setStatus("Sent", "ok");
  state.term.focus();
}

function getTerminalLines() {
  if (!state.term?.buffer?.active) return [];
  const buffer = state.term.buffer.active;
  const lines = [];
  for (let i = 0; i < buffer.length; i += 1) {
    const line = buffer.getLine(i);
    if (!line) continue;
    lines.push(line.translateToString(true));
  }
  return lines;
}

function getTerminalText(scope) {
  const lines = getTerminalLines();
  if (scope === "last50") return lines.slice(-50).join("\n").trimEnd();
  if (scope === "last") {
    for (let i = lines.length - 1; i >= 0; i -= 1) {
      const value = lines[i].trimEnd();
      if (value.trim()) return value;
    }
    return "";
  }
  return lines.join("\n").trimEnd();
}

async function copyText(text) {
  const value = String(text || "");
  if (!value.trim()) {
    setUiMessage("چیزی برای کپی وجود ندارد.", "error");
    return false;
  }
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
    } else {
      const textarea = document.createElement("textarea");
      textarea.value = value;
      textarea.setAttribute("readonly", "readonly");
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
    setUiMessage("خروجی ترمینال کپی شد.", "ok");
    setStatus("Copied", "ok");
    return true;
  } catch (error) {
    await uiLog("error", "ui.copy", error?.message || String(error), { stack: error?.stack });
    setUiMessage(`کپی ناموفق بود: ${error}`, "error");
    setStatus("Copy Error", "error");
    return false;
  } finally {
    if (state.term) state.term.focus();
  }
}

async function copyTerminal(scope) {
  const text = getTerminalText(scope);
  await copyText(text);
}

function showConfirm() {
  $("confirmText").textContent = state.currentPlan.explanation_fa || "این عملیات نیازمند تأیید است.";
  $("confirmCommand").textContent = argvToPowerShell(state.currentPlan.argv);
  showModal("confirmModal");
}
function showModal(id) { $(id).classList.remove("hidden"); }
function hideModal(id) { $(id).classList.add("hidden"); if (state.term) state.term.focus(); }

function wireEvents() {
  $("parseBtn").addEventListener("click", smartRunRequest);
  $("runBtn").addEventListener("click", () => runCurrent(false));
  $("saveSettingsBtn").addEventListener("click", saveSettings);
  $("testLlmBtn").addEventListener("click", testLlm);
  $("makeKeyBtn").addEventListener("click", makeKeypair);
  $("refreshSyncBtn").addEventListener("click", refreshSync);
  $("syncBtn").addEventListener("click", refreshSync);
  $("copyAllBtn").addEventListener("click", () => copyTerminal("all"));
  $("copyLast50Btn").addEventListener("click", () => copyTerminal("last50"));
  $("copyLastMsgBtn").addEventListener("click", () => copyTerminal("last"));
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
      if (event.ctrlKey) await parseRequest({ autoRun: false });
      else await smartRunRequest();
    }
  });
}

window.addEventListener("error", (event) => {
  uiLog("error", "ui.window_error", event.message, { filename: event.filename, lineno: event.lineno, colno: event.colno, stack: event.error?.stack });
});
window.addEventListener("unhandledrejection", (event) => {
  uiLog("error", "ui.unhandled_promise", event.reason?.message || String(event.reason), { stack: event.reason?.stack });
});
window.addEventListener("DOMContentLoaded", () => {
  wireEvents();
  setStatus("Waiting API", "warn");
  try {
    initTerminal();
    setUiMessage("در حال آماده‌سازی ترمینال واقعی...");
  } catch (error) {
    setStatus("Boot Error", "error");
  }
  if (pyApi()) boot();
});
window.addEventListener("pywebviewready", boot);
