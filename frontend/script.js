let currentLang = 'en';
// Chat history is now purely in-memory and ephemeral (no saving to local/server)
// --- Global Error Boundary ---
window.addEventListener('error', function(e) {
  console.error("Global UI Error:", e.message);
});
window.addEventListener('unhandledrejection', function(e) {
  console.error("Unhandled Promise Rejection:", e.reason);
});

let chatHistory = []; 

const langConfig = {
  en: {
    voiceCode: 'en-IN',
    ttsLang: 'en-IN',
    placeholder: 'Enter your command...',
    voiceLabel: 'Voice Input',
    langLabel: 'English Mode Active',
    topics: {
      anime: 'Recommend a standout anime and provide a concise summary.',
      sports: 'Summarize the key sports developments of the week.',
      health: 'Offer three practical health tips for today.',
      study: 'Share efficient study strategies for focus and retention.',
      'fun facts': 'Provide three concise, surprising facts.',
      motivation: 'Offer a motivational message to stay productive.',
      productivity: 'Give three quick productivity hacks for a busy day.',
      tech: 'Explain one useful tech trend in simple terms.',
      travel: 'Suggest a short travel idea for a weekend escape.',
      movies: 'Give me the latest movie reviews, budget, box office collections, and hit/flop verdicts.'
    },
    topicLabels: ['Movies','Anime','Sports','Health','Study','Ideas','Motivation','Productivity','Tech','Travel'],
    topicKeys: ['movies','anime','sports','health','study','fun facts','motivation','productivity','tech','travel'],
    systemPrompt: `You are Mikey — a professional, factual, and helpful AI assistant. Prioritize accuracy: if you are unsure about a fact, say "I may be mistaken" or "I don't know" rather than inventing details. Avoid fabricating events, quotes, or specifics. Keep replies concise, polite, and indicate when a claim should be verified.`
  },
  te: {
    voiceCode: 'te-IN',
    ttsLang: 'te-IN',
    placeholder: 'మీ కమాండ్ ఇవ్వండి...',
    voiceLabel: 'వాయిస్ ఇన్పుట్',
    langLabel: 'తెలుగు మోడ్ ఆక్టివ్',
    topics: {
      anime: 'ఒక మంచి యానిమే సిరీస్ గురించి చెప్పండి!',
      sports: 'ఈ వారం క్రీడా వార్తలు చెప్పండి?',
      health: 'ఈ రోజుకి ఒక 3 హెల్త్ టిప్స్ చెప్పండి!',
      study: 'చదువు కోసం మంచి టిప్స్ చెప్పండి!',
      'fun facts': '3 ఆసక్తికరమైన నిజాలు చెప్పండి!',
      motivation: 'నన్ను ఉత్తేజపరిచే ఒక కొటేషన్ చెప్పండి!',
      productivity: 'ఉత్పాదకత పెంచడానికి 3 టిప్స్.',
      tech: 'ఒక కొత్త టెక్ ట్రెండ్ గురించి సులభంగా చెప్పండి.',
      travel: 'ఈ వారాంతానికి వెళ్ళడానికి ఒక మంచి ప్రదేశం చెప్పండి.',
      movies: 'తాజా సినిమాల రివ్యూలు, బడ్జెట్, బాక్స్ ఆఫీస్ కలెక్షన్స్, మరియు హిట్టా ఫ్లాపా అనే వివరాలు చెప్పండి.'
    },
    topicLabels: ['సినిమాలు','యానిమే','క్రీడలు','ఆరోగ్యం','చదువు','ఐడియాలు','మోటివేషన్','ఉత్పాదకత','టెక్','ట్రావెల్'],
    topicKeys: ['movies','anime','sports','health','study','fun facts','motivation','productivity','tech','travel'],
    systemPrompt: `మీరు Mikey — ఒక ప్రొఫెషనల్, వాస్తవికమైన మరియు సహాయక AI. ఖచ్చితత్వానికి ప్రాధాన్యత ఇవ్వండి: ఒక వాస్తవం గురించి మీకు ఖచ్చితంగా తెలియకపోతే 'నాకు బహుశా తెలియకపోవచ్చు' లేదా 'నాకు తెలియదు' అని చెప్పండి, అంతేగానీ మీరే ఊహించి చెప్పకండి. సంభాషణలు సంక్షిప్తంగా, మర్యాదగా ఉంచండి మరియు ఒక వాదనను ఎప్పుడు ధృవీకరించాలో సూచించండి.

CRITICAL INSTRUCTION: You MUST speak strictly in Telugu (and English if needed). ABSOLUTELY NO CHINESE, JAPANESE, OR KOREAN CHARACTERS ALLOWED.`
  }};

function updateTopicButtons() {
  const bar = document.getElementById('topicsBar');
  if (!bar) return;
  bar.innerHTML = '';
  const cfg = langConfig[currentLang];
  cfg.topicKeys.forEach((key, i) => {
    const btn = document.createElement('button');
    btn.className = 'topic-btn';
    btn.textContent = cfg.topicLabels[i];
    btn.onclick = () => quickTopic(key);
    bar.appendChild(btn);
  });
}

function setLang(lang) {
  currentLang = lang;
  document.getElementById('chatInput').placeholder = langConfig[lang].placeholder;
  document.getElementById('voiceLabel').textContent = langConfig[lang].voiceLabel;
  document.getElementById('langLabel').textContent = langConfig[lang].langLabel;
  document.getElementById('btnEN').className = 'lang-btn' + (lang === 'en' ? ' active' : '');
  document.getElementById('btnTE').className = 'lang-btn' + (lang === 'te' ? ' active' : '');
  
  // Only change welcome message if it's the first message
  const welcomeMsg = document.getElementById('welcomeMsg');
  if (welcomeMsg) {
    welcomeMsg.innerHTML = lang === 'te'
      ? `నమస్తే! నేను మీ <strong>Mikey</strong>. మీ కమాండ్ ఇవ్వండి, నేను సిద్ధంగా ఉన్నాను.`
      : `System initialized. I am <strong>Mikey</strong>. Standing by for your directive.`;
  }
  updateTopicButtons();
}

function formatMarkdown(text) {
  if (!text) return '';
  if (typeof marked !== 'undefined') {
    let html = marked.parse(text);
    // Replace literal \n with <br> inside table cells so code blocks format correctly
    html = html.replace(/(<(td|th)[^>]*>)([\s\S]*?)(<\/\2>)/g, function(match, p1, p2, p3, p4) {
      return p1 + p3.replace(/\\n/g, '<br>').replace(/\\"/g, '"') + p4;
    });
    // Wrap table in scrollable container
    html = html.replace(/<table[\s\S]*?<\/table>/g, '<div style="max-width: 100%; overflow-x: auto;">$&</div>');
    // Format Sources section into modern cards
    html = html.replace(/<p><strong>Sources:<\/strong><\/p>\s*<ul>([\s\S]*?)<\/ul>/gi, function(match, items) {
      const pills = items.replace(/<li>([\s\S]*?)<\/li>/gi, '<div class="source-pill">$1</div>');
      return `<div class="sources-card-container"><div class="sources-header">🌐 Verified Real-Time Web Sources</div><div class="sources-list">${pills}</div></div>`;
    });
    return html;
  }
  return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
}

// ── Claude / ChatGPT Style Bot Action Handlers ──────────────────
let feedbackToastTimer = null;
function showFeedbackToast(text) {
  let toast = document.getElementById('feedbackToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'feedbackToast';
    toast.className = 'feedback-toast';
    document.body.appendChild(toast);
  }
  toast.textContent = text;
  toast.classList.add('show');
  if (feedbackToastTimer) clearTimeout(feedbackToastTimer);
  feedbackToastTimer = setTimeout(() => {
    toast.classList.remove('show');
  }, 2200);
}

function unlockAudioPlayback() {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (AudioCtx) {
      if (!window._mikeyAudioCtx) {
        window._mikeyAudioCtx = new AudioCtx();
      }
      if (window._mikeyAudioCtx.state === 'suspended') {
        window._mikeyAudioCtx.resume();
      }
    }
  } catch(e) {}
}
window.addEventListener('click', unlockAudioPlayback, { once: true, passive: true });
window.addEventListener('keydown', unlockAudioPlayback, { once: true, passive: true });

function stopAllAudioPlayback() {
  if (typeof voiceQueue !== 'undefined' && voiceQueue && voiceQueue.stop) {
    voiceQueue.stop();
  }
  if (typeof activeAudio !== 'undefined' && activeAudio) {
    try {
      activeAudio.onended = null;
      activeAudio.onerror = null;
      activeAudio.pause();
      activeAudio.currentTime = 0;
    } catch(e) {}
    activeAudio = null;
  }
  if ('speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel();
    } catch(e) {}
  }
  window._activeSpeechUtter = null;
  if (typeof isSpeaking !== 'undefined') isSpeaking = false;
  document.querySelectorAll('.msg-action-btn.speaking').forEach(b => {
    b.classList.remove('speaking');
    b.setAttribute('data-tooltip', 'Read aloud');
  });
  if (typeof setVoiceState === 'function') setVoiceState('IDLE');
}

function copyMessageText(btn) {
  const msgContainer = btn.closest('.msg');
  if (!msgContainer) return;
  const bubble = msgContainer.querySelector('.bubble');
  if (!bubble) return;

  const clone = bubble.cloneNode(true);
  const sources = clone.querySelector('.sources-card-container');
  if (sources) sources.remove();
  const text = clone.innerText.trim();
  if (!text) return;

  const origSvg = btn.innerHTML;
  const checkSvg = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#34d399" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;

  const onSuccess = () => {
    btn.innerHTML = checkSvg;
    btn.setAttribute('data-tooltip', 'Copied!');
    showFeedbackToast('Copied to clipboard');
    setTimeout(() => {
      btn.innerHTML = origSvg;
      btn.setAttribute('data-tooltip', 'Copy text');
    }, 2000);
  };

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(onSuccess).catch(() => {
      fallbackCopyText(text, onSuccess);
    });
  } else {
    fallbackCopyText(text, onSuccess);
  }
}

function fallbackCopyText(text, onSuccess) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  try {
    document.execCommand('copy');
    if (onSuccess) onSuccess();
  } catch(e) {
    showFeedbackToast('Copy failed');
  }
  document.body.removeChild(ta);
}

function toggleMessageSpeech(btn) {
  if (btn.classList.contains('speaking')) {
    stopAllAudioPlayback();
    return;
  }

  stopAllAudioPlayback();
  unlockAudioPlayback();

  // Stop active speech recognition while reading message aloud
  if (recognition) {
    try { recognition.abort(); } catch(e) {}
    recognition = null;
  }

  const msgContainer = btn.closest('.msg');
  if (!msgContainer) return;
  const bubble = msgContainer.querySelector('.bubble');
  if (!bubble) return;

  const clone = bubble.cloneNode(true);
  const sources = clone.querySelector('.sources-card-container');
  if (sources) sources.remove();
  const text = clone.innerText.trim();
  if (!text) return;

  const clean = cleanTextForSpeech(text);
  if (!clean) return;

  btn.classList.add('speaking');
  btn.setAttribute('data-tooltip', 'Stop speech');

  const prefs = langConfig[currentLang] || { ttsLang: 'en' };
  const sentences = clean.split(/(?<=[.!?\n]+)\s+/).map(s => s.trim()).filter(s => s.length > 0);

  let queuedCount = 0;
  if (sentences.length <= 1) {
    voiceQueue.add(clean, prefs.ttsLang, true);
    queuedCount = 1;
  } else {
    sentences.forEach(s => {
      if (s && s.length > 0) {
        voiceQueue.add(s, prefs.ttsLang, true);
        queuedCount++;
      }
    });
    if (queuedCount === 0) {
      voiceQueue.add(clean, prefs.ttsLang, true);
      queuedCount = 1;
    }
  }

  if (queuedCount === 0) {
    btn.classList.remove('speaking');
    btn.setAttribute('data-tooltip', 'Read aloud');
  }
}

function handleThumbFeedback(btn, type) {
  const parent = btn.closest('.msg-actions');
  if (!parent) return;

  const upBtn = parent.querySelector('.thumb-up-btn');
  const downBtn = parent.querySelector('.thumb-down-btn');

  if (type === 'up') {
    const isActive = btn.classList.contains('active-up');
    if (downBtn) downBtn.classList.remove('active-down');
    if (isActive) {
      btn.classList.remove('active-up');
    } else {
      btn.classList.add('active-up');
      showFeedbackToast('Thanks for your feedback!');
    }
  } else if (type === 'down') {
    const isActive = btn.classList.contains('active-down');
    if (upBtn) upBtn.classList.remove('active-up');
    if (isActive) {
      btn.classList.remove('active-down');
    } else {
      btn.classList.add('active-down');
      showFeedbackToast("Feedback submitted. We'll improve!");
    }
  }
}

function regenerateLastResponse(btn) {
  if (isStreamActive) return;

  const msgContainer = btn.closest('.msg');
  if (!msgContainer) return;

  stopAllAudioPlayback();

  let prev = msgContainer.previousElementSibling;
  let userText = null;

  while (prev) {
    if (prev.classList.contains('user')) {
      const bubble = prev.querySelector('.bubble');
      if (bubble) {
        const clone = bubble.cloneNode(true);
        const imgInClone = clone.querySelector('.chat-img-attachment');
        if (imgInClone) imgInClone.remove();
        userText = clone.innerText.trim();
      }
      break;
    }
    prev = prev.previousElementSibling;
  }

  if (!userText && chatHistory.length > 0) {
    for (let i = chatHistory.length - 1; i >= 0; i--) {
      if (chatHistory[i].role === 'user') {
        userText = chatHistory[i].content;
        break;
      }
    }
  }

  if (!userText) {
    showFeedbackToast('No user prompt found to regenerate.');
    return;
  }

  msgContainer.remove();

  if (chatHistory.length > 0 && chatHistory[chatHistory.length - 1].role === 'assistant') {
    chatHistory.pop();
  }
  if (chatHistory.length > 0 && chatHistory[chatHistory.length - 1].role === 'user') {
    chatHistory.pop();
  }
  if (prev && prev.parentNode) {
    prev.remove();
  }

  saveCurrentThread();
  sendMessage(userText);
}

function createBotActionsHtml() {
  return `
    <div class="msg-actions">
      <button class="msg-action-btn copy-btn" onclick="copyMessageText(this)" data-tooltip="Copy text" title="Copy text">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
      </button>
      <button class="msg-action-btn speak-btn" onclick="toggleMessageSpeech(this)" data-tooltip="Read aloud" title="Read aloud">
        <svg class="speaker-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
          <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
          <path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>
        </svg>
      </button>
      <button class="msg-action-btn thumb-up-btn" onclick="handleThumbFeedback(this, 'up')" data-tooltip="Good response" title="Good response">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
        </svg>
      </button>
      <button class="msg-action-btn thumb-down-btn" onclick="handleThumbFeedback(this, 'down')" data-tooltip="Bad response" title="Bad response">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"></path>
        </svg>
      </button>
      <button class="msg-action-btn retry-btn" onclick="regenerateLastResponse(this)" data-tooltip="Regenerate" title="Regenerate">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="23 4 23 10 17 10"></polyline>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
        </svg>
      </button>
    </div>
  `;
}

function appendMsg(who, text, emoji, imageUrl) {
  const box = document.getElementById('messages');
  const welcome = document.getElementById('welcomeMsg');
  if (welcome && who === 'user') {
    welcome.remove();
  }
  const div = document.createElement('div');
  div.className = `msg ${who}`;
  const formattedText = who === 'bot' ? formatMarkdown(text) : text;
  let contentHtml = formattedText;
  if (imageUrl) {
    contentHtml = `<img src="${imageUrl}" class="chat-img-attachment" />` + (formattedText ? `<div>${formattedText}</div>` : '');
  }
  const isError = who === 'bot' && text && (text.startsWith('Error:') || text.includes('Network Error') || text.includes('Could not connect'));
  const actionsHtml = (who === 'bot' && text && !isError) ? createBotActionsHtml() : '';
  div.innerHTML = `<div class="avatar ${who}-av">${emoji}</div><div class="bubble ${who}-bubble">${contentHtml}</div>${actionsHtml}`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function appendSystemMsg(phase, text) {
  const box = document.getElementById('messages');
  const welcome = document.getElementById('welcomeMsg');
  if (welcome) welcome.remove();

  const div = document.createElement('div');
  div.className = 'msg system';
  
  let label = "SYSTEM";
  if (phase === 'plan') label = "IMPLEMENTATION PLAN";
  if (phase === 'complete') label = "IMPLEMENTATION COMPLETE";
  if (phase === 'error') label = "IMPLEMENTATION FAILED";
  
  div.innerHTML = `<div class="system-bubble ${phase}">
    <div class="system-label">${label}</div>
    ${formatMarkdown(text)}
  </div>`;
  
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

let lastAnnouncePoll = Date.now() / 1000;
async function pollAnnouncements() {
  try {
    const res = await fetch(`/api/poll-announce?since=${lastAnnouncePoll}`);
    if (res.ok) {
      const data = await res.json();
      if (data.messages && data.messages.length > 0) {
        for (const msg of data.messages) {
          appendSystemMsg(msg.phase, msg.message);
          lastAnnouncePoll = Math.max(lastAnnouncePoll, msg.ts);
        }
      }
    }
  } catch (e) {
    console.error("Announcement poll failed:", e);
  }
}
setInterval(pollAnnouncements, 2000);

function renderMessages() {
  const box = document.getElementById('messages');
  box.innerHTML = '';
  if (!chatHistory.length) {
    const welcome = document.createElement('div');
    welcome.className = 'msg bot';
    welcome.innerHTML = `<div class="avatar bot-av">✦</div><div class="bubble bot-bubble" id="welcomeMsg">System initialized. I am <strong>Mikey</strong>. Standing by for your directive.<br><br><span style="color:var(--text-muted);font-size:0.92em;">⚙ Layout synchronization complete. The Neural Link panel now fills the available viewport height, the command bar is anchored to the bottom, and all three dashboard columns are vertically aligned.</span></div>`;
    box.appendChild(welcome);
    return;
  }
  chatHistory.forEach(msg => {
    appendMsg(msg.role === 'user' ? 'user' : 'bot', msg.content, msg.role === 'user' ? '❖' : '✦', msg.image_url);
  });
}

function appendTyping() {
  const box = document.getElementById('messages');
  const id = 'typing-' + Date.now();
  const div = document.createElement('div');
  div.id = id; div.className = 'msg bot';
  div.innerHTML = `<div class="avatar bot-av">✦</div><div class="bubble bot-bubble"><div class="typing"><span></span><span></span><span></span></div></div>`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return id;
}

function removeTyping(id) { const el = document.getElementById(id); if (el) el.remove(); }

function openCommandTabs(message) {
  const commands = {
    youtube: 'https://www.youtube.com',
    youtude: 'https://www.youtube.com',
    chatgpt: 'https://chat.openai.com',
    claude: 'https://claude.ai',
    google: 'https://www.google.com',
    github: 'https://github.com',
    gmail: 'https://mail.google.com',
    gmaul: 'https://mail.google.com',
    reddit: 'https://www.reddit.com',
    spotify: 'https://open.spotify.com',
    spoifttr: 'https://open.spotify.com',
    telegram: 'https://web.telegram.org'
  };
  const lower = message.toLowerCase().trim();
  let opened = false;
  
  if (!lower.includes('open')) return false;

  const fireOpen = (url) => {
    fetch('/open-url', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ url: url }) 
    }).catch(console.error);
  };

  Object.keys(commands).forEach(key => {
    if (lower.includes(key)) {
      fireOpen(commands[key]);
      opened = true;
    }
  });

  if (!opened) {
    const match = lower.match(/open\s+([a-z0-9.-]+)/);
    if (match && match[1]) {
      let target = match[1];
      if (target.includes('.')) {
        if (!target.startsWith('http')) {
          target = 'https://' + target;
        }
        fireOpen(target);
      } else {
        fireOpen('https://www.' + target + '.com');
      }
      opened = true;
    }
  }

  return opened;
}

function quickTopic(key) {
  const prompt = langConfig[currentLang].topics[key];
  if (prompt) sendMessage(prompt);
}

const wxIcons = {'01d':'☀️','01n':'🌙','02d':'⛅','02n':'🌥️','03d':'☁️','03n':'☁️','04d':'🌦️','04n':'🌦️','09d':'🌧️','09n':'🌧️','10d':'🌦️','10n':'🌦️','11d':'⛈️','11n':'⛈️','13d':'❄️','13n':'❄️','50d':'🌫️','50n':'🌫️'};
async function getWeather() {
  const city = document.getElementById('cityInput').value.trim();
  if (!city) return;
  try {
    const res = await fetch('/weather', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ city }) });
    if (!res.ok) {
      const msg = currentLang === 'te' ? `"${city}" దొరకలేదు. స్పెల్లింగ్ చెక్ చేయి.` : `City "${city}" not found. Check spelling.`;
      appendMsg('bot', msg, '✦');
      return;
    }
    const d = await res.json();
    document.getElementById('wxTemp').textContent = `${d.temp}°C`;
    document.getElementById('wxCity').textContent = d.city;
    document.getElementById('wxDesc').textContent = d.description;
    document.getElementById('wxFeels').textContent = `${d.feels_like}°C`;
    document.getElementById('wxHumid').textContent = `${d.humidity}%`;
    document.getElementById('wxWind').textContent = `${d.wind} km/h`;
    document.getElementById('wxCountry').textContent = d.country;
    document.getElementById('wxIcon').textContent = wxIcons[d.icon] || '🌡️';
    document.getElementById('weatherResult').style.display = 'block';
  } catch (e) {
    appendMsg('bot', 'Weather fetch failed 😅', '✦');
  }
}

let activeAudio = null;

// ── Voice Assistant: Audio Queue, Pre-fetching & State Management ──────
let chatAbortController = null;
let isStreamActive = false;
let isLiveMode = false;
let voiceState = 'IDLE'; // 'IDLE' | 'LISTENING' | 'PROCESSING' | 'SPEAKING'
let voiceWatchdog = null;

function setVoiceState(state) {
  voiceState = state;
  const voiceBtn = document.getElementById('voiceBtn');
  const statusPill = document.getElementById('voiceStatusPill');
  const statusText = document.getElementById('voiceStatusText');
  const statusDot = document.getElementById('voiceStatusDot');

  if (voiceWatchdog) clearTimeout(voiceWatchdog);

  if (state === 'LISTENING') {
    if (voiceBtn) {
      voiceBtn.className = 'action-btn listening';
      voiceBtn.title = 'Listening... (Click to stop)';
    }
    if (statusPill) statusPill.style.display = 'inline-flex';
    if (statusText) statusText.textContent = 'Listening...';
    if (statusDot) statusDot.className = 'voice-status-dot listening';
  } else if (state === 'PROCESSING') {
    if (voiceBtn) {
      voiceBtn.className = 'action-btn processing';
      voiceBtn.title = 'Thinking...';
    }
    if (statusPill) statusPill.style.display = 'inline-flex';
    if (statusText) statusText.textContent = 'Thinking...';
    if (statusDot) statusDot.className = 'voice-status-dot processing';
    // Watchdog for network/LLM hangs
    voiceWatchdog = setTimeout(() => {
      if (voiceState === 'PROCESSING') {
        console.warn('Voice processing watchdog triggered');
        setVoiceState('IDLE');
      }
    }, 15000);
  } else if (state === 'SPEAKING') {
    if (voiceBtn) {
      voiceBtn.className = 'action-btn speaking';
      voiceBtn.title = 'Speaking...';
    }
    if (statusPill) statusPill.style.display = 'inline-flex';
    if (statusText) statusText.textContent = 'Speaking...';
    if (statusDot) statusDot.className = 'voice-status-dot speaking';
    // Watchdog for audio playback hangs
    voiceWatchdog = setTimeout(() => {
      if (voiceState === 'SPEAKING') {
        console.warn('Voice playback watchdog triggered - recovering to IDLE');
        stopAllAudioPlayback();
        setVoiceState('IDLE');
        if (isLiveMode && !isStreamActive) {
          setTimeout(startListening, 500);
        }
      }
    }, 20000);
  } else {
    // IDLE
    if (voiceBtn) {
      voiceBtn.className = 'action-btn';
      voiceBtn.title = 'Voice Input';
    }
    if (statusPill) statusPill.style.display = 'none';
  }
}

class AudioQueue {
  constructor() {
    this.queue = [];
    this.isPlaying = false;
    this.currentAudio = null;
    this.onEndAll = null;
    this.prefetchedAudios = new Map();
    this.lastQueuedText = '';
    this.lastQueuedTime = 0;
    this.playTimeout = null;
    this.activeUtterance = null;
  }

  getRateParam() {
    const raw = parseFloat(document.getElementById('speechRateSelect')?.value || '1.0');
    const pct = Math.round((raw - 1.0) * 100);
    return `${pct >= 0 ? '+' : ''}${pct}%`;
  }

  prefetch(item) {
    if (!item || !item.text) return;
    const key = `${item.text}_${item.langCode}_${item.rate}`;
    if (this.prefetchedAudios.has(key)) return;

    const safeLang = (item.langCode || 'en').toLowerCase().startsWith('te') ? 'te' : 'en';
    const audio = new Audio(`/tts?text=${encodeURIComponent(item.text)}&lang=${safeLang}&rate=${encodeURIComponent(item.rate)}`);
    audio.preload = 'auto';
    audio.onerror = () => {};
    this.prefetchedAudios.set(key, audio);
  }

  add(text, langCode, isExplicitClick = false) {
    const clean = cleanTextForSpeech(text);
    if (!clean) return;

    // Prevent duplicate consecutive utterances queued within rapid succession (< 2s) unless explicitly clicked
    if (!isExplicitClick && this.lastQueuedText === clean && (Date.now() - this.lastQueuedTime < 2000)) {
      console.warn("Skipping duplicate queued utterance:", clean);
      return;
    }
    this.lastQueuedText = clean;
    this.lastQueuedTime = Date.now();

    // Ensure active mic recognition is paused so it does not hear the speaker!
    if (recognition) {
      try { recognition.abort(); } catch(e) {}
      recognition = null;
    }

    const rate = this.getRateParam();
    const safeLang = (langCode || langConfig[currentLang]?.ttsLang || 'en').toLowerCase().startsWith('te') ? 'te' : 'en';
    const item = { text: clean, langCode: safeLang, rate };
    this.queue.push(item);

    // Pre-fetch this item immediately
    this.prefetch(item);

    if (!this.isPlaying) {
      this.playNext();
    }
  }

  async playNext() {
    if (this.playTimeout) {
      clearTimeout(this.playTimeout);
      this.playTimeout = null;
    }

    if (!this.isPlaying && this.queue.length > 0) {
      this.isPlaying = true;
    }

    if (this.queue.length === 0) {
      this.isPlaying = false;
      this.currentAudio = null;
      this.activeUtterance = null;
      window._activeSpeechUtter = null;
      document.querySelectorAll('.msg-action-btn.speaking').forEach(b => {
        b.classList.remove('speaking');
        b.setAttribute('data-tooltip', 'Read aloud');
      });
      if (this.onEndAll && !isStreamActive) {
        this.onEndAll();
      } else if (!isStreamActive) {
        setVoiceState('IDLE');
        if (isLiveMode) {
          setTimeout(startListening, 500);
        }
      }
      return;
    }

    this.isPlaying = true;
    setVoiceState('SPEAKING');

    // Ensure mic is definitely stopped while audio plays
    if (recognition) {
      try { recognition.abort(); } catch(e) {}
      recognition = null;
    }

    const item = this.queue.shift();
    const key = `${item.text}_${item.langCode}_${item.rate}`;

    // Pre-fetch the next item in line so it is immediately buffered with 0ms gap
    if (this.queue.length > 0) {
      this.prefetch(this.queue[0]);
    }

    let audio = this.prefetchedAudios.get(key);
    this.prefetchedAudios.delete(key);

    const safeLang = (item.langCode || 'en').toLowerCase().startsWith('te') ? 'te' : 'en';
    if (!audio) {
      audio = new Audio(`/tts?text=${encodeURIComponent(item.text)}&lang=${safeLang}&rate=${encodeURIComponent(item.rate)}`);
    }

    this.currentAudio = audio;

    let advanced = false;
    let fallbackAttempted = false;

    const advance = () => {
      if (advanced) return;
      advanced = true;
      if (this.playTimeout) {
        clearTimeout(this.playTimeout);
        this.playTimeout = null;
      }
      this.activeUtterance = null;
      window._activeSpeechUtter = null;
      if (!this.isPlaying) return; // Prevent advancing if stopped
      if (this.currentAudio === audio) {
        this.currentAudio = null;
      }
      this.playNext();
    };

    // Safety watchdog per chunk (max 25s or proportional to length)
    const maxDurationMs = Math.max(5000, Math.min(25000, (item.text.length / 8) * 1000 + 4000));
    this.playTimeout = setTimeout(() => {
      console.warn("Audio item playback timed out, advancing queue:", item.text.substring(0, 30));
      advance();
    }, maxDurationMs);

    const runFallback = (reason) => {
      if (fallbackAttempted || advanced) return;
      fallbackAttempted = true;
      if (!this.isPlaying) return; // Prevent fallback if stopped
      console.warn(`TTS audio fallback triggered (${reason}) for:`, item.text);
      if ('speechSynthesis' in window) {
        try {
          window.speechSynthesis.cancel();
          window.speechSynthesis.resume();
          const utter = new SpeechSynthesisUtterance(item.text);
          this.activeUtterance = utter;
          window._activeSpeechUtter = utter; // Retain globally to prevent Chromium GC bug
          utter.lang = safeLang === 'te' ? 'te-IN' : 'en-US';
          utter.rate = parseFloat(document.getElementById('speechRateSelect')?.value || '1.0');
          utter.onend = () => {
            this.activeUtterance = null;
            window._activeSpeechUtter = null;
            advance();
          };
          utter.onerror = (err) => {
            console.warn("SpeechSynthesis error:", err);
            this.activeUtterance = null;
            window._activeSpeechUtter = null;
            advance();
          };
          window.speechSynthesis.speak(utter);
          return;
        } catch (synthErr) {
          console.warn("SpeechSynthesis error:", synthErr);
        }
      }
      advance();
    };

    audio.onended = advance;
    audio.onerror = () => runFallback('onerror');

    try {
      unlockAudioPlayback();
      await audio.play();
    } catch (playErr) {
      if (!this.isPlaying) return;
      runFallback('playErr');
    }
  }

  stop() {
    if (this.playTimeout) {
      clearTimeout(this.playTimeout);
      this.playTimeout = null;
    }
    this.queue = [];
    this.prefetchedAudios.clear();
    this.lastQueuedText = '';
    this.lastQueuedTime = 0;
    this.isPlaying = false;
    this.activeUtterance = null;
    window._activeSpeechUtter = null;
    if (this.currentAudio) {
      try {
        this.currentAudio.onended = null;
        this.currentAudio.onerror = null;
        this.currentAudio.pause();
        this.currentAudio.currentTime = 0;
      } catch(e) {}
      this.currentAudio = null;
    }
    if (activeAudio) {
      try {
        activeAudio.onended = null;
        activeAudio.onerror = null;
        activeAudio.pause();
        activeAudio.currentTime = 0;
      } catch(e) {}
      activeAudio = null;
    }
    if ('speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
      } catch(e) {}
    }
    isSpeaking = false;
    document.querySelectorAll('.msg-action-btn.speaking').forEach(b => {
      b.classList.remove('speaking');
      b.setAttribute('data-tooltip', 'Read aloud');
    });
    setVoiceState('IDLE');
  }
}

const voiceQueue = new AudioQueue();
voiceQueue.onEndAll = () => {
  document.querySelectorAll('.msg-action-btn.speaking').forEach(b => {
    b.classList.remove('speaking');
    b.setAttribute('data-tooltip', 'Read aloud');
  });
  setVoiceState('IDLE');
  if (isLiveMode && !isStreamActive) {
    setTimeout(startListening, 500);
  }
};
// ──────────────────────────────────────────────────────────────────────────


function cleanTextForSpeech(text) {
  if (!text) return '';
  return text
    .replace(/\*\*Sources:\*\*[\s\S]*$/i, '')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/\|[ \-\:]+\|/g, ' ')
    .replace(/\|/g, ' ')
    .replace(/[*_~`#>\-•✦■◆]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

async function playTtsFallback(text, langCode = 'en-IN') {
  const safeLang = (langCode || 'en').toLowerCase().startsWith('te') ? 'te' : 'en';
  const clean = cleanTextForSpeech(text);
  if (!clean) return;
  if (recognition) {
    try { recognition.abort(); } catch(e) {}
    recognition = null;
  }
  unlockAudioPlayback();
  try {
    if (activeAudio) {
      activeAudio.onended = null;
      activeAudio.onerror = null;
      activeAudio.pause();
      activeAudio.currentTime = 0;
    }
    isSpeaking = true;
    setVoiceState('SPEAKING');
    activeAudio = new Audio(`/tts?text=${encodeURIComponent(clean)}&lang=${safeLang}`);
    activeAudio.onended = () => {
      isSpeaking = false;
      document.querySelectorAll('.msg-action-btn.speaking').forEach(b => {
        b.classList.remove('speaking');
        b.setAttribute('data-tooltip', 'Read aloud');
      });
      setVoiceState('IDLE');
      if (isLiveMode && !isStreamActive) setTimeout(startListening, 500);
    };
    activeAudio.onerror = () => {
      isSpeaking = false;
      document.querySelectorAll('.msg-action-btn.speaking').forEach(b => {
        b.classList.remove('speaking');
        b.setAttribute('data-tooltip', 'Read aloud');
      });
      setVoiceState('IDLE');
      if (isLiveMode && !isStreamActive) setTimeout(startListening, 500);
    };
    await activeAudio.play();
  } catch (error) {
    isSpeaking = false;
    document.querySelectorAll('.msg-action-btn.speaking').forEach(b => {
      b.classList.remove('speaking');
      b.setAttribute('data-tooltip', 'Read aloud');
    });
    setVoiceState('IDLE');
    if (isLiveMode && !isStreamActive) setTimeout(startListening, 500);
    console.warn('Fallback TTS playback failed:', error);
  }
}

// ── Choose Your Vibe (Theme System) ──────────────────────────
const VIBES = {
  lovers: {
    name: 'Lovers',
    gradient: 'linear-gradient(135deg, #f43f5e, #fda4af)',
    primary: '#f43f5e',
    secondary: '#fb7185',
    userBubble: '#4c0519',
    glow: '0 0 16px rgba(244, 63, 94, 0.45)',
    bgGradient: 'radial-gradient(circle at top center, rgba(244, 63, 94, 0.18) 0%, rgba(5, 5, 5, 1) 60%)',
    panelBorder: 'rgba(244, 63, 94, 0.3)'
  },
  friendship: {
    name: 'Friendship',
    gradient: 'linear-gradient(135deg, #f97316, #fb923c)',
    primary: '#f97316',
    secondary: '#ea580c',
    userBubble: '#431407',
    glow: '0 0 16px rgba(249, 115, 22, 0.45)',
    bgGradient: 'radial-gradient(circle at top center, rgba(249, 115, 22, 0.18) 0%, rgba(5, 5, 5, 1) 60%)',
    panelBorder: 'rgba(249, 115, 22, 0.3)'
  },
  chill: {
    name: 'Chill',
    gradient: 'linear-gradient(135deg, #0284c7, #38bdf8)',
    primary: '#0ea5e9',
    secondary: '#0284c7',
    userBubble: '#082f49',
    glow: '0 0 16px rgba(14, 165, 233, 0.45)',
    bgGradient: 'radial-gradient(circle at top center, rgba(14, 165, 233, 0.18) 0%, rgba(5, 5, 5, 1) 60%)',
    panelBorder: 'rgba(14, 165, 233, 0.3)'
  },
  derry: {
    name: 'Derry',
    gradient: 'linear-gradient(135deg, #7c3aed, #a855f7)',
    primary: '#a855f7',
    secondary: '#7c3aed',
    userBubble: '#2e1065',
    glow: '0 0 16px rgba(168, 85, 247, 0.45)',
    bgGradient: 'radial-gradient(circle at top center, rgba(168, 85, 247, 0.18) 0%, rgba(5, 5, 5, 1) 60%)',
    panelBorder: 'rgba(168, 85, 247, 0.3)'
  },
  tron: {
    name: 'Tron',
    gradient: 'linear-gradient(135deg, #00f2fe, #4facfe)',
    primary: '#00f2fe',
    secondary: '#0284c7',
    userBubble: '#042f2e',
    glow: '0 0 18px rgba(0, 242, 254, 0.5)',
    bgGradient: 'radial-gradient(circle at top center, rgba(0, 242, 254, 0.18) 0%, rgba(5, 5, 5, 1) 60%)',
    panelBorder: 'rgba(0, 242, 254, 0.35)'
  },
  taylorshift: {
    name: 'Taylorshift',
    gradient: 'linear-gradient(135deg, #e11d48, #ec4899)',
    primary: '#ec4899',
    secondary: '#db2777',
    userBubble: '#500724',
    glow: '0 0 16px rgba(236, 72, 153, 0.45)',
    bgGradient: 'radial-gradient(circle at top center, rgba(236, 72, 153, 0.18) 0%, rgba(5, 5, 5, 1) 60%)',
    panelBorder: 'rgba(236, 72, 153, 0.3)'
  },
  sunset: {
    name: 'Sunset',
    gradient: 'linear-gradient(135deg, #fb923c, #f43f5e)',
    primary: '#fb923c',
    secondary: '#f43f5e',
    userBubble: '#451a03',
    glow: '0 0 16px rgba(251, 146, 60, 0.45)',
    bgGradient: 'radial-gradient(circle at top center, rgba(251, 146, 60, 0.18) 0%, rgba(5, 5, 5, 1) 60%)',
    panelBorder: 'rgba(251, 146, 60, 0.3)'
  },
  forest: {
    name: 'Forest',
    gradient: 'linear-gradient(135deg, #10b981, #0f766e)',
    primary: '#10b981',
    secondary: '#059669',
    userBubble: '#064e3b',
    glow: '0 0 16px rgba(168, 185, 129, 0.45)',
    bgGradient: 'radial-gradient(circle at top center, rgba(16, 185, 129, 0.18) 0%, rgba(5, 5, 5, 1) 60%)',
    panelBorder: 'rgba(16, 185, 129, 0.3)'
  },
  shadow: {
    name: 'Shadow',
    gradient: 'linear-gradient(135deg, #ff0055, #cc0044)',
    primary: '#ff0055',
    secondary: '#cc0044',
    userBubble: '#4d001a',
    glow: '0 0 16px rgba(255, 0, 85, 0.5)',
    bgGradient: 'radial-gradient(circle at top center, rgba(153, 0, 0, 0.15) 0%, rgba(5, 5, 5, 1) 60%)',
    panelBorder: 'rgba(255, 0, 85, 0.3)'
  },
  cyberpunk: {
    name: 'Cyberpunk',
    gradient: 'linear-gradient(135deg, #facc15, #f59e0b)',
    primary: '#facc15',
    secondary: '#eab308',
    userBubble: '#422006',
    glow: '0 0 16px rgba(250, 204, 21, 0.45)',
    bgGradient: 'radial-gradient(circle at top center, rgba(250, 204, 21, 0.14) 0%, rgba(5, 5, 5, 1) 60%)',
    panelBorder: 'rgba(250, 204, 21, 0.3)'
  }
};

let currentVibe = 'shadow';

function setVibe(key) {
  const vibe = VIBES[key] || VIBES['shadow'];
  currentVibe = key in VIBES ? key : 'shadow';
  const root = document.documentElement;

  root.style.setProperty('--accent-primary', vibe.primary);
  root.style.setProperty('--accent-secondary', vibe.secondary);
  root.style.setProperty('--accent-gradient', vibe.gradient);
  root.style.setProperty('--glow-shadow', vibe.glow);
  root.style.setProperty('--glow-text', `0 0 8px ${vibe.primary}99`);
  root.style.setProperty('--panel-border', vibe.panelBorder);
  root.style.setProperty('--user-bubble', vibe.userBubble);
  root.style.setProperty('--bg-gradient', vibe.bgGradient);
  if (document.body) {
    document.body.style.backgroundImage = vibe.bgGradient;
  }

  // Sync preview dots
  document.querySelectorAll('.vibe-preview-dot').forEach(dot => {
    dot.style.background = vibe.primary;
    dot.style.boxShadow = `0 0 8px ${vibe.primary}`;
  });

  const sidebarName = document.getElementById('sidebarVibeName');
  if (sidebarName) sidebarName.textContent = vibe.name;

  // Mark active in grid
  document.querySelectorAll('.vibe-card').forEach(c => {
    if (c.getAttribute('data-vibe') === currentVibe) {
      c.classList.add('active');
    } else {
      c.classList.remove('active');
    }
  });

  try {
    localStorage.setItem('mikey_vibe', currentVibe);
    localStorage.setItem('shadowcall_vibe', currentVibe);
  } catch (e) {}
}

function setTheme(theme) {
  // Legacy alias
  if (theme === 'violet') setVibe('derry');
  else if (theme === 'emerald') setVibe('forest');
  else if (theme === 'cyan') setVibe('tron');
  else setVibe(theme);
}

function renderVibeGrid() {
  const grid = document.getElementById('vibeGrid');
  if (!grid) return;
  grid.innerHTML = '';

  Object.entries(VIBES).forEach(([key, vibe]) => {
    const card = document.createElement('div');
    card.className = `vibe-card ${key === currentVibe ? 'active' : ''}`;
    card.setAttribute('data-vibe', key);
    card.onclick = () => {
      setVibe(key);
      if (typeof showFeedbackToast === 'function') {
        showFeedbackToast(`Vibe changed to ${vibe.name}`);
      }
    };

    card.innerHTML = `
      <div class="vibe-swatch" style="background: ${vibe.gradient};"></div>
      <div class="vibe-name">${vibe.name}</div>
    `;
    grid.appendChild(card);
  });
}

function openVibeModal() {
  const m = document.getElementById('vibeModal');
  if (m) {
    m.style.display = 'flex';
    renderVibeGrid();
  }
}

function closeVibeModal() {
  const m = document.getElementById('vibeModal');
  if (m) m.style.display = 'none';
}

window.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeVibeModal();
    if (typeof closeVisionKeyModal === 'function') closeVisionKeyModal();
  }
});

function exportChat() {
  if (!chatHistory.length) {
    alert("No active conversation to export.");
    return;
  }
  let mdContent = `# Mikey Conversation Export\n*Exported on ${new Date().toLocaleString()}*\n\n---\n\n`;
  chatHistory.forEach(m => {
    const sender = m.role === 'user' ? '👤 User' : '✦ Mikey';
    mdContent += `### ${sender}\n${m.content}\n\n`;
  });
  
  const blob = new Blob([mdContent], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `mikey_chat_${currentThreadId || 'export'}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

function speak(text, langCode = 'en-IN') {
  const clean = cleanTextForSpeech(text);
  if (!clean) return;

  if (!('speechSynthesis' in window)) {
    playTtsFallback(clean, langCode);
    return;
  }

  const synth = window.speechSynthesis;
  const voices = synth.getVoices();
  
  // Try to find a male English voice first, but ONLY if the current language is English
  let bestVoice = null;
  if (langCode.toLowerCase().startsWith('en')) {
    bestVoice = voices.find(v => v.lang.startsWith('en') && (
      v.name.includes('David') || 
      v.name.includes('Mark') || 
      v.name.includes('Guy') || 
      v.name.includes('George') || 
      v.name.toLowerCase().includes('male')
    ));
  }
  
  // If no explicit male voice is found, fall back to default logic
  const exact = voices.find(v => v.lang.toLowerCase() === langCode.toLowerCase());
  const languageMatch = voices.find(v => v.lang.toLowerCase().startsWith(langCode.split('-')[0].toLowerCase()));
  const fallbackEn = voices.find(v => v.lang.toLowerCase().startsWith('en'));

  if (!bestVoice && !exact && !languageMatch) {
    playTtsFallback(clean, langCode);
    return;
  }

  if (recognition) {
    try { recognition.abort(); } catch(e) {}
    recognition = null;
  }
  unlockAudioPlayback();
  synth.cancel();
  try { synth.resume(); } catch(e) {}
  const utter = new SpeechSynthesisUtterance(clean);
  window._activeSpeechUtter = utter;
  const rateVal = parseFloat(document.getElementById('speechRateSelect')?.value || '1.0');
  utter.rate = rateVal;
  utter.pitch = bestVoice ? 1.0 : 0.8; // Lower pitch if we couldn't guarantee a male voice
  utter.volume = 0.95;
  utter.voice = bestVoice || exact || languageMatch || fallbackEn;
  utter.lang = utter.voice ? utter.voice.lang : 'en-US';
  isSpeaking = true;
  setVoiceState('SPEAKING');
  utter.onend = () => {
    isSpeaking = false;
    window._activeSpeechUtter = null;
    document.querySelectorAll('.msg-action-btn.speaking').forEach(b => {
      b.classList.remove('speaking');
      b.setAttribute('data-tooltip', 'Read aloud');
    });
    setVoiceState('IDLE');
    if (isLiveMode && !isStreamActive) setTimeout(startListening, 500);
  };
  utter.onerror = () => {
    isSpeaking = false;
    window._activeSpeechUtter = null;
    document.querySelectorAll('.msg-action-btn.speaking').forEach(b => {
      b.classList.remove('speaking');
      b.setAttribute('data-tooltip', 'Read aloud');
    });
    setVoiceState('IDLE');
    if (isLiveMode && !isStreamActive) setTimeout(startListening, 500);
  };
  synth.speak(utter);
}

if ('speechSynthesis' in window) window.speechSynthesis.onvoiceschanged = () => { window.speechSynthesis.getVoices(); };

let recognition = null;
let isSpeaking = false;
let speechSilenceTimer = null;
let activeSpeechTranscript = '';
const SILENCE_DEBOUNCE_MS = 1300; // Natural 1.3s pause before concluding user finished speaking

function commitSpeechAndSend() {
  if (speechSilenceTimer) {
    clearTimeout(speechSilenceTimer);
    speechSilenceTimer = null;
  }

  const textToSend = activeSpeechTranscript.trim();
  activeSpeechTranscript = '';

  if (!textToSend) return;

  stopAllAudioPlayback();

  // Stop active recognition temporarily while AI processes & speaks
  if (recognition) {
    try { recognition.abort(); } catch(e) {}
    recognition = null;
  }

  setVoiceState('PROCESSING');
  const input = document.getElementById('chatInput');
  if (input) {
    input.value = textToSend;
    autoResizeChatInput();
  }
  sendMessage(textToSend);
}

function startListening() {
  if (!isLiveMode || isStreamActive || voiceQueue.isPlaying || isSpeaking) return;

  if (speechSilenceTimer) {
    clearTimeout(speechSilenceTimer);
    speechSilenceTimer = null;
  }
  activeSpeechTranscript = '';

  if (recognition) {
    try { recognition.abort(); } catch(e) {}
    recognition = null;
  }

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    console.warn("Speech recognition is not supported in this browser.");
    return;
  }

  recognition = new SR();
  recognition.lang = langConfig[currentLang]?.voiceCode || 'en-IN';
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;
  recognition.continuous = true; // Stay listening through natural pauses

  recognition.onstart = () => {
    setVoiceState('LISTENING');
  };

  // Barge-in: If user speaks, interrupt bot playback immediately
  recognition.onspeechstart = () => {
    if (voiceQueue.isPlaying || isStreamActive || isSpeaking) {
      stopAllAudioPlayback();
      if (chatAbortController) chatAbortController.abort();
      isStreamActive = false;
      setVoiceState('LISTENING');
    }
  };

  recognition.onresult = (e) => {
    let sessionInterim = '';
    let sessionFinal = '';

    for (let i = e.resultIndex; i < e.results.length; ++i) {
      const trans = e.results[i][0].transcript;
      if (e.results[i].isFinal) {
        sessionFinal += trans;
      } else {
        sessionInterim += trans;
      }
    }

    if (sessionFinal) {
      if (activeSpeechTranscript && !activeSpeechTranscript.endsWith(' ')) {
        activeSpeechTranscript += ' ';
      }
      activeSpeechTranscript += sessionFinal.trim();
    }

    const currentDisplay = (activeSpeechTranscript + ' ' + sessionInterim).trim();
    const input = document.getElementById('chatInput');
    if (input && currentDisplay) {
      input.value = currentDisplay;
      autoResizeChatInput();
    }

    // Reset silence debounce timer
    if (speechSilenceTimer) {
      clearTimeout(speechSilenceTimer);
      speechSilenceTimer = null;
    }

    if (currentDisplay) {
      speechSilenceTimer = setTimeout(() => {
        if (sessionInterim.trim()) {
          if (activeSpeechTranscript && !activeSpeechTranscript.endsWith(' ')) {
            activeSpeechTranscript += ' ';
          }
          activeSpeechTranscript += sessionInterim.trim();
        }
        commitSpeechAndSend();
      }, SILENCE_DEBOUNCE_MS);
    }
  };

  recognition.onerror = (e) => {
    console.warn("Mic error:", e.error);
    if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
      isLiveMode = false;
      if (speechSilenceTimer) clearTimeout(speechSilenceTimer);
      activeSpeechTranscript = '';
      setVoiceState('IDLE');
      appendMsg('bot', 'Microphone permission was denied. Please allow microphone access in your browser.', '🤖');
    }
  };

  recognition.onend = () => {
    recognition = null;
    // If the browser closed recognition while we have uncommitted words, commit and send them now
    if (activeSpeechTranscript.trim()) {
      commitSpeechAndSend();
      return;
    }

    // Only restart if still in LISTENING state and not busy processing or speaking
    if (isLiveMode && voiceState === 'LISTENING' && !isStreamActive && !voiceQueue.isPlaying && !isSpeaking) {
      setTimeout(startListening, 400);
    } else if (!isLiveMode && voiceState === 'LISTENING') {
      setVoiceState('IDLE');
    }
  };

  try {
    recognition.start();
  } catch (e) {
    console.error("Speech recognition start error:", e);
    setVoiceState('IDLE');
  }
}

function toggleVoice() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    appendMsg('bot', 'Voice input is not supported in this browser. Please use Chrome or Edge.', '✦');
    return;
  }

  unlockAudioPlayback();

  if (isLiveMode) {
    isLiveMode = false;
    if (speechSilenceTimer) {
      clearTimeout(speechSilenceTimer);
      speechSilenceTimer = null;
    }
    activeSpeechTranscript = '';
    stopAllAudioPlayback();
    if (recognition) {
      try { recognition.abort(); } catch(e) {}
      recognition = null;
    }
    setVoiceState('IDLE');
    appendMsg('bot', 'Live Talk Mode disabled.', '✦');
    chatHistory.push({ role: 'assistant', content: 'Live Talk Mode disabled.' });
    saveCurrentThread();
    return;
  }

  stopAllAudioPlayback();
  isLiveMode = true;
  appendMsg('bot', 'Live Talk Mode activated. Listening continuously...', '✦');
  chatHistory.push({ role: 'assistant', content: 'Live Talk Mode activated. Listening continuously...' });
  saveCurrentThread();
  startListening();
}

async function loadAccount() {
  try {
    const res = await fetch('/me');
    if (!res.ok) {
      loadLocalThreads();
      if (!currentThreadId) newChat();
      return;
    }
    const data = await res.json();
    const badge = document.getElementById('accountBadge');
    if (badge) badge.textContent = data.username || 'User';
    
    if (data.username) {
      currentUsername = data.username;
      threads = [];
      chatHistory = [];
      loadLocalThreads();
    }
    
    const avatarImg = new Image();
    avatarImg.onload = function() {
      const btn = document.getElementById('headerProfileBtn');
      if (btn) btn.innerHTML = `<img src="${this.src}" style="width:100%; height:100%; object-fit:cover;">`;
    };
    avatarImg.src = `/static/avatars/${data.username}.jpg?v=${Date.now()}`;
    
    if (data.preferences?.lang) {
      currentLang = data.preferences.lang;
      setLang(currentLang);
    }
    loadServerThreads();
    listUserDocuments();
    if (!currentThreadId) newChat();
  } catch (e) {
    console.warn('Account load skipped', e);
    loadLocalThreads();
    if (!currentThreadId) newChat();
  }
}

async function loadServerThreads() {
  try {
    const res = await fetch('/api/threads');
    if (!res.ok) return;
    const data = await res.json();
    if (data.threads && data.threads.length) {
      data.threads.forEach(st => {
        const existing = threads.find(t => t.id === st.id);
        if (existing) {
          existing.title = st.title;
        } else {
          threads.push({
            id: st.id,
            title: st.title,
            updated_at: new Date(st.updated_at).getTime() || Date.now(),
            created_at: new Date(st.created_at).getTime() || Date.now(),
            messages: []
          });
        }
      });
      saveLocalThreads();
      renderHistory();
    }
  } catch (e) {
    console.warn("Server threads load failed", e);
  }
}

async function selectThread(id) {
  currentThreadId = id;
  let th = threads.find(t => t.id === id);
  if (th) {
    if (!th.messages || th.messages.length === 0) {
      try {
        const res = await fetch(`/api/threads/${id}`);
        if (res.ok) {
          const data = await res.json();
          if (data.messages && data.messages.length) {
            th.messages = data.messages.map(m => ({ role: m.role, content: m.content, image_url: m.image_url }));
          }
        }
      } catch (e) {
        console.warn("Failed to load thread messages from server", e);
      }
    }
    chatHistory = th.messages || [];
    renderMessages();
    renderHistory();
  }
}

async function saveCurrentThread() {
  if (!currentThreadId) return;
  let th = threads.find(t => t.id === currentThreadId);
  let isNew = false;
  if (!th) {
    isNew = true;
    th = {
      id: currentThreadId,
      title: 'New Conversation',
      created_at: Date.now(),
      updated_at: Date.now(),
      messages: []
    };
    threads.push(th);
  }
  th.updated_at = Date.now();
  th.messages = [...chatHistory];
  
  if (th.title === 'New Conversation' && th.messages.some(m => m.role === 'user')) {
    const firstMsg = th.messages.find(m => m.role === 'user').content;
    const words = (firstMsg || '').split(' ').slice(0, 5).join(' ');
    th.title = words.length > 0 ? words : 'Image Analysis';
    isNew = true;
  }
  
  saveLocalThreads();
  renderHistory();

  if (isNew) {
    try {
      await fetch('/api/threads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: th.id, title: th.title })
      });
    } catch(e) { }
  }
}

async function loadAdminStats() {
  try {
    const res = await fetch('/admin/stats');
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById('adminStats').innerHTML = `
      <div class="info-item"><span>Registered Users</span><strong>${data.user_count}</strong></div>
      <div class="info-item"><span>Total Convos</span><strong>${data.conversation_count}</strong></div>
      <div class="info-item"><span>Active Directives</span><strong>${data.reminder_count}</strong></div>
    `;
  } catch (e) {
    console.warn('Admin stats load skipped', e);
  }
}

async function listUserDocuments() {
  try {
    const res = await fetch('/documents');
    if (!res.ok) return;
    const data = await res.json();
    const list = document.getElementById('documentList');
    if (!list) return;
    if (!data.documents || !data.documents.length) {
      list.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem;">No documents uploaded.</div>';
      return;
    }
    list.innerHTML = data.documents.map(d => `
      <div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:10px; padding:8px 12px; display:flex; justify-content:space-between; align-items:center;">
        <div style="overflow:hidden; flex:1;">
          <div style="color:var(--text-main); font-size:0.85rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">📄 ${d.filename}</div>
          <div style="color:var(--text-muted); font-size:0.75rem;">${d.char_count} chars</div>
        </div>
        <button onclick="deleteUserDocument(${d.id})" style="background:transparent; border:none; color:var(--text-muted); cursor:pointer; font-size:0.85rem; padding:4px;" title="Delete Document">🗑️</button>
      </div>
    `).join('');
  } catch (e) {
    console.warn("Document list load failed", e);
  }
}

async function deleteUserDocument(docId) {
  if (!confirm("Remove this document from knowledge base?")) return;
  try {
    const res = await fetch(`/documents/${docId}`, { method: 'DELETE' });
    if (res.ok) {
      listUserDocuments();
      loadAdminStats();
    }
  } catch (e) {
    console.warn("Delete document failed", e);
  }
}

async function uploadDocument() {
  const fileInput = document.getElementById('docUpload');
  const file = fileInput.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  try {
    const res = await fetch('/upload', { method: 'POST', body: formData });
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch(err) { data = { detail: text || "Server Error" }; }
    if (res.ok) {
      document.getElementById('knowledgeOutput').textContent = data.message || 'Upload complete.';
      document.getElementById('knowledgeOutput').style.color = '#34d399';
      fileInput.value = '';
      listUserDocuments();
      loadAdminStats();
      if (!currentThreadId) newChat();
      appendMsg('bot', `Document uploaded successfully. Type /analyze to analyze it.`, '✦');
      chatHistory.push({ role: 'assistant', content: `Document uploaded successfully. Type /analyze to analyze it.` });
      saveCurrentThread();
    } else {
      document.getElementById('knowledgeOutput').textContent = data.detail || 'Upload failed.';
      document.getElementById('knowledgeOutput').style.color = '#ef4444';
      if (!currentThreadId) newChat();
      appendMsg('bot', `Document upload failed: ${data.detail || 'Upload failed.'}`, '✦');
      chatHistory.push({ role: 'assistant', content: `Document upload failed: ${data.detail || 'Upload failed.'}` });
      saveCurrentThread();
    }
  } catch (e) {
    document.getElementById('knowledgeOutput').textContent = 'Network error during upload.';
    document.getElementById('knowledgeOutput').style.color = '#ef4444';
    if (!currentThreadId) newChat();
    appendMsg('bot', `Document upload failed.`, '✦');
    chatHistory.push({ role: 'assistant', content: `Document upload failed.` });
    saveCurrentThread();
  }
}

async function analyzeDocument() {
  const output = document.getElementById('knowledgeOutput');
  output.textContent = 'Analyzing documents... Please wait.';
  output.style.color = 'var(--text-muted)';
  
  if (!currentThreadId) newChat();
  const tId = appendTyping();
  
  try {
    const res = await fetch('/analyze-documents', { method: 'POST' });
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch(err) { data = { detail: text || "Server Error" }; }
    
    document.getElementById(tId)?.remove();
    
    if (res.ok) {
      output.textContent = 'Analysis complete. Results sent to chat.';
      output.style.color = '#34d399';
      
      const analysisText = `**Document Analysis:**\n\n${data.analysis}`;
      
      if (!currentThreadId) newChat();
      appendMsg('bot', analysisText, '✦');
      chatHistory.push({ role: 'assistant', content: analysisText });
      saveCurrentThread();
      
      // Optionally speak the first part of it
      if (document.getElementById('ttsToggle')?.checked) {
        speak("Analysis complete. The results are in the chat.", langConfig[currentLang].ttsLang);
      }
    } else {
      output.textContent = data.detail || 'Analysis failed.';
      output.style.color = '#ef4444';
    }
  } catch (e) {
    output.textContent = 'Error: ' + (e.message || 'Unknown network error');
    output.style.color = '#ef4444';
    console.error(e);
  }
}

async function listReminders() {
  try {
    const res = await fetch('/reminders');
    if (!res.ok) return;
    const data = await res.json();
    const list = document.getElementById('reminderList');
    if (!data.reminders?.length) {
      list.innerHTML = '<div style="color:var(--text-muted); font-size:0.9rem;">No active directives.</div>';
      return;
    }
    list.innerHTML = data.reminders.map(rem => `
      <div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:12px; padding:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:var(--text-main); font-size:0.95rem;">${rem.title}</strong>
          ${rem.completed ? '<span style="color:#34d399; font-size:0.8rem; font-weight:600;">COMPLETED</span>' : `<button onclick="completeReminder(${rem.id})" style="background:var(--accent-gradient); border:none; color:#fff; border-radius:6px; padding:4px 8px; font-size:0.8rem; cursor:pointer;">MARK DONE</button>`}
        </div>
        <div style="color:var(--text-muted); font-size:0.8rem; margin-top:4px;">${rem.scheduled_at.replace('T', ' ')}</div>
      </div>
    `).join('');
  } catch (e) {
    console.warn('Reminder load failed', e);
  }
}

async function createReminder() {
  const title = document.getElementById('reminderTitle').value.trim();
  const scheduledAt = document.getElementById('reminderTime').value;
  const description = document.getElementById('reminderDescription').value.trim();
  if (!title || !scheduledAt) return;
  const res = await fetch('/reminders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, scheduled_at: scheduledAt, description })
  });
  const data = await res.json();
  document.getElementById('reminderStatus').textContent = data.message || 'Directive logged.';
  document.getElementById('reminderTitle').value = '';
  document.getElementById('reminderTime').value = '';
  document.getElementById('reminderDescription').value = '';
  await listReminders();
  if (res.ok) {
    await fetch('/analytics/event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event_type: 'reminder_created', metadata: title })
    });
    await loadAdminStats();
    await loadAnalytics();
  }
}

async function completeReminder(id) {
  const res = await fetch(`/reminders/${id}/complete`, { method: 'POST' });
  const data = await res.json();
  document.getElementById('reminderStatus').textContent = data.message || 'Directive updated.';
  await listReminders();
  await loadAdminStats();
  await loadAnalytics();
}

async function loadAnalytics() {
  try {
    const res = await fetch('/admin/analytics');
    if (!res.ok) return;
    const data = await res.json();
    const list = document.getElementById('analyticsList');
    if (!data.analytics?.length) {
      list.innerHTML = '<div style="color:var(--text-muted); font-size:0.9rem;">Stream idle.</div>';
      return;
    }
    list.innerHTML = data.analytics.map(item => `
      <div class="info-item">
        <span>${item.event_type}</span>
        <strong>${item.count}</strong>
      </div>
    `).join('');
  } catch (e) {
    console.warn('Analytics load failed', e);
  }
}

async function signup() {
  const username = document.getElementById('usernameInput').value.trim();
  const password = document.getElementById('passwordInput').value;
  if (!username || !password) return;
  const res = await fetch('/signup', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
  const data = await res.json();
  if (res.ok) {
    document.getElementById('accountBadge').textContent = username;
    appendMsg('bot', `Operator ${username} registered successfully.`, '✦');
  } else {
    appendMsg('bot', data.detail || 'Registration failed.', '✦');
  }
}

async function login() {
  const username = document.getElementById('usernameInput').value.trim();
  const password = document.getElementById('passwordInput').value;
  if (!username || !password) return;
  const res = await fetch('/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
  const data = await res.json();
  if (res.ok) {
    document.getElementById('accountBadge').textContent = username;
    appendMsg('bot', `Authentication successful. Welcome back, ${username}.`, '✦');
  } else {
    appendMsg('bot', data.detail || 'Authentication failed.', '✦');
  }
}

async function logout() {
  await fetch('/logout', { method: 'POST' });
  document.getElementById('accountBadge').textContent = 'Guest';
  currentUsername = 'Guest';
  threads = [];
  chatHistory = [];
  currentThreadId = null;
  renderMessages();
  renderHistory();
  appendMsg('bot', 'Operator disconnected. Reverting to Guest mode.', '✦');
}

async function savePreferences() {
  try {
    await fetch('/preferences', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ lang: currentLang, tts_enabled: document.getElementById('ttsToggle')?.checked, voice_input_enabled: true }) });
  } catch (e) {
    console.warn('Preference save failed', e);
  }
}



// Initialization
renderMessages();
setLang('en');
setVibe(localStorage.getItem('mikey_vibe') || localStorage.getItem('shadowcall_vibe') || 'shadow');
loadAccount();
loadAdminStats();
listReminders();
loadAnalytics();

// --- History & Image Logic ---
let currentUsername = 'Guest';
let currentThreadId = null;
let threads = [];
let pendingImageFile = null;
let pendingImageUrl = null; // if using dataURL for local preview

function generateId() { return Math.random().toString(36).substring(2, 15); }

function loadLocalThreads() {
  localStorage.removeItem('shadowcall_threads'); // Clean up old un-scoped storage
  localStorage.removeItem('mikey_threads');
  const user = currentUsername || 'Guest';
  const key = 'mikey_threads_' + user;
  const legacyKey = 'shadowcall_threads_' + user;
  let stored = localStorage.getItem(key) || localStorage.getItem(legacyKey);
  if (stored) threads = JSON.parse(stored);
  else threads = [];
  renderHistory();
}

function saveLocalThreads() {
  try {
    const key = 'mikey_threads_' + (currentUsername || 'Guest');
    // Make a safe copy of threads where massive data URIs are stripped out for local storage
    const safeThreads = threads.map(th => ({
      ...th,
      messages: (th.messages || []).map(m => {
        if (m.image_url && m.image_url.startsWith('data:image')) {
           return { ...m, image_url: null, content: '[Image] ' + (m.content || '') };
        }
        return m;
      })
    }));
    localStorage.setItem(key, JSON.stringify(safeThreads));
  } catch (err) {
    console.warn("Could not save to localStorage (Quota Exceeded?)", err);
  }
}

function newChat() {
  currentThreadId = generateId();
  chatHistory = [];
  renderMessages();
  renderHistory();
  document.getElementById('chatInput').focus();
}

function selectThread(id) {
  currentThreadId = id;
  const th = threads.find(t => t.id === id);
  if (th) {
    chatHistory = th.messages || [];
    renderMessages();
    renderHistory();
  }
}

function renderHistory() {
  const list = document.getElementById('threadList');
  if (!list) return;
  list.innerHTML = '';
  const searchInput = document.getElementById('historySearch');
  const search = searchInput ? searchInput.value.toLowerCase() : '';
  
  // Sort threads by updated_at descending
  let displayThreads = [...threads].sort((a,b) => b.updated_at - a.updated_at);
  if (search) {
    displayThreads = displayThreads.filter(t => t.title.toLowerCase().includes(search) || (t.messages && t.messages.some(m => m.content.toLowerCase().includes(search))));
  }
  
  if (displayThreads.length === 0) {
    list.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem; text-align:center; padding:16px;">No conversations found.</div>';
    return;
  }
  
  displayThreads.forEach(th => {
    const div = document.createElement('div');
    div.className = `thread-item ${th.id === currentThreadId ? 'active' : ''}`;
    div.onclick = () => selectThread(th.id);
    
    // time formatter
    const now = Date.now();
    const diff = now - th.updated_at;
    let timeStr = 'Just now';
    if (diff > 86400000) timeStr = new Date(th.updated_at).toLocaleDateString();
    else if (diff > 3600000) timeStr = Math.floor(diff/3600000) + ' hrs ago';
    else if (diff > 60000) timeStr = Math.floor(diff/60000) + ' min ago';
    
    const safeTitle = (th.title || 'Conversation').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    div.innerHTML = `
      <div class="thread-info">
        <div class="thread-title">✦ ${safeTitle}</div>
        <div class="thread-time">${timeStr}</div>
      </div>
      <button class="delete-thread-btn" onclick="deleteSingleThread(event, '${th.id}')" title="Delete conversation">🗑️</button>
    `;
    list.appendChild(div);
  });
}

async function deleteSingleThread(event, threadId) {
  event.stopPropagation();
  if (!confirm("Are you sure you want to delete this conversation?")) return;
  
  threads = threads.filter(t => t.id !== threadId);
  saveLocalThreads();
  
  try {
    await fetch(`/api/threads/${threadId}`, { method: 'DELETE' });
  } catch (err) {
    console.warn("Server thread deletion failed", err);
  }
  
  if (currentThreadId === threadId) {
    newChat();
  } else {
    renderHistory();
  }
}

async function clearAllHistory() {
  if (!confirm("Are you sure you want to clear all conversation history?")) return;
  threads = [];
  saveLocalThreads();
  
  try {
    await fetch('/api/clear-history', { method: 'DELETE' });
  } catch (err) {
    console.warn("Server clear history failed", err);
  }
  
  newChat();
}

function saveCurrentThread() {
  if (!currentThreadId) return;
  let th = threads.find(t => t.id === currentThreadId);
  if (!th) {
    th = {
      id: currentThreadId,
      title: 'New Conversation',
      created_at: Date.now(),
      updated_at: Date.now(),
      messages: []
    };
    threads.push(th);
  }
  th.updated_at = Date.now();
  th.messages = [...chatHistory];
  
  // Auto title if "New Conversation" and has user messages
  if (th.title === 'New Conversation' && th.messages.some(m => m.role === 'user')) {
    const firstMsg = th.messages.find(m => m.role === 'user').content;
    const words = firstMsg.split(' ').slice(0, 5).join(' ');
    th.title = words.length > 0 ? words : 'Image Analysis';
  }
  
  saveLocalThreads();
  renderHistory();
}

function handleImageSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  pendingImageFile = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    pendingImageUrl = e.target.result;
    document.getElementById('imgPreview').src = pendingImageUrl;
    document.getElementById('imgPreviewContainer').style.display = 'block';
  };
  reader.readAsDataURL(file);
  document.getElementById('imageUpload').value = ''; // reset
}

function removeImage() {
  pendingImageFile = null;
  pendingImageUrl = null;
  document.getElementById('imgPreviewContainer').style.display = 'none';
  document.getElementById('imgPreview').src = '';
}

let lastFailedMessage = '';

function retryLastMessage() {
  if (lastFailedMessage) {
    const textToRetry = lastFailedMessage;
    lastFailedMessage = '';
    const errCards = document.querySelectorAll('.msg.bot.error-msg');
    if (errCards.length) {
      errCards[errCards.length - 1].remove();
    }
    sendMessage(textToRetry);
  }
}

function appendConnectionError() {
  const box = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'msg bot error-msg';
  div.innerHTML = `
    <div class="avatar bot-av" style="color:#f87171;">⚠️</div>
    <div class="bubble bot-bubble conn-error-bubble">
      <div class="conn-error-header">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <span>Network Error: Could not connect to the server</span>
      </div>
      <p class="conn-error-desc">
        Mikey server is unreachable. Please verify that <code>start.bat</code> is running on port 8000.
      </p>
      <div class="conn-error-actions">
        <button class="conn-retry-btn" onclick="retryLastMessage()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10"></polyline>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
          </svg>
          Retry
        </button>
      </div>
    </div>
  `;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function autoResizeChatInput() {
  const input = document.getElementById('chatInput');
  if (!input) return;
  input.style.height = 'auto';
  const maxHeight = 160;
  const newHeight = Math.min(Math.max(input.scrollHeight, 36), maxHeight);
  input.style.height = newHeight + 'px';
  input.style.overflowY = input.scrollHeight > maxHeight ? 'auto' : 'hidden';
}

function handleChatKeyDown(event) {
  if (event.key === 'Enter') {
    if (event.shiftKey) {
      // Shift+Enter: allow default multiline break and auto-resize
      setTimeout(autoResizeChatInput, 0);
    } else {
      // Plain Enter: submit message without newline
      event.preventDefault();
      sendMessage();
    }
  }
}

// Unified sendMessage function
async function sendMessage(overrideText) {
  const input = document.getElementById('chatInput');
  const text = overrideText || input.value.trim();
  const hasImage = pendingImageFile !== null;
  
  if (!text && !hasImage) return;
  if (!overrideText) {
    input.value = '';
    autoResizeChatInput();
  }

  // Immediately stop any active or queued speech playback from prior chats
  stopAllAudioPlayback();

  if (speechSilenceTimer) {
    clearTimeout(speechSilenceTimer);
    speechSilenceTimer = null;
  }
  activeSpeechTranscript = '';
  
  const opened = openCommandTabs(text);
  if (opened) {
    appendMsg('bot', 'Executed external command. Host browser tab opened.', '✦');
    return;
  }
  
  const lowerText = text.toLowerCase();
  if (lowerText === '/analyze') {
    if (!overrideText) input.value = '';
    analyzeDocument();
    return;
  }
  
  if (lowerText === '/upload') {
    if (!overrideText) input.value = '';
    document.getElementById('docUpload').click();
    return;
  }
  
  if (lowerText === '/vibe' || lowerText === '/theme') {
    if (!overrideText) input.value = '';
    openVibeModal();
    return;
  }
  
  if (!currentThreadId) newChat();
  
  let uploadedImageUrl = null;
  let localImgDataUrl = pendingImageUrl;
  
  if (hasImage) {
    // We upload it to backend if we have one
    const formData = new FormData();
    formData.append('file', pendingImageFile);
    try {
      const res = await fetch('/upload-chat-image', { method: 'POST', body: formData });
      if (res.ok) {
        const d = await res.json();
        uploadedImageUrl = d.url;
      }
    } catch(e) { console.warn('Image upload failed, using local preview only'); }
    removeImage(); // clear preview
  }
  
  // Add to local history
  // If we are falling back to local base64, we don't want to save 5MB into localStorage.
  let historyImageUrl = uploadedImageUrl;
  if (!uploadedImageUrl && localImgDataUrl) {
    historyImageUrl = localImgDataUrl; // We will handle size limit in saveLocalThreads
  }
  
  const userMsgObj = { role: 'user', content: text, image_url: historyImageUrl };
  chatHistory.push(userMsgObj);
  appendMsg('user', text, '❖', uploadedImageUrl || localImgDataUrl);
  saveCurrentThread();
  
  const tId = appendTyping();
  
  // Sanitize history payload to prevent massive base64 strings or past refusal messages from repeating
    const cleanHistory = chatHistory.slice(0, -1)
      .filter(h => !h.content || !/text-based mode|cannot directly access|do not have the capability/i.test(h.content))
      .map(h => ({
        role: h.role,
        content: h.content,
        image_url: (h.image_url && h.image_url.startsWith('/uploads/')) ? h.image_url : null
      }));

    const payload = {
      message: text,
      history: cleanHistory,
      system_prompt: langConfig[currentLang].systemPrompt,
      thread_id: currentThreadId,
      persona: document.getElementById('personaSelect')?.value || 'executive',
      tone: document.getElementById('toneSelect')?.value || 'dynamic'
    };

    const imgUrlToSend = uploadedImageUrl || (localImgDataUrl && localImgDataUrl.length < 500000 ? localImgDataUrl : null);
    if (imgUrlToSend) {
      payload.image_url = imgUrlToSend;
    }
    
    // UI Feedback for latency
    const sendBtn = document.querySelector('.send-btn');
    if (sendBtn) sendBtn.disabled = true;
    input.disabled = true;
    input.placeholder = "Mikey is thinking...";
    
    const reqId = "req_" + Date.now();
    
    if (chatAbortController) chatAbortController.abort();
    chatAbortController = new AbortController();
    
    isStreamActive = true;
    setVoiceState('PROCESSING');

    console.log(`\nNEURAL LINK BROWSER REQUEST`);
    console.log(`URL: ${window.location.origin}/stream_chat`);
    console.log(`METHOD: POST`);
    console.log(`BODY: ${JSON.stringify(payload).substring(0, 150)}...`);
    console.log(`REQUEST ID (CLIENT): ${reqId}\n`);
    
    let fullReply = '';
    let streamBubbleDiv = null;

    try {
      const res = await fetch('/stream_chat', {
        signal: chatAbortController.signal,
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      removeTyping(tId);
      
      if (res.ok) {
        // Create empty message bubble
        const msgId = 'msg-' + Date.now();
        const box = document.getElementById('messages');
        const div = document.createElement('div');
        div.id = msgId; div.className = 'msg bot';
        div.innerHTML = `<div class="avatar bot-av">✦</div><div class="bubble bot-bubble"></div>`;
        box.appendChild(div);
        streamBubbleDiv = div;
        
        const bubble = div.querySelector('.bubble');
        
        // Read the stream
        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        
        let unvoicedText = '';
        let hasSpokenFirstChunk = false;
        const prefs = langConfig[currentLang];
        
        while (true) {
          let done, value;
          try {
            const result = await reader.read();
            done = result.done;
            value = result.value;
          } catch (err) {
            isStreamActive = false;
            if (err.name === 'AbortError' || err.code === 20) {
              console.log("Chat aborted by user.");
              break;
            }
            // If we already received chunks (like "Hi! What's on your mind?"), keep the answer!
            if (fullReply.trim()) {
              console.warn("Stream interrupted midway, preserving received answer:", err);
              break;
            }
            throw err;
          }
          
          const shouldSpeak = isLiveMode || document.getElementById('ttsToggle')?.checked;
          if (done) {
            isStreamActive = false;
            if (unvoicedText.trim() && shouldSpeak) {
               const clean = cleanTextForSpeech(unvoicedText);
               if (clean) voiceQueue.add(clean, prefs.ttsLang);
               unvoicedText = "";
            }
            if (!voiceQueue.isPlaying && voiceQueue.queue.length === 0) {
              setVoiceState('IDLE');
              if (isLiveMode) setTimeout(startListening, 500);
            }
            break;
          }
          
          const chunk = decoder.decode(value, { stream: true });
          fullReply += chunk;
          unvoicedText += chunk;
          
          // Chunk by sentence boundaries if TTS is on or in Live Talk Mode
          if (shouldSpeak) {
             while (true) {
               const terminatorRegex = (!hasSpokenFirstChunk && unvoicedText.length >= 35)
                 ? /(?:[\r\n]+|(?<!\b\d)(?<!\b(?:Mr|Mrs|Ms|Dr|Prof|vs|etc|approx|dept|jr|sr|No))[.!?]+(?!\d)|(?<!\b\d)[,:;]+(?!\d))(?=\s+)/i
                 : /(?:[\r\n]+|(?<!\b\d)(?<!\b(?:Mr|Mrs|Ms|Dr|Prof|vs|etc|approx|dept|jr|sr|No))[.!?]+(?!\d))(?=\s+)/i;

               const sentenceMatch = unvoicedText.match(terminatorRegex);
               if (!sentenceMatch) break;

               const endIndex = sentenceMatch.index + sentenceMatch[0].length;
               const sentence = unvoicedText.substring(0, endIndex);
               unvoicedText = unvoicedText.substring(endIndex).replace(/^[\s\r\n]+/, '');

               const clean = cleanTextForSpeech(sentence);
               // Must have meaningful speech content (at least 2 letters/digits, not just a standalone bullet/marker)
               if (clean && /[a-zA-Z0-9\u0C00-\u0C7F]{2,}/.test(clean)) {
                 hasSpokenFirstChunk = true;
                 voiceQueue.add(clean, prefs.ttsLang);
               }
             }
          }
          
          bubble.innerHTML = formatMarkdown(fullReply);
          box.scrollTop = box.scrollHeight;
        }
        
        // Attach Claude-style bot action buttons after stream completes
        if (!div.querySelector('.msg-actions') && fullReply.trim()) {
          div.insertAdjacentHTML('beforeend', createBotActionsHtml());
        }

        // Cleanup and save after stream ends
        if (fullReply.trim()) {
          chatHistory.push({ role: 'assistant', content: fullReply });
          saveCurrentThread();
        }
        
        if (!shouldSpeak) {
          setVoiceState('IDLE');
          if (isLiveMode) setTimeout(startListening, 500);
        }

      } else {
        throw new Error(`Stream endpoint returned ${res.status}`);
      }
    } catch (streamErr) {
      isStreamActive = false;
      if (streamErr.name === 'AbortError' || streamErr.code === 20) {
        console.log('Stream aborted.');
        return;
      }

      // If we already received chunks from the stream, do not treat as fatal error
      if (fullReply && fullReply.trim()) {
        console.log('Stream completed with received content.');
        return;
      }

      // Remove the empty stream bubble if one was created
      if (streamBubbleDiv) {
        streamBubbleDiv.remove();
        streamBubbleDiv = null;
      }

      console.warn('Stream failed, attempting fallback to /chat endpoint:', streamErr);

      // Attempt transparent fallback to non-streaming /chat
      try {
        const fallbackRes = await fetch('/chat', {
          signal: chatAbortController.signal,
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        removeTyping(tId);

        if (fallbackRes.ok) {
          const fallbackData = await fallbackRes.json();
          const replyText = fallbackData.reply || '';
          if (replyText) {
            appendMsg('bot', replyText, '✦');
            chatHistory.push({ role: 'assistant', content: replyText });
            saveCurrentThread();
            const shouldSpeak = isLiveMode || document.getElementById('ttsToggle')?.checked;
            if (shouldSpeak) {
              const clean = cleanTextForSpeech(replyText);
              if (clean) voiceQueue.add(clean, langConfig[currentLang]?.ttsLang);
            } else {
              setVoiceState('IDLE');
              if (isLiveMode) setTimeout(startListening, 500);
            }
            return;
          }
        }
        throw new Error(`Fallback returned ${fallbackRes.status}`);
      } catch (fallbackErr) {
        if (fallbackErr.name === 'AbortError' || fallbackErr.code === 20) {
          return;
        }
        console.error('Both stream and fallback chat failed:', fallbackErr);
        removeTyping(tId);
        lastFailedMessage = text;

        // Restore prompt into input if input is currently empty
        if (!input.value) {
          input.value = text;
        }

        appendConnectionError();
        setVoiceState('IDLE');
        if (isLiveMode) setTimeout(startListening, 500);
      }
    } finally {
      isStreamActive = false;
      if (sendBtn) sendBtn.disabled = false;
      input.disabled = false;
      input.placeholder = langConfig[currentLang]?.placeholder || "Enter message...";
      input.focus();
    }
  }

// Vision Key Modal Functions
function openVisionKeyModal() {
  const m = document.getElementById('visionModal');
  if (m) m.style.display = 'flex';
}
function closeVisionKeyModal() {
  const m = document.getElementById('visionModal');
  if (m) m.style.display = 'none';
}
async function saveGeminiKey() {
  const key = document.getElementById('geminiKeyInput').value.trim();
  if (!key) return;
  const statusDiv = document.getElementById('visionKeyStatus');
  statusDiv.style.color = '#00f2fe';
  statusDiv.textContent = 'Verifying key with Google Gemini...';
  try {
    const res = await fetch('/api/save-gemini-key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: key })
    });
    const data = await res.json();
    if (res.ok) {
      statusDiv.style.color = '#34d399';
      statusDiv.textContent = '✅ ' + data.message;
      setTimeout(() => { closeVisionKeyModal(); }, 1500);
    } else {
      statusDiv.style.color = '#f87171';
      statusDiv.textContent = '❌ ' + (data.detail || 'Verification failed');
    }
  } catch (e) {
    statusDiv.style.color = '#f87171';
    statusDiv.textContent = '❌ Network error: ' + e.message;
  }
}

// init
window.addEventListener('DOMContentLoaded', () => {
  // Initialization now handled after loadAccount() to prevent Guest/User thread bleeding
});