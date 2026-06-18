const state = {
  term: null,
  fit: null,
  ready: false,
  poller: null,
};

const $ = (id) => document.getElementById(id);

function api() {
  return window.pywebview && window.pywebview.api ? window.pywebview.api : null;
}

function setStatus(text) {
  $("status").textContent = text;
}

function write(text) {
  if (state.term) state.term.write(String(text || ""));
}

function initTerminal() {
  if (typeof Terminal === "undefined") {
    $("terminal").textContent = "xterm.js لود نشد. اینترنت/CDN را بررسی کن.";
    setStatus("XTerm Error");
    return;
  }

  state.term = new Terminal({
    cursorBlink: true,
    convertEol: false,
    fontFamily: "Cascadia Mono, Consolas, monospace",
    fontSize: 14,
    scrollback: 8000,
    theme: {
      background: "#0c0c0c",
      foreground: "#f2f2f2",
      cursor: "#ffffff",
      selectionBackground: "#264f78",
    },
  });

  if (window.FitAddon) {
    state.fit = new FitAddon.FitAddon();
    state.term.loadAddon(state.fit);
  }

  state.term.open($("terminal"));
  fitTerminal();

  state.term.onData(async (data) => {
    const backend = api();
    if (backend && state.ready) await backend.write(data);
  });

  window.addEventListener("resize", fitTerminal);
}

async function fitTerminal() {
  if (!state.term) return;
  try {
    if (state.fit) state.fit.fit();
    const backend = api();
    if (backend && state.term.cols && state.term.rows) {
      await backend.resize(state.term.cols, state.term.rows);
    }
  } catch (_) {}
}

async function start() {
  const backend = api();
  if (!backend) {
    setStatus("Waiting API");
    return;
  }

  setStatus("Starting");
  const result = await backend.start("");
  if (!result.ok) {
    write(`\r\n${result.message || "PowerShell start failed"}\r\n${result.technical || ""}\r\n`);
    setStatus("Error");
    return;
  }

  state.ready = true;
  setStatus("Ready");
  await fitTerminal();
  if (state.poller) clearInterval(state.poller);
  state.poller = setInterval(readLoop, 40);
  state.term.focus();
}

async function readLoop() {
  const backend = api();
  if (!backend || !state.ready) return;
  try {
    const result = await backend.read();
    if (result.ok && result.output) write(result.output);
  } catch (_) {}
}

function getText() {
  if (!state.term?.buffer?.active) return "";
  const buffer = state.term.buffer.active;
  const lines = [];
  for (let i = 0; i < buffer.length; i += 1) {
    const line = buffer.getLine(i);
    if (line) lines.push(line.translateToString(true));
  }
  return lines.join("\n").trimEnd();
}

async function copyAll() {
  const text = getText();
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    setStatus("Copied");
    setTimeout(() => setStatus("Ready"), 900);
  } catch (_) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
    setStatus("Copied");
    setTimeout(() => setStatus("Ready"), 900);
  } finally {
    state.term.focus();
  }
}

async function restart() {
  const backend = api();
  if (backend) await backend.stop();
  state.ready = false;
  if (state.term) state.term.clear();
  await start();
}

function wire() {
  $("copyBtn").addEventListener("click", copyAll);
  $("restartBtn").addEventListener("click", restart);
}

window.addEventListener("DOMContentLoaded", () => {
  wire();
  initTerminal();
  if (api()) start();
});

window.addEventListener("pywebviewready", start);
