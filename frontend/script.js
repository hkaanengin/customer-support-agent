const chatEl = document.getElementById('chat');
const formEl = document.getElementById('composer');
const inputEl = document.getElementById('input');
const modelEl = document.getElementById('model');
const useDbEl = document.getElementById('use-db');
let models = [];
// Keep separate histories per model id
const modelIdToMessages = {};

function getMessages() {
  const id = modelEl.value;
  if (!modelIdToMessages[id]) modelIdToMessages[id] = [];
  return modelIdToMessages[id];
}

function render() {
  chatEl.innerHTML = '';
  const msgs = getMessages();
  for (const m of msgs) {
    const row = document.createElement('div');
    row.className = `msg ${m.role}`;
    const role = document.createElement('div');
    role.className = 'role';
    role.textContent = m.role;
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = m.content;
    row.appendChild(role);
    row.appendChild(bubble);
    chatEl.appendChild(row);
  }
  chatEl.scrollTop = chatEl.scrollHeight;
}

async function sendMessage(text) {
  const msgs = getMessages();
  const userMsg = { role: 'user', content: text };
  msgs.push(userMsg);
  render();
  inputEl.value = '';
  inputEl.disabled = true;
  // Show thinking placeholder
  const placeholder = { role: 'assistant', content: '…' };
  msgs.push(placeholder);
  render();

  try {
    const selected = models.find(m => m.id === modelEl.value) || { provider: 'ollama', id: 'llama3.2' };
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    const res = await fetch('http://127.0.0.1:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: selected.id,
        provider: selected.provider,
        messages: msgs,
        use_database: !!useDbEl?.checked,
      }),
      signal: controller.signal,
    });
    clearTimeout(timeout);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const assistantMsg = data.message || { role: 'assistant', content: '' };
    // Some servers return role separately; ensure shape
    if (!assistantMsg.role) assistantMsg.role = 'assistant';
    // Replace placeholder with real response
    const idx = msgs.indexOf(placeholder);
    if (idx !== -1) {
      msgs.splice(idx, 1, assistantMsg);
    } else {
      msgs.push(assistantMsg);
    }
  } catch (err) {
    // Replace placeholder with error
    const idx = msgs.indexOf(placeholder);
    const errMsg = { role: 'assistant', content: `Error: ${err.name === 'AbortError' ? 'Request timed out' : err.message}` };
    if (idx !== -1) {
      msgs.splice(idx, 1, errMsg);
    } else {
      msgs.push(errMsg);
    }
  } finally {
    inputEl.disabled = false;
    render();
    inputEl.focus();
  }
}

formEl.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = inputEl.value.trim();
  if (!text) return;
  sendMessage(text);
});

// Submit on Enter (Shift+Enter inserts newline)
inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    const text = inputEl.value.trim();
    if (!text) return;
    sendMessage(text);
  }
});

async function loadModels() {
  try {
    const res = await fetch('http://127.0.0.1:8000/models');
    const data = await res.json();
    models = data.models || [];
    modelEl.innerHTML = '';
    for (const m of models) {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = m.label || m.id;
      modelEl.appendChild(opt);
    }
    // default to first
    if (models.length > 0) {
      modelEl.value = models[0].id;
      // initialize an empty history for default model
      if (!modelIdToMessages[models[0].id]) modelIdToMessages[models[0].id] = [];
    }
  } catch (e) {
    // fallback if backend not available
    models = [
      { provider: 'ollama', id: 'llama3.2', label: 'Llama 3.2 (Ollama)' },
      { provider: 'gemini', id: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash' },
    ];
    for (const m of models) {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = m.label;
      modelEl.appendChild(opt);
    }
    modelEl.value = 'llama3.2';
    modelIdToMessages['llama3.2'] = modelIdToMessages['llama3.2'] || [];
  }
}

// When changing model, show that model's history (separate per model)
modelEl.addEventListener('change', () => {
  // Ensure a history exists for the newly selected model
  getMessages();
  render();
  inputEl.focus();
});

loadModels().then(render);


