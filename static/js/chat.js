/**
 * Gemini AI Studio - Frontend Application Logic
 */

// State Management
const STATE = {
  currentSessionId: null,
  sessions: [],
  selectedModel: 'gemini-3.8-flash',
  temperature: 0.7,
  systemInstruction: '',
  webSearch: true,
  isGenerating: false,
  abortController: null,
  apiKeyConnected: false
};

// DOM Elements
const DOM = {
  sidebar: document.getElementById('sidebar'),
  sidebarToggleBtn: document.getElementById('sidebarToggleBtn'),
  sidebarCloseBtn: document.getElementById('sidebarCloseBtn'),
  newChatBtn: document.getElementById('newChatBtn'),
  clearAllSessionsBtn: document.getElementById('clearAllSessionsBtn'),
  chatHistoryList: document.getElementById('chatHistoryList'),
  apiStatusCard: document.getElementById('apiStatusCard'),
  statusDot: document.getElementById('statusDot'),
  statusLabel: document.getElementById('statusLabel'),
  keyPreview: document.getElementById('keyPreview'),
  openSettingsBtn: document.getElementById('openSettingsBtn'),
  modelSelectNav: document.getElementById('modelSelectNav'),
  exportChatBtn: document.getElementById('exportChatBtn'),
  clearCurrentChatBtn: document.getElementById('clearCurrentChatBtn'),
  chatViewport: document.getElementById('chatViewport'),
  welcomeScreen: document.getElementById('welcomeScreen'),
  messagesContainer: document.getElementById('messagesContainer'),
  activeModelPill: document.getElementById('activeModelPill'),
  activeModelName: document.getElementById('activeModelName'),
  webSearchToggle: document.getElementById('webSearchToggle'),
  webSearchToggleLabel: document.getElementById('webSearchToggleLabel'),
  statusNotice: document.getElementById('statusNotice'),
  messageInput: document.getElementById('messageInput'),
  sendBtn: document.getElementById('sendBtn'),
  stopBtn: document.getElementById('stopBtn'),
  settingsModal: document.getElementById('settingsModal'),
  closeSettingsBtn: document.getElementById('closeSettingsBtn'),
  modalModelSelect: document.getElementById('modalModelSelect'),
  temperatureSlider: document.getElementById('temperatureSlider'),
  tempValueDisplay: document.getElementById('tempValueDisplay'),
  systemInstructionInput: document.getElementById('systemInstructionInput'),
  modalWebSearchCheckbox: document.getElementById('modalWebSearchCheckbox'),
  modalKeyStatusBox: document.getElementById('modalKeyStatusBox'),
  modalKeyStatusText: document.getElementById('modalKeyStatusText'),
  resetSettingsBtn: document.getElementById('resetSettingsBtn'),
  saveSettingsBtn: document.getElementById('saveSettingsBtn'),
  toastContainer: document.getElementById('toastContainer')
};

// Markdown Renderer Customization
function configureMarked() {
  if (typeof marked !== 'undefined') {
    const renderer = new marked.Renderer();

    renderer.code = function(code, language) {
      const validLang = language && hljs.getLanguage(language) ? language : 'plaintext';
      let highlightedCode = '';
      try {
        highlightedCode = hljs.highlight(code, { language: validLang, ignoreIllegals: true }).value;
      } catch (e) {
        highlightedCode = code;
      }

      return `
        <div class="code-block-container">
          <div class="code-header">
            <span class="code-lang">${validLang}</span>
            <button class="copy-code-btn" onclick="copyCodeFromBlock(this)">
              <i class="fa-regular fa-copy"></i>
              <span>코드 복사</span>
            </button>
          </div>
          <pre><code class="language-${validLang}">${highlightedCode}</code></pre>
        </div>
      `;
    };

    marked.setOptions({
      renderer: renderer,
      breaks: true,
      gfm: true
    });
  }
}

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
  configureMarked();
  loadPreferences();
  setupEventListeners();
  await checkApiStatus();
  loadSessions();

  if (STATE.sessions.length === 0) {
    createNewSession();
  } else {
    switchSession(STATE.sessions[0].id);
  }
});

// Preferences Management (LocalStorage)
function loadPreferences() {
  const savedModel = localStorage.getItem('gemini_selected_model');
  if (savedModel) {
    STATE.selectedModel = savedModel;
    DOM.modelSelectNav.value = savedModel;
    DOM.modalModelSelect.value = savedModel;
  }
  updateModelDisplayName(STATE.selectedModel);

  const savedTemp = localStorage.getItem('gemini_temperature');
  if (savedTemp !== null) {
    STATE.temperature = parseFloat(savedTemp);
    DOM.temperatureSlider.value = STATE.temperature;
    DOM.tempValueDisplay.textContent = STATE.temperature.toFixed(1);
  }

  const savedSys = localStorage.getItem('gemini_system_instruction');
  if (savedSys !== null) {
    STATE.systemInstruction = savedSys;
    DOM.systemInstructionInput.value = savedSys;
  }

  const savedSearch = localStorage.getItem('gemini_web_search');
  if (savedSearch !== null) {
    STATE.webSearch = savedSearch === 'true';
  }
  updateWebSearchUI();
}

function updateWebSearchUI() {
  if (DOM.webSearchToggle) {
    if (STATE.webSearch) {
      DOM.webSearchToggle.classList.add('active');
      if (DOM.webSearchToggleLabel) DOM.webSearchToggleLabel.textContent = '실시간 수정구 ON';
    } else {
      DOM.webSearchToggle.classList.remove('active');
      if (DOM.webSearchToggleLabel) DOM.webSearchToggleLabel.textContent = '실시간 수정구 OFF';
    }
  }
  if (DOM.modalWebSearchCheckbox) {
    DOM.modalWebSearchCheckbox.checked = STATE.webSearch;
  }
}

function savePreferences() {
  localStorage.setItem('gemini_selected_model', STATE.selectedModel);
  localStorage.setItem('gemini_temperature', STATE.temperature);
  localStorage.setItem('gemini_system_instruction', STATE.systemInstruction);
  localStorage.setItem('gemini_web_search', STATE.webSearch);
}

function updateModelDisplayName(modelId) {
  const modelNames = {
    'gemini-3.8-flash': '아이린 • Gemini 3.8 Flash',
    'gemini-7.3-flash': '아이린 • Gemini 7.3 Flash',
    'gemini-3.7-flash': '아이린 • Gemini 3.7 Flash',
    'gemini-2.5-flash': '아이린 • Gemini 2.5 Flash',
    'gemini-2.5-pro': '아이린 • Gemini 2.5 Pro'
  };
  DOM.activeModelName.textContent = modelNames[modelId] || `아이린 • ${modelId}`;
}

// API Status Check
async function checkApiStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();

    if (data.has_api_key) {
      STATE.apiKeyConnected = true;
      DOM.statusDot.className = 'status-dot active';
      DOM.statusLabel.textContent = 'API 키 연결됨 (환경변수)';
      DOM.keyPreview.textContent = `Key: ${data.masked_key}`;

      DOM.modalKeyStatusBox.className = 'api-key-config-box';
      DOM.modalKeyStatusText.textContent = `GEMINI_API_KEY 로드 완료 (${data.masked_key})`;
    } else {
      STATE.apiKeyConnected = false;
      DOM.statusDot.className = 'status-dot error';
      DOM.statusLabel.textContent = 'API 키 누락됨';
      DOM.keyPreview.textContent = 'GEMINI_API_KEY 미설정';

      DOM.modalKeyStatusBox.className = 'api-key-config-box error';
      DOM.modalKeyStatusText.textContent = '환경변수에 GEMINI_API_KEY가 등록되어 있지 않습니다.';
      showToast('GEMINI_API_KEY 환경변수를 확인해주세요.', 'error');
    }
  } catch (err) {
    console.error('API Status check failed:', err);
    DOM.statusDot.className = 'status-dot error';
    DOM.statusLabel.textContent = '서버 연결 실패';
  }
}

// Session Management
function loadSessions() {
  try {
    const saved = localStorage.getItem('gemini_chat_sessions');
    STATE.sessions = saved ? JSON.parse(saved) : [];
  } catch (e) {
    STATE.sessions = [];
  }
  renderSessionList();
}

function saveSessions() {
  localStorage.setItem('gemini_chat_sessions', JSON.stringify(STATE.sessions));
  renderSessionList();
}

function createNewSession() {
  const newSession = {
    id: 'session_' + Date.now(),
    title: '새로운 대화',
    messages: [],
    createdAt: new Date().toISOString()
  };
  STATE.sessions.unshift(newSession);
  saveSessions();
  switchSession(newSession.id);
  DOM.messageInput.focus();
}

function switchSession(sessionId) {
  STATE.currentSessionId = sessionId;
  const session = STATE.sessions.find(s => s.id === sessionId);
  if (!session) return;

  renderSessionList();
  renderMessages(session.messages);

  // Close sidebar on mobile
  if (window.innerWidth <= 768) {
    DOM.sidebar.classList.remove('open');
  }
}

function deleteSession(sessionId, e) {
  if (e) e.stopPropagation();
  STATE.sessions = STATE.sessions.filter(s => s.id !== sessionId);
  saveSessions();

  if (STATE.currentSessionId === sessionId) {
    if (STATE.sessions.length > 0) {
      switchSession(STATE.sessions[0].id);
    } else {
      createNewSession();
    }
  }
  showToast('대화가 삭제되었습니다.', 'info');
}

function clearAllSessions() {
  if (confirm('모든 대화 기록을 삭제하시겠습니까?')) {
    STATE.sessions = [];
    saveSessions();
    createNewSession();
    showToast('모든 대화가 삭제되었습니다.', 'info');
  }
}

function renderSessionList() {
  DOM.chatHistoryList.innerHTML = '';
  STATE.sessions.forEach(session => {
    const item = document.createElement('div');
    item.className = `history-item ${session.id === STATE.currentSessionId ? 'active' : ''}`;
    item.onclick = () => switchSession(session.id);

    item.innerHTML = `
      <i class="fa-regular fa-message history-item-icon"></i>
      <span class="history-item-title">${escapeHtml(session.title)}</span>
      <button class="history-item-del" title="삭제" onclick="deleteSession('${session.id}', event)">
        <i class="fa-regular fa-trash-can"></i>
      </button>
    `;
    DOM.chatHistoryList.appendChild(item);
  });
}

// Message Rendering
function getCurrentSession() {
  return STATE.sessions.find(s => s.id === STATE.currentSessionId);
}

function renderMessages(messages) {
  DOM.messagesContainer.innerHTML = '';

  if (!messages || messages.length === 0) {
    DOM.welcomeScreen.classList.remove('hidden');
    return;
  }

  DOM.welcomeScreen.classList.add('hidden');

  messages.forEach((msg, idx) => {
    appendMessageElement(msg.role, msg.content, msg.model, msg.error, idx, msg.grounding);
  });

  scrollToBottom();
}

function renderGroundingHTML(grounding) {
  if (!grounding || !grounding.sources || grounding.sources.length === 0) return '';

  const queries = (grounding.queries || []).map(q => escapeHtml(q)).join(', ');
  const queryBadge = queries ? `<span class="grounding-query-badge" title="검색어: ${queries}"><i class="fa-solid fa-magnifying-glass"></i> ${queries}</span>` : '';

  const chips = grounding.sources.map(src => {
    const title = escapeHtml(src.title || '출처 링크');
    const uri = escapeHtml(src.uri || '#');
    return `
      <a href="${uri}" target="_blank" rel="noopener noreferrer" class="source-chip" title="${title}">
        <i class="fa-solid fa-arrow-up-right-from-square"></i>
        <span>${title}</span>
      </a>
    `;
  }).join('');

  return `
    <div class="grounding-sources-card">
      <div class="grounding-header">
        <div class="grounding-title">
          <i class="fa-solid fa-globe"></i>
          <span>실시간 웹 검색 출처 (${grounding.sources.length}건)</span>
        </div>
        ${queryBadge}
      </div>
      <div class="grounding-sources-list">
        ${chips}
      </div>
    </div>
  `;
}

function appendMessageElement(role, content, model, isError = false, index = null, grounding = null) {
  const row = document.createElement('div');
  row.className = `message-row ${role}`;
  if (index !== null) row.dataset.index = index;

  const isUser = role === 'user';
  const avatarHtml = isUser
    ? '<i class="fa-solid fa-feather-pointed"></i>'
    : '<img src="/static/img/ireen_avatar.png" alt="아이린" class="avatar-img-circle">';
  const displayName = isUser ? '여행자님' : '수습 마녀 아이린';

  const formattedContent = isUser ? escapeHtml(content).replace(/\n/g, '<br>') : marked.parse(content || '');
  const groundingHTML = !isUser ? renderGroundingHTML(grounding) : '';

  row.innerHTML = `
    <div class="message-avatar">${avatarHtml}</div>
    <div class="message-content-wrapper">
      <div class="message-meta">
        <span class="user-label">${displayName}</span>
        ${!isUser ? `<span class="model-tag">${model || STATE.selectedModel}</span>` : ''}
        ${grounding && grounding.sources && grounding.sources.length > 0 ? '<span class="model-tag" style="background: rgba(94, 234, 212, 0.15); color: #5eead4; border-color: rgba(94, 234, 212, 0.4);"><i class="fa-solid fa-crystal-ball"></i> 수정구 검색</span>' : ''}
      </div>
      <div class="message-bubble ${isError ? 'error-bubble' : ''}">
        ${formattedContent}
      </div>
      ${groundingHTML}
      <div class="message-actions">
        <button class="msg-action-btn" onclick="copyMessageText(this)">
          <i class="fa-regular fa-copy"></i> 복사
        </button>
      </div>
    </div>
  `;

  DOM.messagesContainer.appendChild(row);
  return row;
}

// Send and Stream Handling
async function handleSendMessage(customPrompt = null) {
  if (STATE.isGenerating) return;

  const prompt = customPrompt || DOM.messageInput.value.trim();
  if (!prompt) return;

  const session = getCurrentSession();
  if (!session) return;

  // Add user message to session
  const userMsg = {
    role: 'user',
    content: prompt,
    timestamp: new Date().toISOString()
  };
  session.messages.push(userMsg);

  // Auto-set title from first message
  if (session.messages.length === 1) {
    session.title = prompt.slice(0, 26) + (prompt.length > 26 ? '...' : '');
  }

  saveSessions();
  renderMessages(session.messages);

  DOM.messageInput.value = '';
  adjustTextareaHeight();

  // Create empty assistant row for streaming
  DOM.welcomeScreen.classList.add('hidden');
  const assistantRow = document.createElement('div');
  assistantRow.className = 'message-row model';
  const currentModel = STATE.selectedModel;
  const isWebSearchActive = STATE.webSearch;

  assistantRow.innerHTML = `
    <div class="message-avatar"><img src="/static/img/ireen_avatar.png" alt="아이린" class="avatar-img-circle"></div>
    <div class="message-content-wrapper">
      <div class="message-meta">
        <span class="user-label">수습 마녀 아이린</span>
        <span class="model-tag">${currentModel}</span>
        ${isWebSearchActive ? '<span class="model-tag" style="background: rgba(94, 234, 212, 0.15); color: #5eead4; border-color: rgba(94, 234, 212, 0.4);"><i class="fa-solid fa-crystal-ball"></i> 수정구 검색</span>' : ''}
      </div>
      ${isWebSearchActive ? '<div class="search-searching-badge" id="searchProgressBadge"><i class="fa-solid fa-crystal-ball"></i> <span>아이린이 지혜의 수정구로 세상의 기록을 비추어보는 중...</span></div>' : ''}
      <div class="message-bubble">
        <span class="stream-text"></span><span class="streaming-cursor"></span>
      </div>
      <div class="grounding-slot"></div>
      <div class="message-actions">
        <button class="msg-action-btn" onclick="copyMessageText(this)">
          <i class="fa-regular fa-copy"></i> 복사
        </button>
      </div>
    </div>
  `;
  DOM.messagesContainer.appendChild(assistantRow);
  scrollToBottom();

  const bubble = assistantRow.querySelector('.message-bubble');
  const streamTextSpan = bubble.querySelector('.stream-text');
  const cursor = bubble.querySelector('.streaming-cursor');
  const searchProgressBadge = assistantRow.querySelector('#searchProgressBadge');
  const groundingSlot = assistantRow.querySelector('.grounding-slot');

  setGeneratingState(true);
  let accumulatedText = '';
  let hadError = false;
  let receivedGrounding = null;

  STATE.abortController = new AbortController();

  try {
    const payload = {
      model: currentModel,
      messages: session.messages.map(m => ({ role: m.role, content: m.content })),
      temperature: STATE.temperature,
      system_instruction: STATE.systemInstruction,
      web_search: STATE.webSearch
    };

    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: STATE.abortController.signal
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status} (${response.statusText})`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Keep incomplete tail

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data: ')) continue;

        const dataStr = trimmed.slice(6);
        try {
          const data = JSON.parse(dataStr);

          if (data.error) {
            hadError = true;
            if (searchProgressBadge) searchProgressBadge.remove();
            bubble.classList.add('error-bubble');
            accumulatedText = data.message || '요청 처리 중 오류가 발생했습니다.';
            streamTextSpan.innerHTML = marked.parse(accumulatedText);
            break;
          }

          if (data.grounding) {
            receivedGrounding = data.grounding;
            if (groundingSlot) {
              groundingSlot.innerHTML = renderGroundingHTML(receivedGrounding);
            }
          }

          if (data.done) {
            if (data.grounding && !receivedGrounding) {
              receivedGrounding = data.grounding;
              if (groundingSlot) groundingSlot.innerHTML = renderGroundingHTML(receivedGrounding);
            }
            break;
          }

          if (data.text) {
            if (searchProgressBadge) searchProgressBadge.remove();
            accumulatedText += data.text;
            streamTextSpan.innerHTML = marked.parse(accumulatedText);
            scrollToBottom();
          }
        } catch (parseErr) {
          console.warn('SSE Parse error:', parseErr, dataStr);
        }
      }
    }

    if (searchProgressBadge) searchProgressBadge.remove();

    if (!hadError && accumulatedText) {
      session.messages.push({
        role: 'assistant',
        content: accumulatedText,
        model: currentModel,
        grounding: receivedGrounding,
        timestamp: new Date().toISOString()
      });
      saveSessions();
    } else if (hadError) {
      session.messages.push({
        role: 'assistant',
        content: accumulatedText,
        model: currentModel,
        error: true,
        timestamp: new Date().toISOString()
      });
      saveSessions();
    }

  } catch (err) {
    if (err.name === 'AbortError') {
      if (accumulatedText) {
        session.messages.push({
          role: 'assistant',
          content: accumulatedText + '\n\n*(생성이 사용자에 의해 중단되었습니다)*',
          model: currentModel,
          timestamp: new Date().toISOString()
        });
        saveSessions();
      }
      showToast('응답 생성이 중단되었습니다.', 'info');
    } else {
      console.error('Streaming error:', err);
      bubble.classList.add('error-bubble');
      accumulatedText = `서버 연결 에러: ${err.message}`;
      streamTextSpan.innerHTML = `<p>${escapeHtml(accumulatedText)}</p>`;
      showToast('스트리밍 중 오류 발생', 'error');
    }
  } finally {
    if (cursor) cursor.remove();
    setGeneratingState(false);
    STATE.abortController = null;
    scrollToBottom();
  }
}

function setGeneratingState(generating) {
  STATE.isGenerating = generating;
  if (generating) {
    DOM.sendBtn.classList.add('hidden');
    DOM.stopBtn.classList.remove('hidden');
    DOM.messageInput.disabled = true;
  } else {
    DOM.sendBtn.classList.remove('hidden');
    DOM.stopBtn.classList.add('hidden');
    DOM.messageInput.disabled = false;
    DOM.messageInput.focus();
  }
}

function stopGeneration() {
  if (STATE.abortController) {
    STATE.abortController.abort();
  }
}

// Event Listeners
function setupEventListeners() {
  // Sidebar Toggle
  DOM.sidebarToggleBtn.addEventListener('click', () => {
    DOM.sidebar.classList.toggle('open');
  });
  DOM.sidebarCloseBtn.addEventListener('click', () => {
    DOM.sidebar.classList.remove('open');
  });

  // New Chat & Clear
  DOM.newChatBtn.addEventListener('click', createNewSession);
  DOM.clearAllSessionsBtn.addEventListener('click', clearAllSessions);
  DOM.clearCurrentChatBtn.addEventListener('click', () => {
    const session = getCurrentSession();
    if (session && session.messages.length > 0) {
      if (confirm('현재 대화 내용을 모두 지우시겠습니까?')) {
        session.messages = [];
        saveSessions();
        renderMessages([]);
      }
    }
  });

  // Model Selection Sync
  DOM.modelSelectNav.addEventListener('change', (e) => {
    STATE.selectedModel = e.target.value;
    DOM.modalModelSelect.value = STATE.selectedModel;
    updateModelDisplayName(STATE.selectedModel);
    savePreferences();
    showToast(`모델이 '${STATE.selectedModel}'로 변경되었습니다.`, 'info');
  });

  DOM.modalModelSelect.addEventListener('change', (e) => {
    STATE.selectedModel = e.target.value;
    DOM.modelSelectNav.value = STATE.selectedModel;
    updateModelDisplayName(STATE.selectedModel);
    savePreferences();
  });

  // Export Chat
  DOM.exportChatBtn.addEventListener('click', exportChatAsMarkdown);

  // Suggestion Cards
  document.querySelectorAll('.suggestion-card').forEach(card => {
    card.addEventListener('click', () => {
      const prompt = card.getAttribute('data-prompt');
      if (prompt) {
        handleSendMessage(prompt);
      }
    });
  });

  // Input & Auto-resize
  DOM.messageInput.addEventListener('input', adjustTextareaHeight);
  DOM.messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  DOM.sendBtn.addEventListener('click', () => handleSendMessage());
  DOM.stopBtn.addEventListener('click', stopGeneration);

  // Global Keyboard Shortcuts
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      createNewSession();
    }
  });

  // Settings Modal Controls
  DOM.openSettingsBtn.addEventListener('click', () => {
    DOM.settingsModal.classList.remove('hidden');
  });
  DOM.closeSettingsBtn.addEventListener('click', () => {
    DOM.settingsModal.classList.add('hidden');
  });
  DOM.settingsModal.addEventListener('click', (e) => {
    if (e.target === DOM.settingsModal) {
      DOM.settingsModal.classList.add('hidden');
    }
  });

  DOM.temperatureSlider.addEventListener('input', (e) => {
    DOM.tempValueDisplay.textContent = parseFloat(e.target.value).toFixed(1);
  });

  // Web Search Toggle in Dock
  if (DOM.webSearchToggle) {
    DOM.webSearchToggle.addEventListener('click', () => {
      STATE.webSearch = !STATE.webSearch;
      updateWebSearchUI();
      savePreferences();
      showToast(`실시간 웹 검색이 ${STATE.webSearch ? '활성화' : '비활성화'}되었습니다.`, 'info');
    });
  }

  // Web Search Checkbox in Modal
  if (DOM.modalWebSearchCheckbox) {
    DOM.modalWebSearchCheckbox.addEventListener('change', (e) => {
      STATE.webSearch = e.target.checked;
      updateWebSearchUI();
      savePreferences();
    });
  }

  DOM.saveSettingsBtn.addEventListener('click', () => {
    STATE.temperature = parseFloat(DOM.temperatureSlider.value);
    STATE.systemInstruction = DOM.systemInstructionInput.value.trim();
    STATE.selectedModel = DOM.modalModelSelect.value;
    if (DOM.modalWebSearchCheckbox) {
      STATE.webSearch = DOM.modalWebSearchCheckbox.checked;
      updateWebSearchUI();
    }
    DOM.modelSelectNav.value = STATE.selectedModel;
    updateModelDisplayName(STATE.selectedModel);
    savePreferences();
    DOM.settingsModal.classList.add('hidden');
    showToast('설정이 저장되었습니다.', 'success');
  });

  DOM.resetSettingsBtn.addEventListener('click', () => {
    STATE.selectedModel = 'gemini-3.8-flash';
    STATE.temperature = 0.7;
    STATE.systemInstruction = '';
    STATE.webSearch = true;
    updateWebSearchUI();
    DOM.modalModelSelect.value = 'gemini-3.8-flash';
    DOM.modelSelectNav.value = 'gemini-3.8-flash';
    DOM.temperatureSlider.value = 0.7;
    DOM.tempValueDisplay.textContent = '0.7';
    DOM.systemInstructionInput.value = '';
    updateModelDisplayName('gemini-3.8-flash');
    savePreferences();
    showToast('설정이 기본값으로 복원되었습니다.', 'info');
  });
}

// Utility Functions
function adjustTextareaHeight() {
  const input = DOM.messageInput;
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 160) + 'px';
}

function scrollToBottom() {
  DOM.chatViewport.scrollTo({
    top: DOM.chatViewport.scrollHeight,
    behavior: 'smooth'
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

window.copyCodeFromBlock = function(btn) {
  const container = btn.closest('.code-block-container');
  const code = container.querySelector('pre code').innerText;
  navigator.clipboard.writeText(code).then(() => {
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-check"></i> <span>복사됨!</span>';
    setTimeout(() => {
      btn.innerHTML = originalText;
    }, 2000);
  });
};

window.copyMessageText = function(btn) {
  const bubble = btn.closest('.message-content-wrapper').querySelector('.message-bubble');
  navigator.clipboard.writeText(bubble.innerText).then(() => {
    showToast('메시지가 클립보드에 복사되었습니다.', 'success');
  });
};

function exportChatAsMarkdown() {
  const session = getCurrentSession();
  if (!session || session.messages.length === 0) {
    showToast('내보낼 대화 내용이 없습니다.', 'info');
    return;
  }

  let md = `# ${session.title}\n\n*생성일시: ${new Date(session.createdAt).toLocaleString('ko-KR')}*\n\n---\n\n`;
  session.messages.forEach(m => {
    const roleName = m.role === 'user' ? '### 👤 사용자' : `### ✨ Gemini (${m.model || STATE.selectedModel})`;
    md += `${roleName}\n\n${m.content}\n\n---\n\n`;
  });

  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${session.title.replace(/[\\/:*?"<>|]/g, '_')}.md`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('대화가 마크다운 파일로 다운로드되었습니다.', 'success');
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icon = type === 'success' ? 'fa-check' : type === 'error' ? 'fa-triangle-exclamation' : 'fa-circle-info';
  toast.innerHTML = `<i class="fa-solid ${icon}"></i><span>${escapeHtml(message)}</span>`;

  DOM.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(30px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3200);
}
