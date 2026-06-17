const state = {
  settings: null,
  commands: [],
  currentPlan: null,
  currentIntent: null,
};

const $ = (id) => document.getElementById(id);

function writeOutput(text, mode = "info") {
  const output = $("output");
  const prefix = mode === "error" ? "[ERROR]" : mode === "ok" ? "[OK]" : "[INFO]";
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
    <strong>${escapeHtml(plan.title_fa)}</strong><br />
    <span>${escapeHtml(plan.description_fa)}</span><br />
    <span>ریسک: ${escapeHtml(plan.risk)}</span><br />
    <code dir="ltr">${escapeHtml(preview)}</code><br />
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

async function boot() {
  setStatus("Loading", "warn");
  try {
    const data = await window.pywebview.api.get_bootstrap();
    state.settings = data.settings;
    state.commands = data.commands || [];
    hydrateSettings(data.settings);
    renderCommands(state.commands);
    if (!data.ok) {
      writeOutput(data.catalog_error || "خطای catalog", "error");
      setStatus("Catalog Error", "error");
    } else {
      writeOutput("FaCoderTerminal آماده است.", "ok");
      writeOutput("یک درخواست فارسی وارد کنید یا یکی از دستورهای شناخته‌شده را انتخاب کنید.");
      setStatus("Ready", "ok");
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
}

function collectSettings() {
  const previous = state.settings || {};
  return {
    ...previous,
    default_project_path: $("projectPath").value.trim(),
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
      await parseRequest();
    });
    box.appendChild(item);
  });
}

async function saveSettings() {
  setStatus("Saving", "warn");
  const payload = collectSettings();
  const result = await window.pywebview.api.save_settings(payload);
  if (result.ok) {
    state.settings = result.settings;
    hydrateSettings(result.settings);
    writeOutput("تنظیمات ذخیره شد.", "ok");
    setStatus("Saved", "ok");
  }
}

async function testLlm() {
  await saveSettings();
  setStatus("Testing LLM", "warn");
  const result = await window.pywebview.api.test_llm();
  writeOutput(result.message_fa, result.ok ? "ok" : "error");
  setStatus(result.ok ? "LLM OK" : "LLM Error", result.ok ? "ok" : "error");
}

async function parseRequest() {
  const text = $("requestInput").value.trim();
  const projectPath = $("projectPath").value.trim();
  if (!text) {
    writeOutput("درخواست فارسی خالی است.", "error");
    return;
  }
  setStatus("Parsing", "warn");
  setPlan(null);
  const result = await window.pywebview.api.parse_request(text, projectPath);
  if (!result.ok) {
    writeOutput(result.message_fa || "تشخیص درخواست ناموفق بود.", "error");
    setStatus("Parse Error", "error");
    return;
  }
  setPlan(result.plan, result.command_preview, result.intent);
  writeOutput(`تشخیص داده شد: ${result.plan.command_id} (${result.intent.source})`, "ok");
  setStatus("Parsed", "ok");
}

async function runCurrent(confirmed = false) {
  if (!state.currentPlan) return;
  if (state.currentPlan.requires_confirmation && !confirmed) {
    showConfirm();
    return;
  }
  setStatus("Running", "warn");
  const result = await window.pywebview.api.run_command(
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
  $("confirmModal").classList.remove("hidden");
}

function hideConfirm() {
  $("confirmModal").classList.add("hidden");
}

window.addEventListener("DOMContentLoaded", () => {
  $("parseBtn").addEventListener("click", parseRequest);
  $("runBtn").addEventListener("click", () => runCurrent(false));
  $("saveSettingsBtn").addEventListener("click", saveSettings);
  $("testLlmBtn").addEventListener("click", testLlm);
  $("cancelConfirm").addEventListener("click", hideConfirm);
  $("acceptConfirm").addEventListener("click", async () => {
    hideConfirm();
    await runCurrent(true);
  });
  $("requestInput").addEventListener("keydown", async (event) => {
    if (event.ctrlKey && event.key === "Enter") {
      await parseRequest();
    }
  });
  boot();
});
