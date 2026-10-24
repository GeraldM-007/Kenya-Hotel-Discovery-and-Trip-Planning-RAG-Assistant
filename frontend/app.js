/* Travel Africa — frontend for the Kenya RAG assistant.
 *
 * Backend contract (see INTEGRATION.md):
 *   POST {API_BASE}/api/ask   { "question": "...", "n_results": 5 }
 *   →  200 { "answer": "...", "sources": [{ reference, destination, section, source_url, distance }] }
 */

// ───────── Config ─────────
// Same-origin by default (server.py serves this folder AND the API).
// If the API runs elsewhere, set it before this script loads, e.g.
//   <script>window.TRAVEL_AFRICA_API = "http://localhost:8000";</script>
const API_BASE = (window.TRAVEL_AFRICA_API || "").replace(/\/$/, "");
const ASK_URL = `${API_BASE}/api/ask`;
const N_RESULTS = 5;
const REQUEST_TIMEOUT_MS = 90_000;

// ───────── Elements ─────────
const $ = (s, r = document) => r.querySelector(s);
const app = $("#app");
const form = $("#composer");
const input = $("#question");
const sendBtn = $("#sendBtn");
const thread = $("#thread");
const micBtn = $("#micBtn");
const toastEl = $("#toast");

const LANDING_PLACEHOLDER = input.placeholder;
let busy = false;

// ───────── Helpers ─────────
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : null);

function toast(msg) {
  toastEl.textContent = msg;
  toastEl.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (toastEl.hidden = true), 2600);
}

function autosize() {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 220) + "px";
}

// ───────── Minimal, safe Markdown → HTML (LLM answers) ─────────
function inline(text, sources) {
  let s = esc(text);
  const stash = [];
  const keep = (html) => `\u0000${stash.push(html) - 1}\u0000`;

  s = s.replace(/`([^`]+)`/g, (_, c) => keep(`<code>${c}</code>`));
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, t, u) => keep(`<a href="${u}" target="_blank" rel="noopener noreferrer">${t}</a>`));
  // [1] or [1, 2] → numbered citation chips that link to the source list
  s = s.replace(/\[(\d+(?:\s*,\s*\d+)*)\]/g, (_, nums) =>
    keep(nums.split(",").map((n) => {
      n = n.trim();
      const src = sources[Number(n) - 1];
      const href = src ? `#src-${n}` : null;
      return href ? `<a class="cite" href="${href}" data-src="${n}">${n}</a>` : `<span class="cite dead">${n}</span>`;
    }).join("")));
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
  return s.replace(/\u0000(\d+)\u0000/g, (_, i) => stash[i]);
}

function markdown(md, sources) {
  const lines = md.replace(/\r\n?/g, "\n").split("\n");
  const out = [];
  let i = 0;
  const isTableSep = (l) => /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(l || "");
  const cells = (l) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());

  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }

    let m;
    if ((m = line.match(/^(#{1,4})\s+(.*)$/))) {
      const level = Math.min(m[1].length + 1, 4); // keep headings modest inside a bubble
      out.push(`<h${level}>${inline(m[2], sources)}</h${level}>`); i++; continue;
    }
    if (/^\s*([-*_])\1{2,}\s*$/.test(line)) { out.push("<hr>"); i++; continue; }

    if (line.includes("|") && isTableSep(lines[i + 1])) {
      const head = cells(line); i += 2;
      const rows = [];
      while (i < lines.length && lines[i].includes("|") && lines[i].trim()) rows.push(cells(lines[i++]));
      out.push(`<table><thead><tr>${head.map((h) => `<th>${inline(h, sources)}</th>`).join("")}</tr></thead><tbody>${
        rows.map((r) => `<tr>${r.map((c) => `<td>${inline(c, sources)}</td>`).join("")}</tr>`).join("")}</tbody></table>`);
      continue;
    }

    if (/^\s*([-*•])\s+/.test(line) || /^\s*\d+[.)]\s+/.test(line)) {
      const ordered = /^\s*\d+[.)]\s+/.test(line);
      const items = [];
      while (i < lines.length && (ordered ? /^\s*\d+[.)]\s+/ : /^\s*([-*•])\s+/).test(lines[i])) {
        let item = lines[i++].replace(ordered ? /^\s*\d+[.)]\s+/ : /^\s*([-*•])\s+/, "");
        while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*([-*•]|\d+[.)])\s+/.test(lines[i])) item += " " + lines[i++].trim();
        items.push(`<li>${inline(item, sources)}</li>`);
      }
      out.push(`<${ordered ? "ol" : "ul"}>${items.join("")}</${ordered ? "ol" : "ul"}>`);
      continue;
    }

    const para = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|\s*([-*•]|\d+[.)])\s+)/.test(lines[i]) && !(lines[i].includes("|") && isTableSep(lines[i + 1]))) para.push(lines[i++].trim());
    out.push(`<p>${inline(para.join(" "), sources)}</p>`);
  }
  return out.join("");
}

// ───────── Rendering ─────────
function enterChatMode() {
  if (app.classList.contains("chatting")) return;
  app.classList.add("chatting");
  thread.hidden = false;
  input.placeholder = "Ask a follow-up…";
}

function resetToLanding() {
  if (busy) return;
  app.classList.remove("chatting");
  thread.hidden = true;
  thread.innerHTML = "";
  input.value = "";
  input.placeholder = LANDING_PLACEHOLDER;
  autosize();
  window.scrollTo({ top: 0 });
}

function addUser(text) {
  const el = document.createElement("div");
  el.className = "msg user";
  el.innerHTML = `<div class="bubble-user">${esc(text)}</div>`;
  thread.append(el);
  scrollDown();
}

function addTyping() {
  const el = document.createElement("div");
  el.className = "msg bot";
  el.innerHTML = `<div class="bot-head"><span class="bot-dot">✦</span>Travel Africa</div><div class="typing" aria-label="Thinking"><i></i><i></i><i></i></div>`;
  thread.append(el);
  scrollDown();
  return el;
}

function renderAnswer(el, data) {
  const sources = Array.isArray(data.sources) ? data.sources : [];
  const answerHtml = markdown(String(data.answer ?? ""), sources);

  // De-duplicate sources by URL for the chip list, but keep the original numbering for citations.
  const chips = sources.map((s, idx) => {
    const n = idx + 1;
    const label = [s.destination, s.section].filter(Boolean).join(" — ") || `Source ${n}`;
    const url = safeUrl(s.source_url);
    const tag = url ? "a" : "span";
    const attrs = url ? ` href="${esc(url)}" target="_blank" rel="noopener noreferrer"` : "";
    return `<${tag} class="source" id="src-${n}"${attrs} title="${esc(label)}"><b>${n}</b><span>${esc(label)}</span></${tag}>`;
  }).join("");

  el.innerHTML = `
    <div class="bot-head"><span class="bot-dot">✦</span>Travel Africa</div>
    <div class="answer">${answerHtml || "<p>I couldn't find an answer to that.</p>"}</div>
    ${chips ? `<div class="sources"><div class="sources-title">Sources</div><div class="source-list">${chips}</div></div>` : ""}`;
  scrollDown();
}

function renderError(el, question, message) {
  el.innerHTML = `
    <div class="bot-head"><span class="bot-dot">✦</span>Travel Africa</div>
    <div class="error-box"><strong>Something went wrong.</strong><br>${esc(message)}<br><button type="button">Try again</button></div>`;
  $("button", el).addEventListener("click", () => { el.remove(); ask(question, { echo: false }); });
  scrollDown();
}

function scrollDown() {
  requestAnimationFrame(() => window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "smooth" }));
}

// ───────── Ask the backend ─────────
async function ask(question, { echo = true } = {}) {
  question = question.trim();
  if (!question || busy) return;

  busy = true;
  sendBtn.disabled = true;
  enterChatMode();
  if (echo) addUser(question);
  input.value = "";
  autosize();
  const slot = addTyping();

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT_MS);

  try {
    const res = await fetch(ASK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        question,
        n_results: N_RESULTS,
        // Selected in the header menus. The backend ignores these today; they're here for when it doesn't.
        currency: localStorage.getItem("ta.currency") || "KSh",
        language: localStorage.getItem("ta.language") || "EN",
      }),
      signal: ctrl.signal,
    });

    if (!res.ok) {
      let detail = `The server replied with ${res.status}.`;
      try { const j = await res.json(); if (j.detail) detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch {}
      throw new Error(detail);
    }
    renderAnswer(slot, await res.json());
  } catch (err) {
    const msg = err.name === "AbortError"
      ? "The assistant took too long to respond."
      : err instanceof TypeError
        ? `Couldn't reach the assistant at ${ASK_URL}. Is the backend running?`
        : err.message;
    renderError(slot, question, msg);
  } finally {
    clearTimeout(timer);
    busy = false;
    sendBtn.disabled = false;
    input.focus({ preventScroll: true });
  }
}

// ───────── Events ─────────
form.addEventListener("submit", (e) => {
  e.preventDefault();
  // As in the reference design, the sample prompt is shown as placeholder text; an empty send uses it.
  ask(input.value.trim() || (app.classList.contains("chatting") ? "" : LANDING_PLACEHOLDER));
});

input.addEventListener("input", autosize);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); form.requestSubmit(); }
});

$("#chips").addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (chip) ask(chip.dataset.prompt);
});

$("#logo").addEventListener("click", (e) => { e.preventDefault(); resetToLanding(); });

// Jump from a citation chip to its source card
thread.addEventListener("click", (e) => {
  const c = e.target.closest("a.cite");
  if (!c) return;
  e.preventDefault();
  const target = document.getElementById(`src-${c.dataset.src}`);
  if (target) { target.scrollIntoView({ behavior: "smooth", block: "center" }); target.animate([{ outline: "3px solid #c97f42" }, { outline: "3px solid transparent" }], { duration: 1200 }); }
});

$("#attachBtn").addEventListener("click", () => toast("Attachments aren't supported by the assistant yet."));

// Header menus (persisted; sent along with each request)
document.querySelectorAll(".menu").forEach((menu) => {
  const key = "ta." + menu.dataset.menu;
  const btn = $(".pill", menu), list = $(".menu-list", menu), label = $(".menu-label", menu);
  try { const saved = localStorage.getItem(key); if (saved) label.textContent = saved; } catch {}
  const close = () => { list.hidden = true; btn.setAttribute("aria-expanded", "false"); };
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    const open = list.hidden;
    document.querySelectorAll(".menu-list").forEach((l) => (l.hidden = true));
    list.hidden = !open;
    btn.setAttribute("aria-expanded", String(open));
  });
  list.addEventListener("click", (e) => {
    const li = e.target.closest("li");
    if (!li) return;
    label.textContent = li.dataset.value;
    try { localStorage.setItem(key, li.dataset.value); } catch {}
    close();
  });
  document.addEventListener("click", close);
});

// Voice dictation (browser Web Speech API; hidden if unsupported)
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SR) {
  let rec = null;
  micBtn.addEventListener("click", () => {
    if (rec) { rec.stop(); return; }
    rec = new SR();
    rec.lang = "en-KE";
    rec.interimResults = true;
    const base = input.value ? input.value.trimEnd() + " " : "";
    rec.onresult = (ev) => { input.value = base + Array.from(ev.results).map((r) => r[0].transcript).join(""); autosize(); };
    rec.onend = () => { rec = null; micBtn.classList.remove("listening"); };
    rec.onerror = () => toast("Couldn't access the microphone.");
    micBtn.classList.add("listening");
    rec.start();
  });
} else {
  micBtn.title = "Dictation isn't supported in this browser";
  micBtn.addEventListener("click", () => toast("Voice input isn't supported in this browser."));
}

$("#seeHow").addEventListener("click", (e) => { e.preventDefault(); $("#how").scrollIntoView({ behavior: "smooth" }); });

autosize();
