/* ════════════════════════════════════════════════════════════════
   FullTrack Manager — Frontend JavaScript
   ════════════════════════════════════════════════════════════════ */

'use strict';

// ─── State ───────────────────────────────────────────────────────────────────
const state = {
  currentPage: 'dashboard',
  serials: [],
  stats: { total: 0, pendente: 0, bloqueado: 0, erro: 0, nao_encontrado: 0, processando: 0 },
  processing: { running: false, current: null, total: 0, processed: 0, errors: 0 },
  logs: [],
  lastLogId: -1,
  logFilter: '',
  statusFilter: '',
  selectedFile: null,
  pollInterval: null,
  logPollInterval: null,
  serialPage: 1,
  serialPageSize: 50,
};

// ─── API Layer ────────────────────────────────────────────────────────────────
const api = {
  async _fetch(url, options = {}) {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    const json = await res.json();
    if (!json.success && options.throw !== false) {
      throw new Error(json.error || 'Erro desconhecido');
    }
    return json;
  },
  get: (url) => api._fetch(url),
  post: (url, body) => api._fetch(url, { method: 'POST', body: JSON.stringify(body || {}) }),
  delete: (url) => api._fetch(url, { method: 'DELETE' }),

  serials: {
    list: (status) => api.get(`/api/serials${status ? `?status=${status}` : ''}`),
    add: (numeros) => api.post('/api/serials', { numeros }),
    upload: async (file) => {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch('/api/serials/upload', { method: 'POST', body: fd });
      return res.json();
    },
    delete: (id) => api.delete(`/api/serials/${id}`),
    clear: (status) => api.delete(`/api/serials/clear${status ? `?status=${status}` : ''}`),
    block: (id) => api.post(`/api/serials/${id}/block`),
    reset: (id) => api.post(`/api/serials/${id}/reset`),
  },
  process: {
    start: (status = 'pendente') => api.post('/api/process/start', { status }),
    status: () => api.get('/api/process/status'),
  },
  logs: {
    get: (limit, afterId) => api.get(`/api/logs?limit=${limit}${afterId !== undefined ? `&after_id=${afterId}` : ''}`),
    clear: () => api.delete('/api/logs/clear'),
  },
  config: {
    get: () => api.get('/api/config'),
    save: (data) => api.post('/api/config', data),
  },
  stats: () => api.get('/api/stats'),
};

// ─── Navigation ───────────────────────────────────────────────────────────────
function navigate(page) {
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.page').forEach(el => el.classList.remove('active'));

  const navEl = document.getElementById(`nav-${page}`);
  const pageEl = document.getElementById(`page-${page}`);
  if (navEl) navEl.classList.add('active');
  if (pageEl) pageEl.classList.add('active');

  state.currentPage = page;

  const titles = { dashboard: 'Dashboard', configuracoes: 'Configurações', logs: 'Logs de Execução' };
  document.getElementById('page-title').textContent = titles[page] || page;

  if (page === 'configuracoes') loadConfig();
  if (page === 'logs') { renderLogs(); startLogPolling(); } else stopLogPolling();
}

document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', (e) => {
    e.preventDefault();
    navigate(el.dataset.page);
  });
});

// ─── Stats & Polling ──────────────────────────────────────────────────────────
async function fetchStats() {
  try {
    const { data } = await api.stats();
    state.stats = data;
    document.getElementById('stat-total').textContent = data.total;
    document.getElementById('stat-pendente').textContent = data.pendente;
    document.getElementById('stat-bloqueado').textContent = data.bloqueado;
    document.getElementById('stat-erro').textContent = data.erro + (data.nao_encontrado || 0);
  } catch (_) {}
}

async function fetchProcessStatus() {
  try {
    const { data } = await api.process.status();
    state.processing = data;
    updateProcessUI(data);
  } catch (_) {}
}

function updateProcessUI(p) {
  const dot = document.getElementById('indicator-dot');
  const label = document.getElementById('indicator-label');
  const sub = document.getElementById('indicator-sub');
  const progContainer = document.getElementById('progress-container');

  if (p.running) {
    dot.className = 'indicator-dot running';
    label.textContent = 'Processando...';
    sub.textContent = p.current || '';

    const pct = p.total > 0 ? Math.round((p.processed / p.total) * 100) : 0;
    document.getElementById('progress-bar-fill').style.width = pct + '%';
    document.getElementById('progress-count').textContent = `${p.processed}/${p.total}`;
    document.getElementById('progress-current').textContent = p.current ? `Serial atual: ${p.current}` : '';
    document.getElementById('progress-label').textContent = `Progresso: ${pct}%`;
    progContainer.style.display = 'flex';

    document.getElementById('btn-process-all').disabled = true;
  } else {
    dot.className = 'indicator-dot idle';
    label.textContent = 'Aguardando';
    sub.textContent = '';
    progContainer.style.display = 'none';
    document.getElementById('btn-process-all').disabled = false;

    if (state.currentPage === 'dashboard') {
      refreshSerials();
      fetchStats();
    }
  }
}

async function startPolling() {
  await Promise.all([fetchStats(), fetchProcessStatus(), refreshSerials()]);
  state.pollInterval = setInterval(async () => {
    await fetchStats();
    await fetchProcessStatus();
    if (state.processing.running && state.currentPage === 'dashboard') {
      await refreshSerials();
    }
  }, 3000);
}

function stopLogPolling() {
  if (state.logPollInterval) {
    clearInterval(state.logPollInterval);
    state.logPollInterval = null;
  }
}

function startLogPolling() {
  stopLogPolling();
  fetchNewLogs();
  state.logPollInterval = setInterval(fetchNewLogs, 2000);
}

async function fetchNewLogs() {
  try {
    const res = await api.logs.get(200, state.lastLogId === -1 ? undefined : state.lastLogId);
    const newEntries = res.data || [];
    if (newEntries.length > 0) {
      // data comes back newest-first, reverse to append in order
      const ordered = [...newEntries].reverse();
      state.logs = [...state.logs, ...ordered];
      if (state.logs.length > 500) state.logs = state.logs.slice(-500);
      state.lastLogId = Math.max(...state.logs.map(l => l.id));
      if (state.currentPage === 'logs') renderLogs();

      // badge on nav
      const badge = document.getElementById('log-badge');
      if (state.currentPage !== 'logs') {
        badge.textContent = newEntries.length;
        badge.style.display = 'inline-flex';
      } else {
        badge.style.display = 'none';
      }
    }
  } catch (_) {}
}

// ─── Serials Table ────────────────────────────────────────────────────────────
async function refreshSerials() {
  try {
    const { data } = await api.serials.list(state.statusFilter || undefined);
    state.serials = data;
    state.serialPage = 1;
    renderSerials();
  } catch (e) {
    toast('Erro ao carregar seriais: ' + e.message, 'error');
  }
}

function applyFilter() {
  state.statusFilter = document.getElementById('filter-status').value;
  state.serialPage = 1;
  refreshSerials();
}

function renderSerials() {
  const tbody = document.getElementById('serials-tbody');
  if (!state.serials.length) {
    tbody.innerHTML = `
      <tr class="empty-row"><td colspan="8">
        <div class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
            <line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
          <p>Nenhum serial encontrado</p>
          <small>Clique em "Adicionar Seriais" ou importe uma planilha</small>
        </div>
      </td></tr>`;
    renderPagination(0, 1);
    return;
  }

  const total = state.serials.length;
  const pageSize = state.serialPageSize;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (state.serialPage > totalPages) state.serialPage = totalPages;
  const start = (state.serialPage - 1) * pageSize;
  const currentPageSerials = state.serials.slice(start, start + pageSize);

  tbody.innerHTML = currentPageSerials.map(s => `
    <tr data-id="${s.id}">
      <td><span class="contract-cell" title="${escHtml(s.contrato || '')}">${escHtml(s.contrato || '—')}</span></td>
      <td><span class="serial-number">${escHtml(s.numero)}</span></td>
      <td><span class="client-cell" title="${escHtml(s.cliente || '')}">${escHtml(s.cliente || '—')}</span></td>
      <td><span class="note-cell" title="${escHtml(s.observacao || '')}">${escHtml(s.observacao || '—')}</span></td>
      <td>${renderBadge(s.status)}</td>
      <td><span class="msg-cell" title="${escHtml(s.mensagem || '')}">${escHtml(s.mensagem || '—')}</span></td>
      <td><span class="date-cell">${formatDate(s.atualizado_em)}</span></td>
      <td class="actions-cell">
        ${s.status !== 'bloqueado' ? `
          <button class="btn-action block-btn" title="Bloquear agora" onclick="blockSerial(${s.id}, '${escHtml(s.numero)}')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
          </button>` : ''}
        ${s.status !== 'pendente' ? `
          <button class="btn-action reset-btn" title="Resetar para pendente" onclick="resetSerial(${s.id})">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
            </svg>
          </button>` : ''}
        <button class="btn-action delete-btn" title="Remover" onclick="deleteSerial(${s.id})">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/>
            <path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>
          </svg>
        </button>
      </td>
    </tr>`).join('');

  renderPagination(total, totalPages);
}

function renderPagination(total, totalPages) {
  const container = document.getElementById('pagination-bar');
  if (total <= state.serialPageSize) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = `
    <div class="pagination">
      <button class="btn btn-ghost btn-sm" onclick="goToSerialPage(1)" ${state.serialPage === 1 ? 'disabled' : ''}>Primeira</button>
      <button class="btn btn-ghost btn-sm" onclick="goToSerialPage(${Math.max(1, state.serialPage - 1)})" ${state.serialPage === 1 ? 'disabled' : ''}>Anterior</button>
      <span class="pagination-info">Página ${state.serialPage} de ${totalPages} · ${total} item(s)</span>
      <button class="btn btn-ghost btn-sm" onclick="goToSerialPage(${Math.min(totalPages, state.serialPage + 1)})" ${state.serialPage === totalPages ? 'disabled' : ''}>Próxima</button>
      <button class="btn btn-ghost btn-sm" onclick="goToSerialPage(${totalPages})" ${state.serialPage === totalPages ? 'disabled' : ''}>Última</button>
    </div>`;
}

function goToSerialPage(page) {
  state.serialPage = page;
  renderSerials();
}

function clearSerials() {
  const status = state.statusFilter || undefined;
  const message = status
    ? `Deseja limpar todos os seriais filtrados como '${state.statusFilter}'?`
    : 'Deseja limpar todos os seriais da lista?';

  if (!confirm(message)) return;
  api.serials.clear(status)
    .then(() => {
      state.serialPage = 1;
      refreshSerials();
      fetchStats();
      toast('Lista de seriais limpa', 'success');
    })
    .catch((e) => toast('Erro ao limpar seriais: ' + e.message, 'error'));
}

function renderBadge(status) {
  const labels = {
    pendente: 'Pendente',
    bloqueado: 'Bloqueado',
    erro: 'Erro',
    nao_encontrado: 'Não encontrado',
    processando: 'Processando',
  };
  return `<span class="badge badge-${status}">${labels[status] || status}</span>`;
}

// ─── Serial Actions ───────────────────────────────────────────────────────────
async function blockSerial(id, numero) {
  if (state.processing.running) {
    toast('Aguarde o processamento atual terminar.', 'warning');
    return;
  }
  try {
    await api.serials.block(id);
    toast(`🔒 Bloqueio iniciado para: ${numero}`, 'info');
    navigate('logs');
    startLogPolling();
  } catch (e) {
    toast('Erro: ' + e.message, 'error');
  }
}

async function resetSerial(id) {
  try {
    await api.serials.reset(id);
    toast('Serial resetado para pendente', 'success');
    await refreshSerials();
    await fetchStats();
  } catch (e) {
    toast('Erro: ' + e.message, 'error');
  }
}

async function deleteSerial(id) {
  try {
    await api.serials.delete(id);
    await refreshSerials();
    await fetchStats();
  } catch (e) {
    toast('Erro: ' + e.message, 'error');
  }
}

async function processAll() {
  if (state.processing.running) {
    toast('Já existe um processamento em andamento.', 'warning');
    return;
  }
  if (state.stats.pendente === 0) {
    toast('Nenhum serial pendente para processar.', 'warning');
    return;
  }
  try {
    const { queued } = await api.process.start('pendente');
    toast(`🚀 Processamento iniciado: ${queued} serial(is)`, 'success');
    navigate('logs');
    startLogPolling();
  } catch (e) {
    toast('Erro ao iniciar: ' + e.message, 'error');
  }
}

// ─── Add Modal ────────────────────────────────────────────────────────────────
function openAddModal() {
  document.getElementById('textarea-serials').value = '';
  openModal('modal-add');
}

async function submitAddSerials() {
  const text = document.getElementById('textarea-serials').value.trim();
  if (!text) { toast('Digite pelo menos um número de série.', 'warning'); return; }

  try {
    const { added, duplicates, total } = await api.serials.add(text);
    closeModal('modal-add');
    toast(`✅ ${added} serial(is) adicionado(s)${duplicates ? ` · ${duplicates} duplicado(s) ignorado(s)` : ''}`, 'success');
    await refreshSerials();
    await fetchStats();
  } catch (e) {
    toast('Erro: ' + e.message, 'error');
  }
}

// ─── Upload Modal ─────────────────────────────────────────────────────────────
function openUploadModal() {
  clearFileSelection();
  openModal('modal-upload');
}

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) setSelectedFile(file);
}

function setSelectedFile(file) {
  state.selectedFile = file;
  document.getElementById('file-name').textContent = file.name;
  document.getElementById('file-preview').style.display = 'block';
  document.getElementById('upload-area').style.display = 'none';
  document.getElementById('btn-upload-submit').disabled = false;
}

function clearFileSelection() {
  state.selectedFile = null;
  document.getElementById('file-input').value = '';
  document.getElementById('file-preview').style.display = 'none';
  document.getElementById('upload-area').style.display = 'flex';
  document.getElementById('btn-upload-submit').disabled = true;
}

function handleDragOver(e) {
  e.preventDefault();
  document.getElementById('upload-area').classList.add('drag-over');
}
function handleDragLeave() {
  document.getElementById('upload-area').classList.remove('drag-over');
}
function handleDrop(e) {
  e.preventDefault();
  document.getElementById('upload-area').classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) setSelectedFile(file);
}

async function submitUpload() {
  if (!state.selectedFile) return;
  const btn = document.getElementById('btn-upload-submit');
  btn.disabled = true;
  btn.textContent = 'Importando...';

  try {
    const { added, duplicates, total } = await api.serials.upload(state.selectedFile);
    closeModal('modal-upload');
    toast(`✅ Importados ${added} de ${total} serial(is)${duplicates ? ` (${duplicates} duplicados)` : ''}`, 'success');
    await refreshSerials();
    await fetchStats();
  } catch (e) {
    toast('Erro no upload: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg> Importar`;
  }
}

// ─── Settings ─────────────────────────────────────────────────────────────────
async function loadConfig() {
  try {
    const { data } = await api.config.get();
    document.getElementById('input-username').value = data.username || '';
    document.getElementById('input-password').value = '';
    document.getElementById('pass-hint').textContent = data.password_set
      ? 'Senha salva. Deixe em branco para manter a atual.'
      : 'Nenhuma senha salva ainda.';
    document.getElementById('input-url').value = data.fulltrack_url || '';
    document.getElementById('input-search-selector').value = data.search_selector || '';
    document.getElementById('input-timeout').value = data.timeout || 20;
    document.getElementById('input-delay').value = data.delay_between || 1;
    document.getElementById('input-headless').checked = data.headless !== false;
  } catch (e) {
    toast('Erro ao carregar configurações: ' + e.message, 'error');
  }
}

async function saveCredentials(e) {
  e.preventDefault();
  const payload = {
    username: document.getElementById('input-username').value.trim(),
    password: document.getElementById('input-password').value,
  };
  try {
    await api.config.save(payload);
    toast('✅ Credenciais salvas com sucesso!', 'success');
    document.getElementById('input-password').value = '';
    document.getElementById('pass-hint').textContent = 'Senha salva. Deixe em branco para manter a atual.';
  } catch (e) {
    toast('Erro: ' + e.message, 'error');
  }
}

async function saveAutomation(e) {
  e.preventDefault();
  const payload = {
    fulltrack_url: document.getElementById('input-url').value.trim(),
    search_selector: document.getElementById('input-search-selector').value.trim(),
    timeout: document.getElementById('input-timeout').value,
    delay_between: document.getElementById('input-delay').value,
    headless: document.getElementById('input-headless').checked,
  };
  try {
    await api.config.save(payload);
    toast('✅ Configurações de automação salvas!', 'success');
  } catch (e) {
    toast('Erro: ' + e.message, 'error');
  }
}

async function testConnection() {
  toast('⏳ Iniciando teste de conexão...', 'info');
  // Inicia um processamento com um serial fictício para testar o login
  toast('Para testar, adicione um serial real e clique em "Bloquear" na tabela.', 'info');
}

function togglePassword(inputId, btn) {
  const inp = document.getElementById(inputId);
  const isPass = inp.type === 'password';
  inp.type = isPass ? 'text' : 'password';
  btn.style.opacity = isPass ? '1' : '0.5';
}

// ─── Logs ─────────────────────────────────────────────────────────────────────
function setLogFilter(level, btn) {
  state.logFilter = level;
  document.querySelectorAll('.log-filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderLogs();
}

function renderLogs() {
  const container = document.getElementById('logs-container');
  const filtered = state.logFilter
    ? state.logs.filter(l => l.level === state.logFilter)
    : state.logs;

  if (!filtered.length) {
    container.innerHTML = '<div class="log-empty">Nenhum log encontrado...</div>';
    return;
  }

  // Render newest first
  const reversed = [...filtered].reverse();
  container.innerHTML = reversed.map(l => `
    <div class="log-entry ${l.level || 'INFO'}">
      <span class="log-ts">${formatTime(l.timestamp)}</span>
      <span class="log-level">${l.level || 'INFO'}</span>
      <span class="log-msg">${escHtml(l.message)}</span>
    </div>`).join('');

  if (document.getElementById('auto-scroll').checked) {
    container.scrollTop = 0; // newest on top
  }
}

async function clearLogs() {
  try {
    await api.logs.clear();
    state.logs = [];
    state.lastLogId = -1;
    renderLogs();
    toast('Logs limpos', 'success');
  } catch (e) {
    toast('Erro: ' + e.message, 'error');
  }
}

// ─── Modals ───────────────────────────────────────────────────────────────────
function openModal(id) {
  document.getElementById(id).classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeModal(id) {
  document.getElementById(id).classList.remove('open');
  document.body.style.overflow = '';
}
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(el => {
      el.classList.remove('open');
      document.body.style.overflow = '';
    });
  }
});

// ─── Toasts ───────────────────────────────────────────────────────────────────
function toast(message, type = 'info', duration = 4000) {
  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ️'}</span><span class="toast-msg">${escHtml(message)}</span>`;
  document.getElementById('toast-container').prepend(el);
  setTimeout(() => {
    el.style.animation = 'fadeOut 0.3s ease forwards';
    setTimeout(() => el.remove(), 300);
  }, duration);
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatDate(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch { return iso; }
}

function formatTime(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch { return iso.slice(11, 19) || ''; }
}

// ─── Init ─────────────────────────────────────────────────────────────────────
async function init() {
  navigate('dashboard');
  await startPolling();
}

document.addEventListener('DOMContentLoaded', init);
