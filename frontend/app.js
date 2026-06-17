const state = {
  settings: null,
  commands: [],
  currentPlan: null,
  currentIntent: null,
  apiReady: false,
};

const $ = (id) => document.getElementById(id);

function writeOutput(text, mode = "info") {
  const output = $("output");
  const prefix = mode === "error" ? "[ERROR]" : mode === "ok" ? "[OK]" : mode === "cmd" ? "PS >" : "[INFO]";
  output.textContent += `${prefix} ${text}\n`;
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
    $("planBox").textContent = "هنوز دستوری تشخیص داده نشده است.";
    $("runBtn").disabled = true;
    return;
  }
  $("cwdLabel").textContent = plan.project_path || ".";
  $("planBox").innerHTML = `
    <strong>${escapeHtml(plan.title_fa)}</strong>
    <span> · ریسک: ${escapeHtml(plan.risk)}</span>
    <code dir="ltr">${escapeHtml(preview)}</code>
    <span>${escapeHtml(plan.explanation_fa || "")}</span>
  `;
  $("runBtn").disabled = false;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
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
    } else {
      writeOutput("FaCoderTerminal آماده است.", "ok");
      writeOutput("Enter برای تشخیص فارسی؛ هدف نهایی: ترمینال زنده داخلی + لایه هوشمند.");
      writeOutput("برای تنظیم Local/GitHub/Server دکمه تنظیمات را بزن.");
      setStatus("Ready", "ok");
      $("requestInput").focus();
    }
  } catch (error) {
    writeOutput(`خطای شروع برنامه: ${error}`, "error");
    setStatus("Boot Error", "error");
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
    github: {
      ...(previous.github || {}),
      repo_url: $("githubRepoUrl").value.trim(),
      default_branch: $("githubBranch").value.trim() || "main",
      use_gh_cli: true,
    },
    server: {
      ...(previous.server || {}),
      name: $("serverName").value.trim() || "production",
      host: $("serverHost").value.trim(),
      port: Number($("serverPort").value.trim() || 22),
      username: $("serverUser").value.trim(),
      project_path: $("serverProjectPath").value.trim(),
      key_path: $("serverKeyPath").value.trim(),
      auth_note: "password is not stored by MVP",
    },
    llm: {
      ...(previous.llm || {}),
      provider_type: "openai_compatible",
      base_url: $("baseUrl").value.trim(),
      api_key: $("apiKey").value.trim(),
      model: $("modelName").value.trim(),
      temperature: 0,
      enabled: $("llmEnabled").checked,
    },
  };
}

function renderCommands(commands) {
  const box = $("commandsList");
  box.innerHTML = "";
  commands.forEach((command) => {
    const item = document.createElement("button");
    item.className = "command-item";
    item.innerHTML = `
      <strong>${escapeHtml(command.title_fa)}</strong>
      <span>${escapeHtml(command.id)} · ${escapeHtml(command.risk)}</span>
    `;
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
  setStatus("Saving", "warn");
  const payload = collectSettings();
  const result = await api.save_settings(payload);
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
  setStatus("Testing LLM", "warn");
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
  writeOutput("وضعیت هماهنگی Local/GitHub/Server بررسی شد.", result.ok ? "ok" : "error");
}

async function parseRequest() {
  const api = pyApi();
  if (!api) {
    writeOutput("API برنامه هنوز آماده نیست.", "error");
    return;
  }

  const text = $("requestInput").value.trim();
  const projectPath = $("projectPath").value.trim();
  if (!text) {
    writeOutput("دستور خالی است.", "error");
    return;
  }
  writeOutput(text, "cmd");
  setStatus("Parsing", "warn");
  setPlan(null);
  const result = await api.parse_request(text, projectPath);
  if (!result.ok) {
    writeOutput(result.message_fa || "تشخیص درخواست ناموفق بود.", "error");
    setStatus("Parse Error", "error");
    return;
  }
  setPlan(result.plan, result.command_preview, result.intent);
  writeOutput(`تشخیص: ${result.plan.command_id} (${result.intent.source})`, "ok");
  setStatus("Parsed", "ok");
}

async function runCurrent(confirmed = false) {
  const api = pyApi();
  if (!api || !state.currentPlan) return;
  if (state.currentPlan.requires_confirmation && !confirmed) {
    showConfirm();
    return;
  }
  setStatus("Running", "warn");
  const result = await api.run_command(
    state.currentPlan.command_id,
    state.currentIntent?.args || {},
    $("projectPath").value.trim(),
    confirmed,
    $("requestInput").value.trim()
  );
  if (!result.ok && !result.result) {
    writeOutput(result.message_fa || "اجرا ناموفق بود.", "error");
    setStatus("Run Error", "error");
    return;
  }
  const run = result.result;
  writeOutput(run.message_fa, run.ok ? "ok" : "error");
  if (run.stdout) writeOutput(run.stdout, run.ok ? "ok" : "info");
  if (run.stderr) writeOutput(run.stderr, "error");
  setStatus(run.ok ? "Done" : "Failed", run.ok ? "ok" : "error");
}

function showConfirm() {
  $("confirmText").textContent = state.currentPlan.explanation_fa || "این عملیات نیازمند تأیید است.";
  $("confirmCommand").textContent = state.currentPlan.argv.join(" ");
  showModal("confirmModal");
}

function showModal(id) {
  $(id).classList.remove("hidden");
}

function hideModal(id) {
  $(id).classList.add("hidden");
}

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
  $("acceptConfirm").addEventListener("click", async () => {
    hideModal("confirmModal");
    await runCurrent(true);
  });
  $("requestInput").addEventListener("keydown", async (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      if (event.ctrlKey) {
        await runCurrent(false);
      } else {
        await parseRequest();
      }
    }
  });
}

window.addEventListener("DOMContentLoaded", () => {
  wireEvents();
  setStatus("Waiting API", "warn");
  writeOutput("در حال آماده‌سازی رابط برنامه...");
  if (pyApi()) boot();
});

window.addEventListener("pywebviewready", boot);
