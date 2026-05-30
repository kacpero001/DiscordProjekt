/* ============================================
   NEXUS CHAT - Main JavaScript
   ============================================ */

// ===== UTILITIES =====
function showToast(message, type = 'info') {
  const container = document.querySelector('.toast-container') || createToastContainer();
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function createToastContainer() {
  const el = document.createElement('div');
  el.className = 'toast-container';
  document.body.appendChild(el);
  return el;
}

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

async function apiPost(url, data = {}, isFormData = false) {
  const options = {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
  };
  if (isFormData) {
    options.body = data;
  } else {
    options.headers['Content-Type'] = 'application/x-www-form-urlencoded';
    options.body = new URLSearchParams(data);
  }
  const res = await fetch(url, options);
  return res.json();
}

// ===== WEBSOCKET CHAT =====
class ChatSocket {
  constructor(url) {
    this.url = url;
    this.socket = null;
    this.reconnectAttempts = 0;
    this.maxReconnect = 5;
    this.typingTimeout = null;
    this.connect();
  }

  connect() {
    this.socket = new WebSocket(this.url);
    this.socket.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };
    this.socket.onmessage = (e) => this.handleMessage(JSON.parse(e.data));
    this.socket.onclose = () => this.handleClose();
    this.socket.onerror = (e) => console.error('WS Error:', e);
  }

  handleClose() {
    if (this.reconnectAttempts < this.maxReconnect) {
      this.reconnectAttempts++;
      setTimeout(() => this.connect(), 1000 * this.reconnectAttempts);
    }
  }

  send(data) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    }
  }

  sendMessage(content) {
    this.send({ type: 'message', content });
  }

  sendTyping(isTyping) {
    this.send({ type: 'typing', is_typing: isTyping });
  }

  sendReaction(messageId, emoji) {
    this.send({ type: 'reaction', message_id: messageId, emoji });
  }

  sendDelete(messageId) {
    this.send({ type: 'delete', message_id: messageId });
  }

  handleMessage(data) {
    switch (data.type) {
      case 'message': appendMessage(data); break;
      case 'dm': appendMessage(data, true); break;
      case 'typing': showTyping(data); break;
      case 'reaction': updateReaction(data); break;
      case 'deleted': markDeleted(data.message_id); break;
      case 'user_status': updateUserStatus(data); break;
    }
  }
}

// ===== MESSAGE RENDERING =====
function appendMessage(data, isDm = false) {
  const area = document.getElementById('messages-area');
  if (!area) return;

  const div = document.createElement('div');
  div.className = 'message-group';
  div.dataset.messageId = data.message_id || data.id;

  const avatarHtml = data.avatar
    ? `<img src="${data.avatar}" alt="${data.username}" class="message-avatar">`
    : `<div class="avatar-placeholder-lg">${getInitials(data.username)}</div>`;

  const roleBadge = data.role && data.role !== 'user'
    ? `<span class="role-badge role-${data.role}">${data.role === 'admin' ? 'Admin' : 'Mod'}</span>`
    : '';

  const actionsHtml = !isDm ? `
    <div class="message-actions">
      <button class="message-action-btn" onclick="openEmojiPicker(this, ${data.message_id})" title="Reakcja">😊</button>
      <button class="message-action-btn danger" onclick="deleteMsg(${data.message_id})" title="Usuń">🗑️</button>
    </div>` : '';

  div.innerHTML = `
    ${avatarHtml}
    <div class="message-content">
      <div class="message-header">
        <span class="message-username" onclick="openUserMenu(event, '${data.username}')">${escapeHtml(data.username)}</span>
        ${roleBadge}
        <span class="message-timestamp">${data.timestamp}</span>
      </div>
      <div class="message-text" id="msg-text-${data.message_id}">${escapeHtml(data.content)}</div>
      <div class="message-reactions" id="reactions-${data.message_id}"></div>
    </div>
    ${actionsHtml}
  `;

  area.appendChild(div);
  scrollToBottom();
  playNotificationSound();
}

function appendFileMessage(data) {
  const area = document.getElementById('messages-area');
  if (!area) return;
  const div = document.createElement('div');
  div.className = 'message-group';
  const avatarHtml = data.avatar
    ? `<img src="${data.avatar}" alt="${data.username}" class="message-avatar">`
    : `<div class="avatar-placeholder-lg">${getInitials(data.username)}</div>`;
  let fileHtml = '';
  if (data.message_type === 'image') {
    fileHtml = `<img src="${data.file_url}" class="message-image" onclick="openLightbox(this.src)" alt="obraz">`;
  } else if (data.message_type === 'audio') {
    fileHtml = `<div class="message-audio"><audio controls src="${data.file_url}"></audio></div>`;
  }
  div.innerHTML = `
    ${avatarHtml}
    <div class="message-content">
      <div class="message-header">
        <span class="message-username">${escapeHtml(data.username)}</span>
        <span class="message-timestamp">${data.timestamp}</span>
      </div>
      ${data.content ? `<div class="message-text">${escapeHtml(data.content)}</div>` : ''}
      ${fileHtml}
    </div>
  `;
  area.appendChild(div);
  scrollToBottom();
}

function markDeleted(messageId) {
  const el = document.getElementById(`msg-text-${messageId}`);
  if (el) {
    el.textContent = 'Wiadomość została usunięta';
    el.classList.add('deleted');
  }
}

function updateReaction(data) {
  const container = document.getElementById(`reactions-${data.message_id}`);
  if (!container) return;
  let badge = container.querySelector(`[data-emoji="${data.emoji}"]`);
  if (data.action === 'added') {
    if (!badge) {
      badge = document.createElement('button');
      badge.className = 'reaction-badge';
      badge.dataset.emoji = data.emoji;
      badge.dataset.users = JSON.stringify([data.username]);
      badge.dataset.count = 1;
      badge.innerHTML = `${data.emoji} <span class="reaction-count">1</span>`;
      badge.onclick = () => window.chatSocket?.sendReaction(data.message_id, data.emoji);
      container.appendChild(badge);
    } else {
      const users = JSON.parse(badge.dataset.users || '[]');
      users.push(data.username);
      badge.dataset.users = JSON.stringify(users);
      badge.dataset.count = users.length;
      badge.querySelector('.reaction-count').textContent = users.length;
    }
    if (data.username === window.currentUser) badge.classList.add('mine');
  } else if (data.action === 'removed') {
    if (badge) {
      const users = JSON.parse(badge.dataset.users || '[]');
      const idx = users.indexOf(data.username);
      if (idx > -1) users.splice(idx, 1);
      if (users.length === 0) {
        badge.remove();
      } else {
        badge.dataset.users = JSON.stringify(users);
        badge.dataset.count = users.length;
        badge.querySelector('.reaction-count').textContent = users.length;
        if (data.username === window.currentUser) badge.classList.remove('mine');
      }
    }
  }
}

function showTyping(data) {
  const el = document.querySelector('.typing-indicator');
  if (!el) return;
  if (data.is_typing) {
    el.textContent = `${data.username} pisze...`;
    clearTimeout(window.typingClearTimer);
    window.typingClearTimer = setTimeout(() => el.textContent = '', 3000);
  } else {
    el.textContent = '';
  }
}

function updateUserStatus(data) {
  const dots = document.querySelectorAll(`[data-username="${data.username}"] .status-dot`);
  dots.forEach(dot => {
    dot.className = `status-dot status-${data.status}`;
  });
}

// ===== EMOJI PICKER =====
const EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '😡', '🎉', '🔥', '✅', '👀', '🙏', '💯'];

function openEmojiPicker(btn, messageId) {
  document.querySelector('.emoji-picker')?.remove();
  const picker = document.createElement('div');
  picker.className = 'emoji-picker';
  picker.style.cssText = 'position:absolute;z-index:500;';
  EMOJIS.forEach(emoji => {
    const b = document.createElement('button');
    b.className = 'emoji-btn';
    b.textContent = emoji;
    b.onclick = () => {
      window.chatSocket?.sendReaction(messageId, emoji);
      picker.remove();
    };
    picker.appendChild(b);
  });
  const rect = btn.getBoundingClientRect();
  picker.style.top = (rect.top - 60) + 'px';
  picker.style.left = rect.left + 'px';
  document.body.appendChild(picker);
  setTimeout(() => document.addEventListener('click', () => picker.remove(), { once: true }), 0);
}

// ===== MESSAGE INPUT =====
function initMessageInput(sendUrl = null) {
  const input = document.getElementById('message-input');
  const sendBtn = document.getElementById('send-btn');
  const fileInput = document.getElementById('file-input');
  const preview = document.getElementById('upload-preview');
  let typingTimer = null;
  let isTyping = false;

  if (!input) return;

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendTextMessage();
    }
    if (!isTyping) {
      isTyping = true;
      window.chatSocket?.sendTyping(true);
    }
    clearTimeout(typingTimer);
    typingTimer = setTimeout(() => {
      isTyping = false;
      window.chatSocket?.sendTyping(false);
    }, 2000);
  });

  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 200) + 'px';
  });

  if (sendBtn) sendBtn.onclick = sendTextMessage;

  if (fileInput) {
    fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;
      if (preview) {
        preview.style.display = 'flex';
        if (file.type.startsWith('image/')) {
          const reader = new FileReader();
          reader.onload = (ev) => {
            preview.innerHTML = `<img src="${ev.target.result}"> <span>${escapeHtml(file.name)}</span> <button onclick="clearUpload()" class="btn btn-sm">✕</button>`;
          };
          reader.readAsDataURL(file);
        } else {
          preview.innerHTML = `<span>🎵 ${escapeHtml(file.name)}</span> <button onclick="clearUpload()" class="btn btn-sm">✕</button>`;
        }
      }
    });
  }

  function sendTextMessage() {
    const content = input.value.trim();
    if (!content && !fileInput?.files[0]) return;

    if (fileInput?.files[0]) {
      sendFile(fileInput.files[0], content, sendUrl);
    } else if (window.chatSocket) {
      window.chatSocket.sendMessage(content);
      input.value = '';
      input.style.height = 'auto';
    }
  }
}

function clearUpload() {
  document.getElementById('file-input').value = '';
  const preview = document.getElementById('upload-preview');
  if (preview) { preview.style.display = 'none'; preview.innerHTML = ''; }
}

function sendFile(file, caption, url) {
  if (!url) return;
  const fd = new FormData();
  fd.append('file', file);
  if (caption) fd.append('content', caption);
  fd.append('csrfmiddlewaretoken', getCookie('csrftoken'));

  fetch(url, { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      if (data.ok) {
        appendFileMessage(data);
        clearUpload();
        document.getElementById('message-input').value = '';
      }
    })
    .catch(e => showToast('Błąd wysyłania pliku', 'error'));
}

// ===== VOICE RECORDING =====
let mediaRecorder = null;
let audioChunks = [];

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
    mediaRecorder.onstop = () => {
      const blob = new Blob(audioChunks, { type: 'audio/webm' });
      const file = new File([blob], 'voice-message.webm', { type: 'audio/webm' });
      const sendUrl = document.getElementById('send-url')?.value;
      if (sendUrl) sendFile(file, '', sendUrl);
      stream.getTracks().forEach(t => t.stop());
    };
    mediaRecorder.start();
    document.getElementById('record-btn')?.classList.add('recording');
    showToast('Nagrywanie... kliknij ponownie aby zatrzymać', 'info');
  } catch (e) {
    showToast('Brak dostępu do mikrofonu', 'error');
  }
}

function toggleRecording() {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop();
    document.getElementById('record-btn')?.classList.remove('recording');
  } else {
    startRecording();
  }
}

// ===== MODALS =====
function openModal(id) {
  document.getElementById(id)?.classList.remove('d-none');
  document.getElementById(id)?.style.setProperty('display', 'flex');
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = 'none';
}

function openCreateChannelModal() {
  const modal = document.getElementById('create-channel-modal');
  if (modal) modal.style.display = 'flex';
}

// ===== USER CONTEXT MENU =====
function openUserMenu(event, username) {
  event.preventDefault();
  document.querySelector('.context-menu')?.remove();
  const menu = document.createElement('div');
  menu.className = 'context-menu';
  const isDmPage = window.location.href.includes('/dm/');
  menu.innerHTML = `
    <a href="/accounts/profile/${username}/" class="context-menu-item">👤 Profil</a>
    <a href="/chat/dm/${username}/" class="context-menu-item">💬 Wiadomość</a>
    <div class="context-menu-divider"></div>
    <button class="context-menu-item" onclick="reportUser('${username}')">🚩 Zgłoś</button>
    ${window.isModerator ? `<button class="context-menu-item danger" onclick="blockUser('${username}')">🔨 Zablokuj</button>` : ''}
  `;
  menu.style.cssText = `position:fixed;top:${event.clientY}px;left:${event.clientX}px;`;
  document.body.appendChild(menu);
  setTimeout(() => document.addEventListener('click', () => menu.remove(), { once: true }), 0);
}

async function reportUser(username) {
  const reason = prompt('Podaj powód zgłoszenia:');
  if (!reason) return;
  const data = await apiPost(`/chat/user/${username}/report/`, { reason });
  showToast(data.ok ? 'Zgłoszono użytkownika' : 'Błąd', data.ok ? 'success' : 'error');
}

async function blockUser(username) {
  if (!confirm(`Zablokować użytkownika ${username}?`)) return;
  const data = await apiPost(`/chat/user/${username}/block/`, {});
  showToast(data.blocked ? `${username} zablokowany` : `${username} odblokowany`, 'success');
}

// ===== DELETE MESSAGE =====
async function deleteMsg(messageId) {
  if (!confirm('Usunąć wiadomość?')) return;
  if (window.chatSocket) {
    window.chatSocket.sendDelete(messageId);
  } else {
    const data = await apiPost(`/chat/channel/message/${messageId}/delete/`, {});
    if (data.ok) markDeleted(messageId);
  }
}

// ===== CHANNEL MANAGEMENT =====
async function createChannel() {
  const name = document.getElementById('channel-name')?.value.trim();
  const description = document.getElementById('channel-description')?.value.trim();
  const type = document.getElementById('channel-type')?.value;
  const isPublic = document.getElementById('channel-public')?.checked ? 'true' : 'false';

  if (!name) { showToast('Podaj nazwę kanału', 'error'); return; }

  const data = await apiPost('/chat/channel/create/', {
    name, description: description || '', channel_type: type, is_public: isPublic
  });

  if (data.ok) {
    closeModal('create-channel-modal');
    showToast(`Kanał #${data.name} utworzony!`, 'success');
    const prefix = data.type === 'voice' ? '🔊 ' : '# ';
    const list = document.getElementById('channels-list');
    if (list) {
      const item = document.createElement('a');
      item.href = `/chat/channel/${data.id}/`;
      item.className = 'channel-item';
      item.innerHTML = `<i class="channel-icon">${data.type === 'voice' ? '🔊' : '#'}</i>${escapeHtml(data.name)}`;
      list.appendChild(item);
    }
  } else {
    showToast(data.error || 'Błąd tworzenia kanału', 'error');
  }
}

async function deleteChannel(channelId) {
  if (!confirm('Usunąć kanał? Ta operacja jest nieodwracalna.')) return;
  const data = await apiPost(`/chat/channel/${channelId}/delete/`, {});
  if (data.ok) {
    showToast('Kanał usunięty', 'success');
    window.location.href = '/chat/';
  }
}

// ===== STATUS =====
async function setStatus(status) {
  const data = await apiPost('/accounts/status/', { status });
  if (data.ok) {
    const dot = document.querySelector('.user-panel .status-dot');
    if (dot) dot.className = `status-dot status-${status}`;
    document.querySelectorAll('.status-option').forEach(el => {
      el.classList.toggle('active', el.dataset.status === status);
    });
    showToast('Status zmieniony', 'success');
  }
}

// ===== LIGHTBOX =====
function openLightbox(src) {
  const overlay = document.createElement('div');
  overlay.className = 'lightbox-overlay';
  overlay.innerHTML = `<img src="${src}" alt="pełny rozmiar">`;
  overlay.onclick = () => overlay.remove();
  document.body.appendChild(overlay);
}

// ===== MOBILE SIDEBAR =====
function toggleSidebar() {
  document.querySelector('.channel-sidebar')?.classList.toggle('open');
}

// ===== SEARCH USERS =====
let searchTimer = null;
function searchUsers(query) {
  clearTimeout(searchTimer);
  const results = document.getElementById('search-results');
  if (!results) return;
  if (!query) { results.innerHTML = ''; results.style.display = 'none'; return; }
  searchTimer = setTimeout(async () => {
    const res = await fetch(`/accounts/search/?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    if (data.users.length === 0) { results.style.display = 'none'; return; }
    results.style.display = 'block';
    results.innerHTML = data.users.map(u => `
      <a href="/chat/dm/${u.username}/" class="member-item">
        <div class="member-avatar">
          ${u.avatar ? `<img src="${u.avatar}" alt="${escapeHtml(u.username)}">` : `<div class="mini-placeholder">${getInitials(u.username)}</div>`}
          <span class="status-dot status-${u.status}"></span>
        </div>
        <span class="member-name">${escapeHtml(u.username)}</span>
      </a>
    `).join('');
  }, 300);
}

// ===== HELPERS =====
function scrollToBottom() {
  const area = document.getElementById('messages-area');
  if (area) {
    const parent = area.closest('.messages-area') || area;
    parent.scrollTop = parent.scrollHeight;
  }
}

function escapeHtml(text) {
  if (!text) return '';
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
             .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

function getInitials(username) {
  return (username || '??').slice(0, 2).toUpperCase();
}

function playNotificationSound() {
  if (!window.notifSound) return;
  try {
    const audio = new Audio('data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAA...');
    audio.volume = 0.1;
  } catch(e) {}
}

// ===== UNREAD BADGE =====
function updateUnreadBadge() {
  fetch('/chat/unread/')
    .then(r => r.json())
    .then(data => {
      const badge = document.getElementById('unread-badge');
      if (badge) {
        badge.textContent = data.count > 0 ? data.count : '';
        badge.style.display = data.count > 0 ? 'flex' : 'none';
      }
    });
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => {
  scrollToBottom();
  setInterval(updateUnreadBadge, 30000);

  // Close modals on overlay click
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.style.display = 'none';
    });
  });

  // Record btn
  document.getElementById('record-btn')?.addEventListener('click', toggleRecording);
});