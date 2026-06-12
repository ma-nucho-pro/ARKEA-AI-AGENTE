/*
 * ARKEA AI
 * by: Arkeai AI Roberto Manuel Jara Peche
 * Copyright (C) 2026 Roberto Manuel Jara Peche.
 * Licensed under AGPL-3.0-or-later.
 */
const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));
const messages = $('#messages');
const viewer = $('#viewer');
const code = $('#code');
const avatarFace = $('#avatarFace');
let voices = [];
const ARKEA_LANGS = {
  es:{name:'Español',lang:'es-ES',prefixes:['es'],ui:{talk:'Hablar',camera:'Cámara',screen:'Pantalla',send:'Enviar',upload:'Subir',visual:'Modo HTML visual',clear:'Limpiar',newChat:'+ Nuevo chat',placeholder:'Escribe tu mensaje o usa el micrófono...',mini:'Escribe aquí...',live:'Vista y código en vivo.',thinking:'Pensando...'}},
  en:{name:'English',lang:'en-US',prefixes:['en'],ui:{talk:'Talk',camera:'Camera',screen:'Screen',send:'Send',upload:'Upload',visual:'Visual HTML mode',clear:'Clear',newChat:'+ New chat',placeholder:'Type your message or use the microphone...',mini:'Type here...',live:'Live view and code.',thinking:'Thinking...'}},
  fr:{name:'Français',lang:'fr-FR',prefixes:['fr'],ui:{talk:'Parler',camera:'Caméra',screen:'Écran',send:'Envoyer',upload:'Téléverser',visual:'Mode HTML visuel',clear:'Nettoyer',newChat:'+ Nouveau chat',placeholder:'Écris ton message ou utilise le micro...',mini:'Écris ici...',live:'Vue et code en direct.',thinking:'Réflexion...'}},
  it:{name:'Italiano',lang:'it-IT',prefixes:['it'],ui:{talk:'Parla',camera:'Camera',screen:'Schermo',send:'Invia',upload:'Carica',visual:'Modo HTML visuale',clear:'Pulisci',newChat:'+ Nuova chat',placeholder:'Scrivi il messaggio o usa il microfono...',mini:'Scrivi qui...',live:'Vista e codice live.',thinking:'Sto pensando...'}},
  pt:{name:'Português',lang:'pt-BR',prefixes:['pt'],ui:{talk:'Falar',camera:'Câmera',screen:'Tela',send:'Enviar',upload:'Subir',visual:'Modo HTML visual',clear:'Limpar',newChat:'+ Novo chat',placeholder:'Escreva a mensagem ou use o microfone...',mini:'Escreva aqui...',live:'Vista e código ao vivo.',thinking:'Pensando...'}},
  zh:{name:'中文',lang:'zh-CN',prefixes:['zh'],ui:{talk:'说话',camera:'摄像头',screen:'屏幕',send:'发送',upload:'上传',visual:'HTML 可视模式',clear:'清空',newChat:'+ 新聊天',placeholder:'输入消息或使用麦克风...',mini:'在此输入...',live:'实时视图和代码。',thinking:'思考中...'}}
};
let settingsCache = {};
let currentConversationId = null;
let currentProjectId = null;
let currentConversationFolder = '';
let currentPreviewUrl = '';
let currentOutputFolder = '';
let currentOutputFile = '';
let currentDownloadUrl = '';
let currentPreviewKind = 'html';
let viewerZoom = 1;
let liveBuildTimer = null;
let currentAudio = null;
let liveAbortControllers = new Set();
let stopAllGeneration = 0;
let visualMode = true;
let sendingMessage = false;
let activePulls = new Set();
let autoBootstrapStarted = false;
let recording = false;
let audioCtx = null;
let micStream = null;
let processor = null;
let chunks = [];
let voiceStarted = false;
let silenceStart = 0;
let recordingStartedAt = 0;
let screenLiveTimer = null;
let cameraStream = null;
let cameraLiveTimer = null;
let lastCameraAnalyze = 0;
let lastVisionSay = '';
let lastVisionSayTs = 0;
let currentScreenSourceId = '';
let screenLiveActive = false;
let screenLiveToken = 0;
let lastScreenFrame = '';
let lastScreenName = '';
let cameraLiveActive = false;
let cameraLiveToken = 0;
let lastCameraFrame = '';
let lastScreenAnalyze = 0;
let uploadedContexts = [];

function esc(v=''){
  return String(v ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}
function js(v=''){ return JSON.stringify(String(v ?? '')); }
async function j(url, opts={}){
  const r = await fetch(url, opts);
  const text = await r.text();
  let data = null;
  try { data = text ? JSON.parse(text) : {}; } catch { data = {raw:text}; }
  if(!r.ok){ throw new Error(data.detail || data.error || text || r.statusText); }
  return data;
}
function addMsg(role, text){
  let t = String(text ?? '');
  const looksLikeHugeCode = /<!doctype html|<html|<head|<style|\.term-fg|body\{|@media|<script/i.test(t) && t.length > 350;
  if(role === 'assistant' && looksLikeHugeCode){
    if(/<!doctype html|<html/i.test(t)){
      try{ setPreviewHtml(t); setPreviewLabel('Vista generada'); }catch{}
    }
    t = 'Listo. Actualicé la vista previa sin mostrar el código largo en el chat.';
  }
  if(role === 'assistant' && t.length > 900 && /\{|\}|<|>|;/.test(t)){
    t = t.slice(0,420).replace(/\s+/g,' ').trim() + '…';
  }
  const d = document.createElement('div');
  d.className = 'msg ' + role;
  d.textContent = t;
  messages.appendChild(d);
  messages.scrollTop = messages.scrollHeight;
  return d;
}
function setPreviewLabel(text){ $('#previewLabel').textContent = text || 'Sin archivo'; }
function setLiveStatus(text, thinking=false){ const el=$('#liveStatus'); if(!el) return; el.innerHTML = `<span class="pulse"></span> ${esc(text || '')}`; el.classList.toggle('thinking', !!thinking); }
function updateViewerZoomLabel(){ try{ const el=$('#zoomLabel'); if(el) el.textContent = Math.round(viewerZoom*100) + '%'; }catch{} }
function setPreviewHtml(html){ showViewFrame(); currentPreviewKind='html'; viewer.removeAttribute('src'); viewer.srcdoc = html || ''; currentPreviewUrl = ''; }
function setPreviewUrl(url,label='Vista previa'){ showViewFrame(); currentPreviewKind='url'; currentPreviewUrl=url||''; viewer.removeAttribute('srcdoc'); viewer.src=url||'about:blank'; setPreviewLabel(label); }
function _imageViewerHtml(url,label='Imagen generada'){
  return `<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;min-height:100%;background:#06120f;color:#ecfff2;font-family:Segoe UI,Arial;overflow:auto}.wrap{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;padding:18px;gap:12px}.badge{padding:8px 14px;border-radius:999px;background:rgba(16,185,129,.18);border:1px solid rgba(16,185,129,.38);font-size:12px}img{max-width:calc(100vw - 70px);max-height:calc(100vh - 120px);border-radius:18px;box-shadow:0 18px 60px rgba(0,0,0,.35);transform:scale(${viewerZoom});transform-origin:top center;transition:transform .16s ease}.hint{font-size:12px;opacity:.75}</style></head><body><div class="wrap"><div class="badge">${esc(label)}</div><img src="${url}" alt="${esc(label)}"/><div class="hint">Usa + / - para acercar o alejar.</div></div></body></html>`;
}
function setPreviewImage(url,label='Imagen generada'){ showViewFrame(); currentPreviewKind='image'; currentPreviewUrl=url||''; viewer.removeAttribute('src'); viewer.srcdoc = _imageViewerHtml(url,label); setPreviewLabel(label); updateViewerZoomLabel(); }
function updateViewerZoom(delta=0){ viewerZoom = Math.max(0.25, Math.min(3, Number((viewerZoom + delta).toFixed(2)))); updateViewerZoomLabel(); if(currentPreviewKind==='image' && currentPreviewUrl) setPreviewImage(currentPreviewUrl, $('#previewLabel')?.textContent || 'Imagen generada'); }
function abortLiveRequests(){ try{ liveAbortControllers.forEach(c=>{try{c.abort();}catch{}}); liveAbortControllers.clear(); }catch{} }
async function visionRequest(payload, timeoutMs=30000){ const c=new AbortController(); liveAbortControllers.add(c); const t=setTimeout(()=>c.abort(),timeoutMs); try{return await j('/api/arkea/vision/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:c.signal});} finally{clearTimeout(t); liveAbortControllers.delete(c);} }
function startLiveBuildPreview(prompt=''){
  stopLiveBuildPreview();
  const p=String(prompt||'').toLowerCase();
  const kind=/excel|xlsx|hoja/.test(p)?'excel':/word|docx|documento|informe/.test(p)?'word':/powerpoint|ppt|diapositiva|presentaci/.test(p)?'ppt':/imagen|foto|logo|ilustr|png|jpg|miniatura|thumbnail/.test(p)?'image':/simul|animaci|juego|html|web|app|código|codigo/.test(p)?'code':'chat';
  const titles={word:'Word en vivo',excel:'Excel en vivo',ppt:'PowerPoint en vivo',image:'Imagen en vivo',code:'Código en vivo',chat:'Respuesta visual en vivo'};
  setPreviewLabel(titles[kind] || 'Pensando...');
  if(kind==='code'){
    showCode(); code.textContent='';
    const lines=['// ARKEA AI está creando código nuevo desde cero...','Analizando instrucción del usuario...','Diseñando estructura HTML...', 'Escribiendo CSS visual...', 'Programando JavaScript...', 'Guardando y actualizando vista previa...'];
    let i=0; liveBuildTimer=setInterval(()=>{ if(i<lines.length){ code.textContent += (i?'\n':'')+lines[i++]; code.scrollTop=code.scrollHeight; } },300); return;
  }
  const appName = kind==='word'?'Word':kind==='excel'?'Excel':kind==='ppt'?'PowerPoint':kind==='image'?'Imagen':'ARKEA';
  const steps={word:['Redactando contenido','Organizando títulos y cuadros','Aplicando diseño ARKEA','Preparando DOCX editable'],excel:['Diseñando hojas reales','Aplicando formatos y filtros','Creando tablas y estructura','Preparando XLSX'],ppt:['Diseñando diapositivas','Creando portada y secciones','Aplicando estilo visual','Preparando PPTX'],image:['Preparando prompt visual','Conectando API/imagen local','Generando PNG/JPG','Preparando zoom'],chat:['Pensando...','Preparando respuesta clara','Actualizando vista visual']};
  let i=0, arr=steps[kind]||steps.chat;
  const render=()=>setPreviewHtml(`<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#071812;color:#eafff0;font-family:Segoe UI,Arial;padding:26px}.shell{max-width:980px;margin:auto;background:rgba(255,255,255,.06);border:1px solid rgba(16,185,129,.24);border-radius:22px;padding:0;overflow:hidden;box-shadow:0 20px 70px rgba(0,0,0,.28)}.bar{height:50px;background:linear-gradient(90deg,#0f6b45,#10b981);display:flex;align-items:center;padding:0 18px;font-weight:800}.paper{margin:24px auto;background:#fff;color:#0f172a;width:min(760px,90%);min-height:430px;border-radius:8px;padding:42px;box-shadow:0 12px 30px rgba(0,0,0,.22)}.step{display:flex;gap:10px;margin:12px 0;padding:12px 14px;border-radius:14px;background:rgba(15,23,42,.04);border:1px solid #e2e8f0}.ok{color:#16a34a;font-weight:900}</style></head><body><div class="shell"><div class="bar">${appName} · Vista en vivo</div><div class="paper"><h1>${titles[kind]}</h1><p>ARKEA está creando el archivo en tiempo real.</p>${arr.map((s,idx)=>`<div class="step"><span class="ok">${idx<i?'✓':'…'}</span><span>${s}</span></div>`).join('')}<small>Prompt: ${esc(prompt).slice(0,180)}</small></div></div></body></html>`);
  render(); liveBuildTimer=setInterval(()=>{i=Math.min(i+1,arr.length); render();},450);
}
function stopLiveBuildPreview(){ if(liveBuildTimer){ clearInterval(liveBuildTimer); liveBuildTimer=null; } }
function renderGeneratedFilePreview(data={}){
  const file=data.file||currentOutputFile||'';
  const ext=(file.split('.').pop()||'archivo').toLowerCase();
  const title=(data.title || (ext.toUpperCase() + ' generado'));
  let body='';
  if(ext==='docx' || ext==='doc'){
    body = `<div class="office-shell word"><div class="office-ribbon"><b>Word</b><span>Inicio</span><span>Insertar</span><span>Diseño</span><span>Revisar</span></div><div class="paper"><h1>${esc(title)}</h1><p>${esc(data.say||'Documento Word creado correctamente.')}</p><h2>Contenido generado por ARKEA AI</h2><p>El documento fue redactado con estructura profesional, cuadros, colores y estilo ARKEA. Puedes abrir la carpeta para editarlo en Word u Office compatible.</p><div class="doc-box"><b>Archivo:</b><br>${esc(file)}</div></div></div>`;
  }else if(ext==='xlsx' || ext==='xls'){
    body = `<div class="office-shell excel"><div class="office-ribbon"><b>Excel</b><span>Inicio</span><span>Datos</span><span>Fórmulas</span><span>Vista</span></div><table class="sheet"><tr><th>Hoja</th><th>Estado</th><th>Diseño</th></tr><tr><td>Resumen</td><td>Creada</td><td>ARKEA</td></tr><tr><td>Plan</td><td>Creada</td><td>Colores y filtros</td></tr><tr><td>Indicadores</td><td>Creada</td><td>Lista</td></tr></table><p class="doc-box">${esc(file)}</p></div>`;
  }else if(ext==='pptx' || ext==='ppt'){
    body = `<div class="office-shell ppt"><div class="office-ribbon"><b>PowerPoint</b><span>Diseño</span><span>Transiciones</span><span>Presentación</span></div><div class="slide"><h1>${esc(title)}</h1><p>${esc(data.say||'Presentación creada.')}</p></div><p class="doc-box">${esc(file)}</p></div>`;
  }else{
    body = `<div class="office-shell"><h1>${esc(title)}</h1><p>${esc(data.say||'Archivo generado correctamente.')}</p><div class="doc-box">${esc(file)}</div></div>`;
  }
  const html=`<!doctype html><html><head><meta charset="utf-8"><style>
  body{margin:0;background:#0b1411;color:#0f172a;font-family:Segoe UI,Arial;padding:24px}.office-shell{max-width:980px;margin:auto;background:#f8fafc;border-radius:20px;box-shadow:0 24px 80px rgba(0,0,0,.32);overflow:hidden}.office-ribbon{height:54px;background:linear-gradient(90deg,#0f6b45,#16a34a);color:#fff;display:flex;align-items:center;gap:22px;padding:0 20px}.office-ribbon b{font-size:18px}.paper{width:min(760px,92%);min-height:760px;margin:28px auto;background:#fff;padding:58px;box-shadow:0 8px 26px rgba(15,23,42,.18);border:1px solid #e2e8f0}.paper h1{font-size:30px;color:#0f172a}.paper h2{color:#166534}.doc-box{margin-top:20px;background:#ecfdf5;border:1px solid #bbf7d0;border-radius:14px;padding:14px;color:#14532d;word-break:break-all}.sheet{width:92%;margin:28px auto;border-collapse:collapse;background:white}.sheet th{background:#16a34a;color:#fff}.sheet th,.sheet td{border:1px solid #dbe4f0;padding:14px;text-align:left}.slide{margin:34px auto;width:82%;aspect-ratio:16/9;background:linear-gradient(135deg,#0f6b45,#38bdf8);border-radius:20px;color:white;padding:48px;display:flex;flex-direction:column;justify-content:center}.slide h1{font-size:42px;margin:0 0 16px}</style></head><body>${body}</body></html>`;
  setPreviewHtml(html); setPreviewLabel((ext||'archivo').toUpperCase()+' generado');
}
function setButtonBusy(btn, busy, label='Procesando...'){
  if(!btn) return true;
  if(busy){
    if(btn.dataset.busy === '1') return false;
    btn.dataset.busy = '1';
    btn.dataset.originalText = btn.textContent;
    btn.disabled = true;
    btn.classList.add('loading');
    btn.textContent = '⏳ ' + label;
    return true;
  }
  btn.disabled = false;
  btn.classList.remove('loading');
  btn.textContent = btn.dataset.originalText || btn.textContent;
  btn.dataset.busy = '0';
  return true;
}
function showViewFrame(){ code.hidden = true; viewer.hidden = false; }
function cleanVisionClientText(text=''){
  let t=String(text||'').trim();
  try{const j=JSON.parse(t); t=j.say||j.text||j.output_text||j.choices?.[0]?.message?.content||j.choices?.[0]?.message?.reasoning||t;}catch{}
  t=String(t||'').replace(/```/g,'').replace(/\s+/g,' ').trim();
  t=t.replace(/^El usuario quiere[^.]*\.*/i,'').replace(/^Analizar la imagen[:：]?/i,'').replace(/\*\*/g,'').trim();
  if(t.length>420) t=t.slice(0,420).replace(/[,;:]?\s+\S*$/,'')+'…';
  return t||'No recibí una descripción clara de la imagen.';
}
function addVisionMsg(prefix, text){
  const now = Date.now();
  text = cleanVisionClientText(text);
  const msg = prefix + ' ' + text;
  if(msg === lastVisionSay && now - lastVisionSayTs < 9000) return;
  lastVisionSay = msg; lastVisionSayTs = now;
  addMsg('assistant', msg);
  speak(text);
}
function showImageInPreview(dataUrl, label){ setPreviewImage(dataUrl, label || 'Vista'); }

function setAvatarState(state){
  avatarFace.classList.toggle('speaking', state === 'speaking');
  avatarFace.classList.toggle('listening', state === 'listening');
  $('#avatarCaption').textContent = state === 'speaking' ? 'Hablando...' : state === 'listening' ? 'Escuchando...' : 'Arkea listo';
}
function emotionParams(){
  const e = settingsCache.avatar_emotion || 'neutral';
  return ({happy:{pitch:1.25,rate:1.08},angry:{pitch:.72,rate:1.13},annoyed:{pitch:.82,rate:.94},excited:{pitch:1.36,rate:1.2},serious:{pitch:.8,rate:.9},calm:{pitch:1.05,rate:.86},neutral:{pitch:1,rate:1}})[e] || {pitch:1,rate:1};
}
function emotionPrefix(text){
  // Habla natural: no agrega “wow/wao” ni frases de inicio.
  return text;
}

function applyTheme(){
  const theme = settingsCache.theme_mode || 'jade';
  document.body.classList.toggle('theme-dark', theme === 'dark');
  document.body.classList.toggle('theme-light', theme === 'light' || theme === 'sky');
  if(settingsCache.ui_accent_1) document.documentElement.style.setProperty('--jade', settingsCache.ui_accent_1);
  if(settingsCache.ui_accent_2) document.documentElement.style.setProperty('--jade2', settingsCache.ui_accent_2);
  let bg = settingsCache.ui_background_custom || '';
  if(!bg){
    const preset = settingsCache.ui_background_preset || 'valley';
    bg = preset === 'sky' ? '/static/assets/arkea-wallpaper-sky.png' : '/static/assets/arkea-wallpaper-valley.png';
  }
  const safeBg = String(bg).replace(/"/g,'%22');
  document.documentElement.style.setProperty('--dynamic-bg', `url("${safeBg}")`);
  document.body.style.backgroundImage = `linear-gradient(135deg,rgba(5,26,20,.68),rgba(3,20,18,.72)), url("${safeBg}")`;
  document.body.style.backgroundSize = 'cover'; document.body.style.backgroundAttachment = 'fixed'; document.body.style.backgroundPosition = 'center';
}
function applyAvatarSettings(){
  const e = settingsCache.avatar_emotion || 'neutral';
  avatarFace.className = 'avatar-face emotion-' + e;
  if(settingsCache.avatar_color_1) document.documentElement.style.setProperty('--avatar1', settingsCache.avatar_color_1);
  if(settingsCache.avatar_color_2) document.documentElement.style.setProperty('--avatar2', settingsCache.avatar_color_2);
  if(settingsCache.avatar_eye_color) document.documentElement.style.setProperty('--avatarEye', settingsCache.avatar_eye_color);
  if(settingsCache.avatar_mouth_color) document.documentElement.style.setProperty('--avatarMouth', settingsCache.avatar_mouth_color);
  if(settingsCache.avatar_inner_color) document.documentElement.style.setProperty('--avatarInner', settingsCache.avatar_inner_color);
  const img = $('#customAvatarImg');
  const eyes = avatarFace.querySelector('.avatar-eyes');
  const mouth = $('#avatarMouth');
  const brows = avatarFace.querySelector('.avatar-brows');
  if(settingsCache.avatar_data_url){
    img.src = settingsCache.avatar_data_url;
    img.hidden = false;
    eyes.style.display = 'none'; mouth.style.display = 'block'; brows.style.display = 'none'; mouth.classList.add('custom-mouth');
  } else {
    img.hidden = true;
    eyes.style.display = 'flex'; mouth.style.display = 'block'; brows.style.display = 'flex'; mouth.classList.remove('custom-mouth');
  }
}
async function loadSettings(){
  try{
    try{ await j('/api/arkea/apis/cleanup-broken',{method:'POST'}); }catch{}
    const d = await j('/api/arkea/settings');
    settingsCache = Object.fromEntries((d.settings || []).map(x => [x.key, x.value]));
    if(!settingsCache.user_name){ settingsCache.user_name = 'Manu'; }
    applyTheme(); applyAvatarSettings(); await loadVoices();
  }catch(e){ console.warn(e); }
}
async function saveSetting(k,v){
  await j('/api/arkea/settings/set',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:k,value:String(v ?? '')})});
  settingsCache[k] = String(v ?? '');
  applyTheme(); applyAvatarSettings();
}
async function saveBulk(values){
  await j('/api/arkea/settings/bulk',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({values})});
  for(const [k,v] of Object.entries(values || {})) settingsCache[k] = String(v ?? '');
  applyTheme(); applyAvatarSettings();
}
async function currentLangProfile(){
  const code=(settingsCache.ui_language||'es').slice(0,2).toLowerCase();
  return ARKEA_LANGS[code] || ARKEA_LANGS.es;
}
function loadVoices(){
  try{
    const all = window.speechSynthesis ? (speechSynthesis.getVoices() || []) : [];
    // Mantener los objetos SpeechSynthesisVoice reales. No se clonan porque Chromium puede dejar de hablar si voice no es el objeto real.
    voices = Array.from(all);
    let html = voices.map((v,i)=>`<option value="sys:${i}">${esc(v.name || 'Voz sin nombre')} (${esc(v.lang || 'desconocido')})</option>`).join('');
    if(settingsCache.elevenlabs_voice_id){
      const name = settingsCache.elevenlabs_voice_name || 'ElevenLabs voz personalizada';
      html += `<option value="eleven:${esc(settingsCache.elevenlabs_voice_id)}">${esc(name)} (ElevenLabs)</option>`;
    }
    const sel = $('#voices');
    if(sel){
      const previous = sel.value;
      sel.innerHTML = html || '<option>Sin voces detectadas</option>';
      const preferredSaved = settingsCache.browser_voice_value || '';
      const spanish = voices.findIndex(v => (v.lang || '').toLowerCase().startsWith('es'));
      if(previous && [...sel.options].some(o=>o.value===previous)) sel.value = previous;
      else if(preferredSaved && [...sel.options].some(o=>o.value===preferredSaved)) sel.value = preferredSaved;
      else if(spanish >= 0) sel.value = 'sys:' + spanish;
      else if(voices.length) sel.value = 'sys:0';
      sel.onchange = () => { try{ saveSetting('browser_voice_value', sel.value); }catch{} };
    }
    return voices.length;
  }catch(e){ console.warn(e); return 0; }
}
function loadVoicesRetry(){
  let tries=0;
  const run=()=>{ const n=loadVoices(); if(!n && tries++<10) setTimeout(run, 350); };
  run();
}
if('speechSynthesis' in window) speechSynthesis.onvoiceschanged = () => loadVoicesRetry();

async function speakElevenLabs(text, voiceId=''){
  try{
    setAvatarState('speaking');
    const r = await fetch('/api/arkea/voice/elevenlabs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text, voice_id: voiceId || settingsCache.elevenlabs_voice_id || ''})});
    if(!r.ok) throw new Error(await r.text());
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    currentAudio = audio;
    audio.onended = () => { if(currentAudio === audio) currentAudio = null; setAvatarState('idle'); };
    audio.onerror = () => { if(currentAudio === audio) currentAudio = null; setAvatarState('idle'); };
    await audio.play();
    return true;
  }catch(e){
    addMsg('assistant','No pude usar ElevenLabs: ' + e.message);
    setAvatarState('idle');
    return false;
  }
}

function hablar(textoManual){
  const txt = textoManual || ($('#textoVoz')?.value || 'Hola, soy la voz narradora de ARKEA AI. Puedo hablar en varios idiomas según la voz seleccionada.');
  speak(txt);
}
function pausarVoz(){ try{ speechSynthesis.pause(); }catch{} }
function reanudarVoz(){ try{ speechSynthesis.resume(); }catch{} }
function detenerVoz(){
  try{ speechSynthesis.cancel(); }catch{}
  try{ if(currentAudio){ currentAudio.pause(); currentAudio.currentTime = 0; currentAudio = null; } }catch{}
  setAvatarState('idle');
}

function cleanSpeechText(text=''){
  return String(text || '').replace(/^\s*(wow|wao|guau)[,!¡\s]+/i, '').trim();
}
async function speak(text){
  if(!$('#voiceOut').checked) return;
  if(!voices.length) loadVoicesRetry();
  const finalText = cleanSpeechText(emotionPrefix(text));
  const val = $('#voices').value || '';
  if(val.startsWith('eleven:')){ await speakElevenLabs(finalText, val.slice(7)); return; }
  const useEleven = settingsCache.use_elevenlabs_voice === '1' || settingsCache.use_elevenlabs_voice === 'true';
  if(useEleven && settingsCache.elevenlabs_voice_id){ if(await speakElevenLabs(finalText)) return; }
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(finalText);
  let idx = val.startsWith('sys:') ? Number(val.slice(4)) : -1;
  if(idx < 0 || !voices[idx]){ const pref=(currentLangProfile().prefixes||['es']); idx=voices.findIndex(v=>pref.some(p=>(v.lang||'').toLowerCase().startsWith(p))); }
  if(idx >= 0 && voices[idx]){ u.voice = voices[idx]; u.lang = voices[idx].lang || currentLangProfile().lang; }
  else { u.lang = settingsCache.input_language || currentLangProfile().lang; }
  const p = emotionParams(); u.pitch = p.pitch; u.rate = p.rate;
  u.onstart = () => setAvatarState('speaking');
  u.onend = () => setAvatarState('idle');
  u.onerror = () => setAvatarState('idle');
  try{ speechSynthesis.resume(); }catch{}
  speechSynthesis.speak(u);
  setTimeout(()=>{ if(!speechSynthesis.speaking && !speechSynthesis.pending) setAvatarState('idle'); }, Math.max(1200, finalText.length*55));
}


function isVisionQuestion(text=''){
  const t = String(text || '').toLowerCase();
  return (
    (t.includes('que ves') || t.includes('qué ves') || t.includes('ves en') || t.includes('dime que ves') || t.includes('describe')) &&
    (t.includes('pantalla') || t.includes('camara') || t.includes('cámara') || screenLiveActive || cameraLiveActive || lastScreenFrame || lastCameraFrame)
  );
}
async function answerCurrentVisionQuestion(text, thinkingNode=null){
  const t = String(text || '').toLowerCase();
  let frame = '';
  let source = '';
  if((t.includes('camara') || t.includes('cámara')) && lastCameraFrame){
    frame = lastCameraFrame; source = 'camera-question';
  }else if(lastScreenFrame){
    frame = lastScreenFrame; source = 'screen-question';
  }else if(lastCameraFrame){
    frame = lastCameraFrame; source = 'camera-question';
  }
  if(!frame) return false;
  try{
    const prompt = text + "\nResponde en español, directo y con detalles visibles. Si ves texto, léelo. Si ves ventanas o botones, descríbelos.";
    const res = await j('/api/arkea/vision/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image_data_url:frame, source, prompt})});
    if(thinkingNode) thinkingNode.remove();
    const say = res.say || 'Veo la imagen en vivo, pero no hay modelo de visión/API configurado para describirla todavía. Configura una API de visión en Ajustes > APIS o descarga moondream/gemma3:4b.';
    addMsg('assistant', (source.startsWith('screen') ? '🖥️ ' : '📷 ') + say);
    if($('#voiceOut')?.checked) speak(say);
    return true;
  }catch(e){
    if(thinkingNode) thinkingNode.remove();
    addMsg('assistant','No pude analizar la imagen actual: ' + e.message);
    return true;
  }
}
function setStoppedPreview(label='Vista detenida'){
  setPreviewHtml(`<!doctype html><html><body style="margin:0;display:grid;place-items:center;min-height:100vh;background:#07111f;color:#e5f1ff;font-family:Segoe UI,Arial"><main style="text-align:center"><h1>${esc(label)}</h1><p>La captura en vivo se detuvo correctamente.</p></main></body></html>`);
  setPreviewLabel(label);
}

async function uploadSelectedFiles(files){
  if(!files || !files.length) return;
  for(const file of files){
    const fd = new FormData(); fd.append('file', file, file.name);
    addMsg('user','Archivo subido: '+file.name);
    try{
      const r=await fetch('/api/arkea/uploads/file',{method:'POST',body:fd});
      const data=await r.json();
      if(data.path){ currentOutputFolder=data.path.replace(/[\/][^\/]*$/,''); currentOutputFile=data.path; }
      uploadedContexts.push({filename:data.filename||file.name,kind:data.kind||'file',url:data.url||'',path:data.path||'',data_url:data.data_url||'',extracted_text:data.extracted_text||''});
      if(uploadedContexts.length>8) uploadedContexts=uploadedContexts.slice(-8);
      addMsg('assistant',(data.message||'Archivo recibido.')+' Tipo: '+(data.kind||'archivo')+'. Lo usaré como contexto cuando me preguntes.');
      if(data.kind==='image'){
        visionRequest({image_data_url:data.data_url||data.url,source:'upload',prompt:'Analiza esta imagen brevemente en español. Di qué ves de forma clara y humana.'},30000)
          .then(res=>{ if(res.say){ uploadedContexts[uploadedContexts.length-1].vision_text=res.say; addMsg('assistant','Imagen analizada: '+res.say); if($('#voiceOut')?.checked) speak(res.say); } })
          .catch(()=>{});
      }else if(data.extracted_text){
        const summary=String(data.extracted_text).replace(/\s+/g,' ').slice(0,280);
        addMsg('assistant','Resumen del archivo: '+summary+(summary.length>=280?'…':''));
        if($('#voiceOut')?.checked) speak('Archivo recibido. Ya extraje su contenido y puedo trabajar con él.');
      }
    }catch(e){ addMsg('assistant','No pude subir '+file.name+': '+e.message); }
  }
}



async function downloadCurrentAsset(){
  const url=currentDownloadUrl||currentPreviewUrl||'';
  if(url){ const a=document.createElement('a'); a.href=url; a.download=''; a.target='_blank'; document.body.appendChild(a); a.click(); a.remove(); return; }
  if(currentOutputFile && window.arkeaDesktop?.revealPath){ await window.arkeaDesktop.revealPath(currentOutputFile); return; }
  if(currentOutputFolder){ await openCurrentOutputFolder(); return; }
  addMsg('assistant','Todavía no hay nada para descargar.');
}

async function openCurrentOutputFolder(){
  let folder = currentOutputFolder || currentConversationFolder || settingsCache.workspace || '';
  if(!folder){
    addMsg('assistant','No hay carpeta activa todavía. Crea un archivo o selecciona una carpeta de chat.');
    return;
  }
  try{
    if(window.arkeaDesktop?.openPath) await window.arkeaDesktop.openPath(folder);
    else alert(folder);
  }catch(e){
    addMsg('assistant','No pude abrir carpeta: ' + e.message);
  }
}



function openCanvasEditor(initial=''){
  currentPreviewKind='canvas';
  const content = initial || 'Escribe, pega o selecciona texto aquí. Luego puedes decir: redacta esto, mejora esta parte o exporta a Word/HTML.';
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
  body{margin:0;background:#eefbf4;font-family:Segoe UI,Arial;color:#172033}.top{position:sticky;top:0;background:#0f6b45;color:#fff;padding:12px 18px;display:flex;gap:12px;align-items:center;z-index:5}.paper{width:min(820px,92%);min-height:860px;margin:24px auto;background:white;padding:58px;box-shadow:0 16px 60px #0003;border:1px solid #dbe4f0;line-height:1.7}.paper:focus{outline:3px solid #10b981}button{border:0;border-radius:12px;background:#10b981;color:white;padding:8px 12px}</style></head><body><div class="top"><b>Canvas editable ARKEA</b><span>Selecciona texto y pídele cambios por voz o chat.</span></div><main id="arkeaCanvas" class="paper" contenteditable="true">${esc(content)}</main></body></html>`;
  setPreviewHtml(html); setPreviewLabel('Canvas editable');
}
function getCanvasSelectionText(){
  try{
    if(currentPreviewKind !== 'canvas') return '';
    const sel = viewer.contentWindow?.getSelection?.();
    return String(sel || '').trim();
  }catch{return '';}
}
function replaceCanvasSelection(text){
  try{
    if(currentPreviewKind !== 'canvas') return false;
    const doc = viewer.contentDocument;
    const sel = viewer.contentWindow.getSelection();
    if(!sel || !sel.rangeCount) return false;
    const range = sel.getRangeAt(0);
    range.deleteContents();
    range.insertNode(doc.createTextNode(text));
    sel.removeAllRanges();
    return true;
  }catch{return false;}
}

function cleanAssistantSay(text='', data={}){
  let t = String(text || '').trim();
  if(/^<!doctype html|^<html|<head[\s>]|<body[\s>]/i.test(t)){
    return data.file ? 'Listo. Creé el archivo y lo mostré en la vista previa.' : 'Listo. Actualicé la vista visual.';
  }
  if(t.length > 420) t = t.slice(0, 420).trim() + '…';
  return t || 'Listo.';
}

async function send(){
  const promptEl = $('#prompt');
  const sendBtn = $('#send');
  if(window.__arkeaSending) return;
  let text = (promptEl?.value || '').trim();
  const canvasSelection = getCanvasSelectionText();
  if(canvasSelection && /redacta|reescribe|mejora|corrige|cambia|modifica|amplia|resume/i.test(text)){
    text += `\n\n[SELECCIÓN DEL CANVAS]\n${canvasSelection}`;
  }
  if(!text && !uploadedContexts.length) return;
  let backendText = text;
  if(uploadedContexts.length){
    const ctx = uploadedContexts.map(f => ({
      archivo:f.filename, tipo:f.kind, ruta:f.path, url:f.url,
      texto:f.extracted_text ? f.extracted_text.slice(0,6000) : '',
      vision:f.vision_text || ''
    }));
    backendText += "\n\n[CONTEXTO DE ARCHIVOS SUBIDOS PARA USAR EN LA RESPUESTA]\n" + JSON.stringify(ctx, null, 2);
  }
  window.__arkeaSending = true;
  sendingMessage = true;
  const oldSendText = sendBtn?.textContent || 'Enviar';
  if(sendBtn){ sendBtn.disabled = true; sendBtn.textContent = '⏳ Enviando'; }
  addMsg('user', text || 'Analiza los archivos subidos.');
  const thinking = addMsg('assistant', '⚡ ARKEA está respondiendo...');
  if(promptEl) promptEl.value = '';
  setLiveStatus((currentLangProfile().ui||ARKEA_LANGS.es.ui).thinking, true);
  startLiveBuildPreview(text || 'Analiza los archivos subidos');
  if(isVisionQuestion(text)){
    const handled = await answerCurrentVisionQuestion(text, thinking);
    if(handled){ window.__arkeaSending = false; sendingMessage = false; if(sendBtn){ sendBtn.disabled = false; sendBtn.textContent = oldSendText; } promptEl?.focus(); return; }
  }
  try{
    const controller = new AbortController();
    const timeout = setTimeout(()=>controller.abort(), Number(settingsCache.chat_timeout_ms || 120000));
    const data = await j('/api/arkea/chat',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:backendText, mode: visualMode ? 'visual_html' : 'auto', conversation_id: currentConversationId, project_id: currentProjectId}),
      signal: controller.signal
    });
    clearTimeout(timeout);
    if(data.conversation_id) currentConversationId = data.conversation_id;
    if(data.folder_path) currentOutputFolder = data.folder_path;
    else if(data.project?.folder_path) currentOutputFolder = data.project.folder_path;
    if(data.project?.id) currentProjectId = data.project.id;
    if(data.file) currentOutputFile = data.file;
    if(data.download_url) currentDownloadUrl = data.download_url;
    if(thinking) thinking.remove();
    const assistantText = cleanAssistantSay(data.say || '', data);
    addMsg('assistant', assistantText);
    stopLiveBuildPreview();
    if(data.image?.url){ currentDownloadUrl = data.image.url; currentOutputFile = data.image.path || currentOutputFile; setPreviewImage(data.image.url, 'Imagen generada'); }
    else if(data.pdf_preview_url){ setPreviewUrl(data.pdf_preview_url, 'Vista LibreOffice/PDF'); }
    else if(data.html_content){ setPreviewHtml(data.html_content); setPreviewLabel('Respuesta visual'); }
    else if(data.preview_url){ setPreviewUrl(data.preview_url, data.project?.name || 'Vista previa'); }
    else if(data.file || data.download_url){ renderGeneratedFilePreview(data); }
    if(canvasSelection && currentPreviewKind === 'canvas' && /redacta|reescribe|mejora|corrige|cambia|modifica|amplia|resume/i.test(text)){
      replaceCanvasSelection(assistantText);
    }
    if(canvasSelection && currentPreviewKind === 'canvas' && /redacta|reescribe|mejora|corrige|cambia|modifica|amplia|resume/i.test(text)){
      replaceCanvasSelection(assistantText);
    }
    if($('#voiceOut')?.checked) speak(assistantText);
    refreshSideChats().catch(()=>{});
  }catch(e){
    if(thinking) thinking.remove();
    stopLiveBuildPreview();
    const msg = e.name === 'AbortError'
      ? 'La solicitud tardó demasiado y fue cancelada para no congelar ARKEA. Prueba un modelo/API recomendado o aumenta el tiempo en Ajustes.'
      : 'Error enviando mensaje: ' + e.message;
    addMsg('assistant', msg);
    setPreviewHtml(`<!doctype html><html><body style="font-family:Segoe UI,Arial;padding:24px;background:#07111f;color:#e5f1ff"><h1>ARKEA AI</h1><p>${esc(msg)}</p></body></html>`);
  }finally{
    stopLiveBuildPreview();
    setLiveStatus((currentLangProfile().ui||ARKEA_LANGS.es.ui).live, false);
    window.__arkeaSending = false;
    sendingMessage = false;
    if(sendBtn){ sendBtn.disabled = false; sendBtn.textContent = oldSendText; }
    promptEl?.focus();
  }
}
window.send = send;

function encodeWAV(samples, sampleRate){
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const wstr = (o,s) => { for(let i=0;i<s.length;i++) view.setUint8(o+i,s.charCodeAt(i)); };
  const w32 = (o,v) => view.setUint32(o,v,true);
  const w16 = (o,v) => view.setUint16(o,v,true);
  wstr(0,'RIFF'); w32(4,36+samples.length*2); wstr(8,'WAVE'); wstr(12,'fmt '); w32(16,16); w16(20,1); w16(22,1); w32(24,sampleRate); w32(28,sampleRate*2); w16(32,2); w16(34,16); wstr(36,'data'); w32(40,samples.length*2);
  let off = 44;
  for(let i=0;i<samples.length;i++,off+=2){ const s = Math.max(-1,Math.min(1,samples[i])); view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7FFF, true); }
  return new Blob([view], {type:'audio/wav'});
}
function flatten(chunks){
  const len = chunks.reduce((a,c)=>a+c.length,0);
  const out = new Float32Array(len);
  let o = 0; chunks.forEach(c=>{out.set(c,o); o+=c.length;});
  return out;
}
async function startVoiceRecording(){
  if(recording) return stopVoiceRecording();
  try{
    micStream = await navigator.mediaDevices.getUserMedia({audio:true});
    audioCtx = new (window.AudioContext || window.webkitAudioContext)({sampleRate:16000});
    const source = audioCtx.createMediaStreamSource(micStream);
    processor = audioCtx.createScriptProcessor(4096,1,1);
    chunks = [];
    voiceStarted = false; silenceStart = 0; recordingStartedAt = performance.now();
    processor.onaudioprocess = e => {
      const data = new Float32Array(e.inputBuffer.getChannelData(0));
      chunks.push(data);
      let sum = 0;
      for(let i=0;i<data.length;i++) sum += data[i]*data[i];
      const rms = Math.sqrt(sum / data.length);
      const now = performance.now();
      if(rms > Number(settingsCache.voice_rms_threshold || 0.006)){ 
        voiceStarted = true;
        silenceStart = 0;
      }else if(voiceStarted && now - recordingStartedAt > 4500){
        if(!silenceStart) silenceStart = now;
        if((settingsCache.auto_stop_voice === '1' || settingsCache.auto_stop_voice === 'true') && now - silenceStart > Number(settingsCache.voice_silence_ms || 12000) && recording){
          stopVoiceRecording();
        }
      }
    };
    source.connect(processor); processor.connect(audioCtx.destination);
    recording = true; setAvatarState('listening'); $('#talkBtn').textContent = 'Detener y enviar'; $('#avatarCaption').textContent='Escuchando sin cortar. Pulsa Detener y enviar cuando termines.';
    setTimeout(()=>{ if(recording) stopVoiceRecording(); }, Number(settingsCache.max_voice_seconds || 1800) * 1000);
  }catch(e){ addMsg('assistant','No pude acceder al micrófono: ' + e.message); showMicGuide(); }
}
async function stopVoiceRecording(autoSend=true){
  try{
    recording = false; $('#talkBtn').textContent = '🎙️ Hablar'; setAvatarState('idle');
    if(processor) processor.disconnect(); if(audioCtx) await audioCtx.close(); if(micStream) micStream.getTracks().forEach(t=>t.stop());
    const samples = flatten(chunks);
    if(samples.length < 1000) return addMsg('assistant','No escuché audio suficiente.');
    const blob = encodeWAV(samples, 16000);
    const fd = new FormData(); fd.append('file', blob, 'voz.wav'); fd.append('language', (settingsCache.input_language || 'es-ES').slice(0,2));
    addMsg('assistant','Transcribiendo voz...');
    const r = await fetch('/api/arkea/voice/transcribe',{method:'POST',body:fd});
    const data = await r.json();
    if(!data.ok){ addMsg('assistant','No pude transcribir: ' + (data.error || data.help || 'Configura STT/Whisper.')); return; }
    const text = (data.text || '').trim();
    if(!text) return addMsg('assistant','No detecté palabras.');
    $('#prompt').value = text;
    if(autoSend && $('#autoListen').checked){
      await send();
    }else{
      addMsg('user','🎙️ ' + text);
    }
  }catch(e){ addMsg('assistant','No pude escuchar: ' + e.message); }
}
function showMicGuide(){
  openSettingsTab('apis');
  alert('Arkea ya no usa SpeechRecognition de Chromium. Si falla la voz: 1) activa micrófono en Windows, 2) en APIS configura voice_stt o pulsa Descargar/activar Whisper tiny, 3) reinicia la app si Windows cambió permisos.');
  if(window.arkeaDesktop?.openMicSettings) window.arkeaDesktop.openMicSettings();
}

async function toggleCameraLive(btn){
  if(cameraLiveTimer){
    stopCameraLive();
    if(btn) btn.textContent = '📷 Cámara';
    return;
  }
  if(btn) btn.textContent = '⏳ Cámara...';
  try{
    await startCameraLive();
    if(btn) btn.textContent = '⏹️ Detener cámara';
  }catch(e){
    addMsg('assistant','No pude activar cámara: ' + e.message + '. Revisa permisos de cámara en Windows.');
    if(btn) btn.textContent = '📷 Cámara';
  }
}

async function startCameraLive(){
  cameraLiveActive = true; cameraLiveToken += 1; const localCameraToken = cameraLiveToken; lastCameraFrame = '';
  try{ $('#stopCameraTop').hidden = false; }catch{}

  if(cameraStream) cameraStream.getTracks().forEach(t=>t.stop());
  cameraStream = await navigator.mediaDevices.getUserMedia({video:{width:{ideal:960},height:{ideal:540}},audio:false});
  const video = document.createElement('video');
  video.srcObject = cameraStream;
  video.muted = true;
  await video.play();
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d', {willReadFrequently:false});
  addMsg('assistant','📷 Cámara en tiempo real activada. Muéstrame un objeto y lo iré revisando rápido.');
  async function tick(){
    if(!cameraLiveActive || !cameraStream || localCameraToken !== cameraLiveToken) return;
    try{
      canvas.width = video.videoWidth || 960;
      canvas.height = video.videoHeight || 540;
      ctx.drawImage(video,0,0,canvas.width,canvas.height);
      const dataUrl = canvas.toDataURL('image/jpeg',0.72);
      if(!cameraLiveActive || localCameraToken !== cameraLiveToken) return;
      lastCameraFrame = dataUrl;
      showImageInPreview(dataUrl, 'Cámara en vivo');
      const now = Date.now();
      if(now - lastCameraAnalyze > 8000){
        lastCameraAnalyze = now;
        visionRequest({image_data_url:dataUrl, source:'camera-live', prompt:'Identifica objetos principales visibles. Responde muy breve en español.'}, 35000)
          .then(res => { if(res.say) addVisionMsg('Cámara:', cleanVisionClientText(res.say)); })
          .catch(()=>{});
      }
    }catch(e){
      addMsg('assistant','Error cámara en vivo: ' + e.message);
      stopCameraLive();
    }
  }
  await tick();
  cameraLiveTimer = setInterval(tick, 900);
}

function stopCameraLive(showMessage=true){
  cameraLiveActive=false; cameraLiveToken += 1; lastCameraFrame=''; lastCameraAnalyze=0; abortLiveRequests();
  try{ $('#stopCameraTop').hidden=true; }catch{}
  if(cameraLiveTimer){ clearInterval(cameraLiveTimer); cameraLiveTimer=null; }
  if(cameraStream){ cameraStream.getTracks().forEach(t=>t.stop()); cameraStream=null; }
  const b=$('#cameraBtn'); if(b) b.textContent='📷 Cámara';
  setStoppedPreview('Cámara detenida');
  if(showMessage) addMsg('assistant','Cámara en vivo detenida. Ya no estoy capturando cámara.');
}


async function captureFrame(kind){
  if(kind === 'screen') return openScreenPicker();
  try{
    const stream = await navigator.mediaDevices.getUserMedia({video:true,audio:false});
    const video = document.createElement('video');
    video.srcObject = stream;
    await video.play();
    await new Promise(r=>setTimeout(r,700));
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 1280; canvas.height = video.videoHeight || 720;
    canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);
    stream.getTracks().forEach(t=>t.stop());
    const dataUrl = canvas.toDataURL('image/jpeg',0.85);
    showImageInPreview(dataUrl, 'Cámara capturada');
    addMsg('user','📷 Analiza lo que ve mi cámara');
    const res = await j('/api/arkea/vision/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image_data_url:dataUrl, source:'camera', prompt:'Describe exactamente lo que ves en la cámara. Si hay objetos como lápiz, hoja, planta, texto o persona, identifícalos. Responde en español.'})});
    const clean = cleanVisionClientText(res.say || JSON.stringify(res));
    addMsg('assistant', clean);
    await speak(clean || 'Ya analicé la cámara.');
  }catch(e){ addMsg('assistant','No pude capturar cámara: ' + e.message + '. Revisa permisos de cámara en Windows.'); }
}
async function openScreenPicker(){
  if(!window.arkeaDesktop?.listScreenSources){
    return addMsg('assistant','Captura avanzada no disponible en esta compilación.');
  }
  $('#screenPickerModal').hidden = false;
  await loadScreenSources();
}
async function loadScreenSources(){
  const box = $('#screenSources');
  box.innerHTML = '<p>Cargando pantallas y ventanas...</p>';
  const r = await window.arkeaDesktop.listScreenSources();
  if(r?.error) return box.innerHTML = `<p class="danger-text">${esc(r.error)}</p>`;
  const sources = r.sources || [];
  if(!sources.length) return box.innerHTML = '<p>No hay fuentes disponibles.</p>';
  box.innerHTML = sources.map(src => `<button class="screen-source" data-action="choose-screen-source" data-id="${esc(src.id)}" data-name="${esc(src.name)}"><img src="${esc(src.thumbnail)}"/><span>${esc(src.name)}</span></button>`).join('');
}
async function chooseScreenSource(id, name){
  currentScreenSourceId = id;
  $('#screenPickerModal').hidden = true;
  addMsg('assistant','Pantalla en vivo activada: ' + name + '. Vuelve a pulsar Pantalla para cambiar de fuente.');
  startScreenLive(id, $('#screenAutoAnalyze')?.checked ?? true);
}
async function startScreenLive(id, autoAnalyze=true){
  screenLiveActive = true; screenLiveToken += 1; const localScreenToken = screenLiveToken; currentScreenSourceId = id; lastScreenFrame = ''; lastScreenName = '';
  try{ $('#stopScreenTop').hidden = false; }catch{}

  if(screenLiveTimer) clearInterval(screenLiveTimer);
  async function tick(){
    if(!screenLiveActive || currentScreenSourceId !== id || localScreenToken !== screenLiveToken) return;
    try{
      const r = await window.arkeaDesktop.captureScreenSource(id);
      if(!screenLiveActive || currentScreenSourceId !== id || localScreenToken !== screenLiveToken) return;
      if(r?.canceled || r?.error){ addMsg('assistant','No pude capturar pantalla: ' + (r.error || 'cancelado')); clearInterval(screenLiveTimer); return; }
      lastScreenFrame = r.dataUrl; lastScreenName = r.name || 'fuente';
      showImageInPreview(r.dataUrl, 'Pantalla en vivo: ' + (r.name || 'fuente'));
      const now = Date.now();
      if(autoAnalyze && now - lastScreenAnalyze > 8000){
        lastScreenAnalyze = now;
        visionRequest({image_data_url:r.dataUrl, source:'screen-live', prompt:'Identifica objetos/texto principal de la pantalla. Responde muy breve en español.'}, 35000)
          .then(res => { if(res.say) addVisionMsg('Pantalla:', cleanVisionClientText(res.say)); })
          .catch(()=>{});
      }
    }catch(e){ addMsg('assistant','Error pantalla en vivo: ' + e.message); clearInterval(screenLiveTimer); }
  }
  await tick();
  screenLiveTimer = setInterval(tick, 1500);
}
function stopScreenLive(showMessage=true){
  screenLiveActive=false; screenLiveToken += 1; currentScreenSourceId=''; lastScreenFrame=''; lastScreenName=''; lastScreenAnalyze=0; abortLiveRequests();
  try{ $('#stopScreenTop').hidden=true; }catch{}
  if(screenLiveTimer){ clearInterval(screenLiveTimer); screenLiveTimer=null; }
  setStoppedPreview('Pantalla detenida');
  if(showMessage) addMsg('assistant','Pantalla en vivo detenida. Ya no estoy capturando pantalla.');
}

async function createNewChat(title='', folderPath=''){
  let folder = folderPath;
  if(!folder){
    if(window.arkeaDesktop?.selectFolder){
      const r = await window.arkeaDesktop.selectFolder();
      if(r?.canceled) return;
      folder = r.path || '';
    } else {
      folder = prompt('Ruta de carpeta para este chat:', settingsCache.workspace || '') || '';
    }
  }
  if(!folder) return;
  let name = title || ('Chat en ' + (folder.split(/[\\/]/).filter(Boolean).pop() || 'carpeta'));
  const c = await j('/api/arkea/conversations/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:name, folder_path:folder})});
  currentConversationId = c.id; currentProjectId = null; currentConversationFolder = c.folder_path || folder;
  await saveSetting('workspace', folder);
  messages.innerHTML = `<div class="msg system">Nuevo chat: ${esc(name)}. Carpeta: ${esc(c.folder_path || folder)}</div>`;
  setPreviewHtml('<!doctype html><html><body style="font-family:Arial;padding:24px"><h1>Chat listo</h1><p>Carpeta activa: '+esc(c.folder_path || folder)+'</p></body></html>');
  setPreviewLabel('Chat activo');
  addMsg('assistant','Listo, trabajaré en esta carpeta: ' + (c.folder_path || folder));
  await refreshSideChats();
  if(!viewer.srcdoc && !viewer.src){ setPreviewHtml('<!doctype html><html><body style="font-family:Arial;padding:24px;background:#07111f;color:#e5f1ff"><h1>ARKEA AI</h1><p>Escribe o habla para empezar.</p></body></html>'); setPreviewLabel('Respuesta visual'); }
  warmOllamaFast();
  autoBootstrapRuntime();
  await showOnboardingIfNeeded();
}
async function openConversation(id){
  const d = await j(`/api/arkea/conversations/${id}/messages`);
  const active = await j(`/api/arkea/conversations/${id}/active`,{method:'POST'});
  currentConversationId = id;
  currentConversationFolder = active.folder_path || '';
  if(currentConversationFolder) await saveSetting('workspace', currentConversationFolder);
  messages.innerHTML = '';
  (d.messages || []).forEach(m => addMsg(m.role, m.content));
  setPreviewLabel('Chat activo');
  await refreshSideChats();
  if(!viewer.srcdoc && !viewer.src){ setPreviewHtml('<!doctype html><html><body style="font-family:Arial;padding:24px;background:#07111f;color:#e5f1ff"><h1>ARKEA AI</h1><p>Escribe o habla para empezar.</p></body></html>'); setPreviewLabel('Respuesta visual'); }
  warmOllamaFast();
  await showOnboardingIfNeeded();
}
async function refreshSideChats(){
  try{
    const d = await j('/api/arkea/conversations');
    const current = (d.conversations || []).find(c=>c.active) || {};
    currentConversationId = current.id || currentConversationId;
    currentConversationFolder = current.folder_path || currentConversationFolder;
    if(!currentConversationFolder && settingsCache.workspace) currentConversationFolder = settingsCache.workspace;
    $('#sideList').innerHTML = `
      <div class="side-block">
        <b>Chat actual:</b><br>${esc(current.title || 'Nuevo chat')}<br>
        <small>${esc(current.folder_path || '')}</small>
        <div class="side-actions">
          <button data-action="new-chat">Nuevo chat</button>
          <button data-action="choose-folder">Cambiar carpeta</button>
          <button data-action="open-folder" data-path="${esc(current.folder_path || settingsCache.workspace || '')}">Abrir carpeta</button>
        </div>
      </div>` +
      (d.conversations || []).map(c=>`<button class="chat-item ${c.active?'active':''}" data-action="open-chat" data-id="${c.id}"><b>${esc(c.title)}</b><small>${esc(c.folder_path || '')}</small></button>`).join('');
  }catch(e){ console.warn(e); }
}
async function openPath(p){
  if(!p) return alert('No hay carpeta o archivo seleccionado.');
  if(window.arkeaDesktop?.openPath) return window.arkeaDesktop.openPath(p);
  alert(p);
}
async function chooseWorkspaceAndNewChat(){
  let path = '';
  if(window.arkeaDesktop?.selectFolder){ const r = await window.arkeaDesktop.selectFolder(); if(r?.canceled) return; path = r.path || ''; }
  else path = prompt('Ruta de carpeta de trabajo:', settingsCache.workspace || '') || '';
  if(!path) return;
  await createNewChat('', path);
}

async function openSettingsTab(tab='workspace'){
  await loadSettings();
  $('#settingsModal').hidden = false;
  $$('.settings-tabs button').forEach(b=>b.classList.toggle('active', b.dataset.tab === tab));
  if(tab === 'workspace') return renderWorkspace();
  if(tab === 'chat') return renderChatSettings();
  if(tab === 'apis') return renderApis();
  if(tab === 'models') return renderModels();
  if(tab === 'avatar') return renderAvatar();
  if(tab === 'skills') return renderSkills();
  if(tab === 'memory') return renderMemory();
  if(tab === 'mcp') return renderMcp();
  if(tab === 'appearance') return renderAppearance();
  if(tab === 'diagnostics') return renderDiagnostics();
}
function closeSettings(){ $('#settingsModal').hidden = true; }
async function renderWorkspace(){
  const p = await j('/api/arkea/projects');
  $('#settingsContent').innerHTML = `<h3>📁 Proyectos y carpeta</h3>
  <div class="card ok"><b>Carpeta actual</b><div class="path">${esc(settingsCache.workspace || '')}</div><div class="actions"><button data-action="choose-folder">Cambiar carpeta + nuevo chat</button><button data-action="open-folder" data-path="${esc(settingsCache.workspace || '')}">Abrir carpeta</button><button data-action="new-chat">Nuevo chat</button></div></div>
  ${(p.projects || []).map(x=>`<div class="card"><b>${esc(x.name)}</b><p>${esc(x.type)}</p><div class="path">${esc(x.folder_path)}</div><div class="actions"><button data-action="open-folder" data-path="${esc(x.folder_path)}">Abrir</button><button data-action="preview" data-url="/api/arkea/projects/${x.id}/preview" data-label="${esc(x.name)}">Preview</button></div></div>`).join('') || '<p>Sin proyectos.</p>'}`;
}
function loadPreview(url,label){ currentPreviewUrl = url; viewer.src = url; setPreviewLabel(label); closeSettings(); }
async function renderChatSettings(){
  const d = await j('/api/arkea/conversations');
  $('#settingsContent').innerHTML = `<h3>💬 Chat actual y anteriores</h3><div class="actions"><button data-action="new-chat">Nuevo chat con carpeta</button><button data-action="choose-folder">Cambiar carpeta del chat</button></div>` +
    (d.conversations || []).map(c=>`<div class="card"><b>${esc(c.title)}</b><div class="path">${esc(c.folder_path || '')}</div><div class="actions"><button data-action="open-chat" data-id="${c.id}">Abrir chat</button><button data-action="open-folder" data-path="${esc(c.folder_path || '')}">Abrir carpeta</button></div></div>`).join('');
}
async function renderApis(){
  const apis = await j('/api/arkea/apis');
  window.apiTemplates = await j('/api/arkea/apis/templates');
  const types = window.apiTemplates.types || [];
  $('#settingsContent').innerHTML = `<h3>🔑 APIS</h3><p class="muted">Guarda cada API por separado. Los campos pueden quedar vacíos si tu proveedor no los necesita.</p>
  <div class="form-grid card"><div><label>Tipo</label><select id="api_type">${types.map(t=>`<option value="${t}">${t}</option>`).join('')}</select></div><div><label>Proveedor</label><select id="api_provider_select"></select></div><div><label>Nombre visible</label><input id="api_display_name" placeholder="Mi API"/></div><div><label>Base URL / endpoint</label><input id="api_base_url_new" placeholder="https://..."/></div><div><label>API Key</label><input id="api_key_new" type="password" placeholder="opcional"/></div><div><label>Model ID</label><input id="api_model_id_new" placeholder="modelo"/></div><div class="full"><label>Extra JSON opcional</label><textarea id="api_extra_new" placeholder='{"voice_id":"..."}'></textarea></div><button data-action="save-api" class="primary">Guardar esta API</button></div>
  <div class="card ok">
    <h3>🚀 Recomendaciones ARKEA por plantillas</h3>
    <p>Coloca tu <b>OpenRouter API Key</b> y ARKEA guardará APIs separadas para chat, visión, web, archivos, código, artefactos e imagen SVG/PNG. Si también pones OpenAI Image API Key, ARKEA genera imágenes reales con gpt-image-1.</p>
    <div class="form-grid">
      <div class="full"><label>OPENROUTER_API_KEY</label><input id="openrouterKeyQuick" type="password" placeholder="sk-or-v1-..."/></div>
      <div class="full"><label>OPENAI_IMAGE_API_KEY opcional para imágenes reales</label><input id="openaiImageKeyQuick" type="password" placeholder="sk-... opcional. Si no la pones, ARKEA usa OpenRouter para SVG/PNG."/></div>
      <button data-action="apply-api-preset" data-preset="arkea_openrouter_free" class="primary">Aplicar GRATIS estable</button>
      <button data-action="apply-api-preset" data-preset="arkea_openrouter_cheap">Aplicar barato recomendado</button>
      <button data-action="apply-api-preset" data-preset="arkea_openrouter_env_compat">Aplicar plantilla tipo ENV anterior</button>
    </div>
    <p class="muted">Incluye modelos actuales: openrouter/free, nex-agi/nex-n2-pro:free, qwen/qwen3-coder:free, nvidia/nemotron-3-ultra-550b-a55b:free, deepseek/deepseek-v4-flash, qwen/qwen3-coder-flash, xiaomi/mimo-v2.5 y stepfun/step-3.7-flash.</p>
  </div>
  <div class="card">
    <h3>👁️ Visión con internet para pantalla/cámara</h3>
    <p>Para ver pantalla/cámara con internet usa una API tipo <b>vision</b>. La plantilla GRATIS ya crea Nex/Qwen/Nemotron sin usar Gemini :free ni Xiaomi inválido.</p>
    <button onclick="document.getElementById('api_type').value='vision'; fillProviders(); document.getElementById('api_provider_select').value='openrouter_nex_vision_free'; document.getElementById('api_provider_select').onchange();">Llenar visión gratis Nex</button>
    <button onclick="document.getElementById('api_type').value='vision'; fillProviders(); document.getElementById('api_provider_select').value='openrouter_vision_step_flash'; document.getElementById('api_provider_select').onchange();">Llenar visión barata StepFun</button>
  </div>
  <h3>Guardadas</h3><div class="actions"><button data-action="cleanup-apis">Limpiar APIs rotas</button></div>${(apis.apis || []).map(a=>`<div class="card"><b>${esc(a.api_type)} / ${esc(a.provider)} / ${esc(a.display_name)}</b><p>${esc(a.model_id || 'sin modelo')}</p><div class="path">${esc(a.base_url || '')}</div><div class="actions"><button data-action="test-api" data-id="${a.id}">Probar API</button><button data-action="delete-api" data-id="${a.id}">Eliminar</button></div><div id="api-test-${a.id}" class="muted"></div></div>`).join('') || '<p>Sin APIs guardadas.</p>'}
  <h3>ElevenLabs rápido</h3><div class="card form-grid"><input id="elevenlabs_voice_name" placeholder="Nombre de voz" value="${esc(settingsCache.elevenlabs_voice_name || '')}"/><input id="elevenlabs_voice_id" placeholder="Voice ID" value="${esc(settingsCache.elevenlabs_voice_id || '')}"/><input id="elevenlabs_api_key" type="password" placeholder="API Key" value="${esc(settingsCache.elevenlabs_api_key || '')}"/><select id="use_elevenlabs_voice"><option value="0">No usar por defecto</option><option value="1">Usar ElevenLabs por defecto</option></select><button data-action="save-eleven">Guardar ElevenLabs</button><button data-action="load-eleven-voices">Ver voces de mi cuenta</button><div id="elevenVoiceList" class="full"></div></div>
  <div class="card"><button data-action="install-whisper">Descargar/activar Whisper tiny local</button><p class="muted">El botón Hablar graba audio WAV y usa voice_stt API o faster-whisper local. No depende de Chromium.</p></div>`;
  $('#use_elevenlabs_voice').value = settingsCache.use_elevenlabs_voice || '0';
  $('#api_type').onchange = fillProviders; fillProviders();
}

async function applyApiPreset(presetId){
  const templates = window.apiTemplates || await j('/api/arkea/apis/templates');
  const preset = (templates.recommended_presets || []).find(p => p.id === presetId);
  if(!preset) return alert('No encontré la plantilla.');
  let key = ($('#openrouterKeyQuick')?.value || '').trim();
  if(preset.needs_key && !key){
    key = prompt('Pega tu OPENROUTER_API_KEY para aplicar esta plantilla:') || '';
  }
  if(preset.needs_key && !key) return;
  try{ await j('/api/arkea/apis/cleanup-broken',{method:'POST'}); }catch{}
  let saved = 0, failed = 0;
  const openaiImageKey = ($('#openaiImageKeyQuick')?.value || '').trim();
  for(const item of (preset.items || [])){
    try{
      await j('/api/arkea/apis/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
        api_type:item.api_type,
        provider:item.provider,
        display_name:item.display_name || item.provider,
        base_url:preset.base_url || item.base_url || 'https://openrouter.ai/api/v1/chat/completions',
        api_key:key,
        model_id:item.model_id,
        extra:item.extra || {},
        enabled:true
      })});
      saved++;
    }catch(e){ failed++; }
  }
  if(openaiImageKey){
    try{ await j('/api/arkea/apis/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_type:'image_generation',provider:'openai_images',display_name:'ARKEA imagen real OpenAI',base_url:'https://api.openai.com/v1/images/generations',api_key:openaiImageKey,model_id:'gpt-image-1',extra:{size:'1024x1024'},enabled:true})}); saved++; }catch(e){ failed++; }
  }
  await saveBulk({
    router_mode:'auto',
    openrouter_model:'deepseek/deepseek-v4-flash',
    stream_model:'deepseek/deepseek-v4-flash',
    openrouter_file_model:'openrouter/auto',
    max_tokens:'2200',
    artifact_max_tokens:'3600',
    stream_artifact_max_tokens:'4500',
    stream_timeout_ms:'75000',
    enable_web_search:'true',
    save_messages:'false',
    save_uploads:'false'
  });
  alert(`Plantilla aplicada. Guardadas: ${saved}. Fallidas: ${failed}. Se desactivaron APIs rotas anteriores si existían.`);
  openSettingsTab('apis');
}

function fillProviders(){
  const type = $('#api_type').value || 'chat';
  const arr = (window.apiTemplates?.providers?.[type] || [{provider:'custom',base_url:'',model:''}]);
  $('#api_provider_select').innerHTML = arr.map(x=>`<option value="${esc(x.provider)}" data-base="${esc(x.base_url)}" data-model="${esc(x.model)}">${esc(x.provider)}</option>`).join('');
  $('#api_provider_select').onchange = () => { const o = $('#api_provider_select').selectedOptions[0]; $('#api_base_url_new').value = o.dataset.base || ''; $('#api_model_id_new').value = o.dataset.model || ''; $('#api_display_name').value = o.value; };
  $('#api_provider_select').onchange();
}
async function saveApiConnection(){
  let extra = {}; try{ extra = $('#api_extra_new').value.trim() ? JSON.parse($('#api_extra_new').value) : {}; }catch{ return alert('Extra JSON no es válido.'); }
  await j('/api/arkea/apis/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_type:$('#api_type').value,provider:$('#api_provider_select').value,display_name:$('#api_display_name').value || 'default',base_url:$('#api_base_url_new').value,api_key:$('#api_key_new').value,model_id:$('#api_model_id_new').value,extra,enabled:true})});
  alert('API guardada'); openSettingsTab('apis');
}
async function deleteApi(id){ await fetch(`/api/arkea/apis/${id}`,{method:'DELETE'}); openSettingsTab('apis'); }
async function testApiConnection(id){
  const box = document.getElementById('api-test-' + id);
  if(box) box.textContent = 'Probando...';
  try{
    const r = await j(`/api/arkea/apis/${id}/test`, {method:'POST'});
    let raw = String(r.message || r.error || r.raw || JSON.stringify(r));
    let nice = raw;
    if(/<!doctype html|<html|<style|\.term-fg|Weather Report|<body/i.test(raw)){
      nice = r.ok ? 'API conectada. Respondió con HTML/código y se ocultó para no ensuciar la interfaz.' : 'La API devolvió HTML/código en vez de una respuesta limpia.';
    }else{
      nice = raw.replace(/<[^>]*>/g,'').replace(/\s+/g,' ').slice(0,260);
    }
    const msg = (r.ok ? '✅ ' : '❌ ') + nice;
    if(box) box.textContent = msg;
    else alert(msg);
  }catch(e){
    const msg = String(e.message || e).replace(/<[^>]*>/g,'').replace(/\s+/g,' ').slice(0,260);
    if(box) box.textContent = '❌ ' + msg;
    else alert(msg);
  }
}
async function saveElevenQuick(){
  const voiceName = $('#elevenlabs_voice_name').value || 'ElevenLabs voz personalizada';
  const voiceId = $('#elevenlabs_voice_id').value || '';
  const apiKey = $('#elevenlabs_api_key').value || '';
  await saveBulk({elevenlabs_voice_name:voiceName, elevenlabs_voice_id:voiceId, elevenlabs_api_key:apiKey, use_elevenlabs_voice:$('#use_elevenlabs_voice').value});
  if(apiKey && voiceId){
    await j('/api/arkea/apis/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_type:'voice_tts',provider:'elevenlabs',display_name:'ARKEA voz ElevenLabs',base_url:'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',api_key:apiKey,model_id:voiceId,extra:{voice_id:voiceId, voice_name:voiceName, model_id:'eleven_multilingual_v2'},enabled:true})});
  }
  await loadVoices(); alert('ElevenLabs guardado, conectado y agregado al selector de voz.');
}
async function loadElevenVoicesFromApi(){
  const v = await j('/api/arkea/voice/elevenlabs/voices');
  const box = $('#elevenVoiceList');
  if(v.error) return box.innerHTML = `<p class="danger-text">${esc(v.error)}</p>`;
  box.innerHTML = (v.voices || []).map(x=>`<button class="small" data-action="select-eleven" data-id="${esc(x.voice_id)}" data-name="${esc(x.name)}">${esc(x.name)}</button>`).join('') || '<p>No encontré voces.</p>';
}
async function selectElevenVoice(id,name){ $('#elevenlabs_voice_id').value = id; $('#elevenlabs_voice_name').value = name; await saveElevenQuick(); }
async function installWhisper(){ const r = await j('/api/arkea/voice/install-whisper-default',{method:'POST'}); alert(r.message || JSON.stringify(r)); }
async function renderModels(){
  const d = await j('/api/arkea/ollama/catalog');
  const groups = {'chat':[], 'code':[], 'vision':[], 'image':[], 'voice':[], 'translation':[], 'embedding':[]};
  (d.catalog || []).forEach(m => { (groups[m.category || 'chat'] ||= []).push(m); });
  const isInstalled = !!d.ollama?.installed;
  const isRunning = !!d.ollama?.running;
  const installedModels = (d.ollama?.models || []).map(m => m.name || m.model).filter(Boolean);
  const installedCount = installedModels.length;
  const selected = d.selected || {};
  const opt = (val, current) => `<option value="${esc(val)}" ${val===current?'selected':''}>${esc(val)}</option>`;
  const installedOptions = (current, fallback) => {
    const list = Array.from(new Set([current, fallback, ...installedModels].filter(Boolean)));
    return list.map(x => opt(x, current || fallback)).join('');
  };
  const ollamaStatus = isInstalled
    ? `<div class="card ok"><b>✅ Ollama detectado</b><p>Estado: ${isRunning ? 'ejecutándose' : 'instalado, pero no iniciado'} · Modelos instalados: ${installedCount}</p><div class="actions"><button data-action="refresh-ollama">Actualizar modelos</button><button data-action="install-required-pack">Instalar/actualizar pack automático</button><button data-action="warm-selected-model">Precargar modelo rápido</button><button data-action="search-ollama-models">Buscar modelos en Ollama</button></div></div>`
    : `<div class="card warn"><b>⚠️ Ollama no detectado</b><p>ARKEA intentará usar el instalador incluido. Si Windows pide permiso, acepta una vez.</p><div class="actions"><button data-action="install-ollama">Instalar Ollama incluido</button><button data-action="refresh-ollama">Detectar otra vez</button><button data-action="install-required-pack">Instalar pack automático</button></div></div>`;
  const selector = `<div class="card ok"><b>Modelo activo por tarea</b><p>Elige aquí qué modelo usará ARKEA. Si uno falla, ARKEA usa fallback rápido automáticamente.</p><div class="form-grid"><div><label>Chat rápido</label><select id="preferred_chat">${installedOptions(selected.chat,'gemma3:270m')}</select></div><div><label>Código</label><select id="preferred_code">${installedOptions(selected.code,'qwen2.5-coder:0.5b')}</select></div><div><label>Visión cámara/pantalla</label><select id="preferred_vision">${installedOptions(selected.vision,'moondream:latest')}</select></div><div><label>Memoria/embeddings</label><select id="preferred_embedding">${installedOptions(selected.embedding,'nomic-embed-text')}</select></div><div><label>Whisper local</label><select id="preferred_stt"><option value="tiny" ${selected.stt==='tiny'?'selected':''}>tiny rápido</option><option value="base" ${selected.stt==='base'?'selected':''}>base mejor</option></select></div></div><div class="actions"><button data-action="save-model-prefs" class="primary">Guardar modelos activos</button><button data-action="delete-selected-model">Eliminar modelo de chat seleccionado</button></div></div>`;
  const localBtn = m => {
    if(!m.model_id || m.model_id.includes(':api') || m.model_id.includes(':cloud') || m.model_id.includes(':local')) return '<span class="muted">Configurar desde APIS o herramienta local externa</span>';
    if(m.installed) return `<button disabled>✅ Ya instalado</button>`;
    return `<button data-action="pull-model" data-model="${esc(m.model_id)}">Descargar con 1 clic</button>`;
  };
  const card = m => `<div class="card ${m.recommended_for_this_pc?'ok':'warn'}"><b>${esc(m.title)} — ${esc(m.model_id)}</b><p>${esc(m.notes || '')}</p><p>Categoría: ${esc(m.category || 'general')} · RAM recomendada: ${esc(m.recommended_ram_gb)} GB · Disco aprox: ${esc(m.disk_gb)} GB</p><p>${m.installed?'✅ Instalado':m.recommended_for_this_pc?'✅ Recomendado para esta PC':'⚠️ Recurso exigente para esta PC'}</p>${localBtn(m)}<div id="pull-status-${esc(String(m.model_id || '').replace(/[^a-zA-Z0-9_-]/g,'_'))}" class="muted"></div></div>`;
  const section = (title, key) => `<h3>${title}</h3>${(groups[key]||[]).map(card).join('') || '<p>Sin modelos en esta categoría.</p>'}`;
  $('#settingsContent').innerHTML = `<h3>🧠 Modelos locales Ollama</h3>${ollamaStatus}${selector}<div class="card"><b>PC detectada</b><p>RAM: ${esc(d.specs?.ram_gb)} GB · Disco libre: ${esc(d.specs?.free_disk_gb)} GB · CPU: ${esc(d.specs?.cpu_count)}</p><p>${esc(d.tier?.message || '')}</p></div><div class="card"><label>Descargar por ID de Ollama</label><input id="pullModelId" placeholder="gemma3:270m"/><button data-action="pull-by-id">Descargar modelo</button><div id="pullByIdStatus" class="muted"></div></div>${section('💬 Chat', 'chat')}${section('💻 Código', 'code')}${section('👁️ Visión', 'vision')}${section('🖼️ Imagen', 'image')}${section('🎙️ Voz', 'voice')}${section('🌐 Traducción', 'translation')}${section('🧠 Embedding / memoria', 'embedding')}`;
}

async function saveModelPrefs(){
  const body = {
    chat: $('#preferred_chat')?.value || 'gemma3:270m',
    code: $('#preferred_code')?.value || 'qwen2.5-coder:0.5b',
    vision: $('#preferred_vision')?.value || 'moondream:latest',
    embedding: $('#preferred_embedding')?.value || 'nomic-embed-text',
    stt: $('#preferred_stt')?.value || 'tiny'
  };
  const r = await j('/api/arkea/ollama/models/select',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  addMsg('assistant','✅ Modelos activos guardados: chat=' + body.chat + ', visión=' + body.vision);
  await j('/api/arkea/ollama/models/warm',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model_id:body.chat})}).catch(()=>{});
  openSettingsTab('models');
}
async function deleteSelectedModel(){
  const mid = $('#preferred_chat')?.value;
  if(!mid) return alert('Selecciona un modelo.');
  if(!confirm('¿Eliminar de Ollama el modelo '+mid+'? Podrás descargarlo otra vez.')) return;
  const r = await j('/api/arkea/ollama/models/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model_id:mid})});
  addMsg('assistant',(r.ok?'✅ ':'⚠️ ') + (r.message || JSON.stringify(r)));
  openSettingsTab('models');
}
async function warmSelectedModel(){
  const mid = $('#preferred_chat')?.value || 'gemma3:270m';
  addMsg('assistant','⚡ Precargando modelo activo: ' + mid);
  const r = await j('/api/arkea/ollama/models/warm',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model_id:mid})});
  addMsg('assistant',(r.ok?'✅ ':'⚠️ ') + (r.message || JSON.stringify(r)));
}
function stopAllLive(){
  stopAllGeneration += 1;
  stopLiveBuildPreview();
  abortLiveRequests();
  try{ stopScreenLive(false); }catch{}
  try{ stopCameraLive(false); }catch{}
  try{ if(recording) stopVoiceRecording(false); }catch{}
  try{ speechSynthesis.cancel(); }catch{}
  try{ if(currentAudio){ currentAudio.pause(); currentAudio.currentTime=0; currentAudio=null; } }catch{}
  setAvatarState('idle');
  addMsg('assistant','Todo detenido: pantalla, cámara, voz y reproducción.');
}
async function installRequiredPack(){
  if(activePulls.has('__required_pack__')) return addMsg('assistant','⏳ Ya estoy instalando el pack mínimo.');
  activePulls.add('__required_pack__');
  addMsg('assistant','⏳ Instalando pack mínimo gratis: chat, código, visión, memoria y Whisper tiny. Puede tardar la primera vez.');
  try{
    if(window.arkeaDesktop?.installBundledOllama){ await window.arkeaDesktop.installBundledOllama(); }
    try{ await j('/api/arkea/voice/install-whisper-default',{method:'POST'}); addMsg('assistant','✅ Whisper tiny preparado para transcripción.'); }catch(e){ addMsg('assistant','⚠️ Whisper tiny no se pudo preparar aún: '+e.message); }
    const r = await j('/api/arkea/ollama/pull-required',{method:'POST'});
    addMsg('assistant', r.message || JSON.stringify(r));
    if(r.models){
      r.models.forEach(m => addMsg('assistant', `${m.ok?'✅':'⚠️'} ${m.role || ''} ${m.model || ''}: ${m.message || ''}`));
    }
  }catch(e){
    addMsg('assistant','⚠️ Pack automático pendiente: ' + e.message + '. Si Ollama está descargando modelos, espera y pulsa Actualizar modelos.');
    if(window.arkeaDesktop?.installBundledOllama) window.arkeaDesktop.installBundledOllama();
  }finally{
    activePulls.delete('__required_pack__');
    openSettingsTab('models');
  }
}

async function refreshOllama(){
  addMsg('assistant','⚡ Detectando Ollama rápido...');
  try{ await j('/api/arkea/ollama/refresh',{method:'POST'}); }catch(e){ addMsg('assistant','No pude refrescar Ollama: '+e.message); }
  openSettingsTab('models');
}
async function installOllama(){ const url='https://ollama.com/download/windows'; if(window.arkeaDesktop?.installBundledOllama){ const r = await window.arkeaDesktop.installBundledOllama(); if(r && r.ok){ addMsg('assistant','Abrí el instalador local de Ollama incluido con ARKEA AI.'); return; } } if(window.arkeaDesktop?.openExternal) await window.arkeaDesktop.openExternal(url); else window.open(url,'_blank'); }
async function searchOllamaModels(){ const url='https://ollama.com/search'; if(window.arkeaDesktop?.openExternal) await window.arkeaDesktop.openExternal(url); else window.open(url,'_blank'); }
async function pullDefaults(){
  if(activePulls.has('__defaults__')) return addMsg('assistant','⏳ Ya estoy procesando modelos recomendados.');
  activePulls.add('__defaults__');
  addMsg('assistant','⏳ Descargando modelos recomendados. Esto puede tardar, pero no se repetirá por doble clic.');
  try{
    const r = await j('/api/arkea/ollama/pull-defaults',{method:'POST'});
    addMsg('assistant', r.message || JSON.stringify(r,null,2));
  }catch(e){
    addMsg('assistant','❌ Error: ' + e.message);
  }finally{
    activePulls.delete('__defaults__');
    openSettingsTab('models');
  }
}
async function pullModel(id){
  if(!id) return;
  if(activePulls.has(id)) return addMsg('assistant','⏳ Ese modelo ya se está procesando: ' + id);
  activePulls.add(id);
  const key = String(id).replace(/[^a-zA-Z0-9_-]/g,'_');
  const box = document.getElementById('pull-status-' + key) || document.getElementById('pullByIdStatus');
  if(box) box.textContent = '⏳ Revisando/descargando ' + id + '...';
  addMsg('assistant','⏳ Procesando modelo ' + id + '. El botón queda bloqueado para evitar descargas duplicadas.');
  try{
    const r = await j('/api/arkea/ollama/pull',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model_id:id})});
    const raw = (r.message || r.error || JSON.stringify(r));
    const nice = String(raw).replace(/<[^>]*>/g,'').replace(/\s+/g,' ').slice(0,260);
    const msg = (r.ok ? '✅ ' : '❌ ') + nice;
    if(box) box.textContent = msg;
    addMsg('assistant', msg);
    await speak(msg);
  }catch(e){
    const msg = '❌ Error descargando ' + id + ': ' + e.message;
    if(box) box.textContent = msg;
    addMsg('assistant', msg);
  }finally{
    activePulls.delete(id);
    openSettingsTab('models');
  }
}
async function pullModelById(){ const id = $('#pullModelId').value.trim(); if(id) await pullModel(id); }
function renderAvatar(){
  $('#settingsContent').innerHTML = `<h3>🤖 Personaje</h3><div class="form-grid"><div><label>Nombre del agente</label><input id="agent_name" value="${esc(settingsCache.agent_name || 'Arkea')}"/></div><div><label>Cómo debe llamarte</label><input id="user_name" value="${esc(settingsCache.user_name || 'Manu')}"/></div><div><label>Emoción/tono</label><select id="avatar_emotion"><option value="neutral">Neutral</option><option value="happy">Feliz</option><option value="angry">Enojado</option><option value="annoyed">Molesto</option><option value="excited">Excitado/emocionado</option><option value="serious">Serio</option><option value="calm">Calmado</option></select></div><div class="color-row"><div><label>Fondo 1</label><input type="color" id="avatar_color_1" value="${esc(settingsCache.avatar_color_1 || '#7c3aed')}"/></div><div><label>Fondo 2</label><input type="color" id="avatar_color_2" value="${esc(settingsCache.avatar_color_2 || '#06b6d4')}"/></div><div><label>Ojos</label><input type="color" id="avatar_eye_color" value="${esc(settingsCache.avatar_eye_color || '#ffffff')}"/></div><div><label>Boca</label><input type="color" id="avatar_mouth_color" value="${esc(settingsCache.avatar_mouth_color || '#e0f2fe')}"/></div><div><label>Interior</label><input type="color" id="avatar_inner_color" value="${esc(settingsCache.avatar_inner_color || '#93c5fd')}"/></div></div><div class="full card"><b>Imagen propia</b><div class="actions"><button data-action="avatar-image">Elegir imagen</button><button data-action="avatar-clear">Quitar imagen</button></div></div></div><button data-action="save-avatar" class="primary">Guardar personaje</button>`;
  $('#avatar_emotion').value = settingsCache.avatar_emotion || 'neutral';
  ['avatar_emotion','avatar_color_1','avatar_color_2','avatar_eye_color','avatar_mouth_color','avatar_inner_color'].forEach(id=>$('#'+id).oninput = () => { settingsCache[id] = $('#'+id).value; applyAvatarSettings(); });
}
async function chooseAvatarImage(){ if(!window.arkeaDesktop?.selectImage) return alert('Funciona en la app de escritorio.'); const r = await window.arkeaDesktop.selectImage(); if(r?.canceled) return; await saveBulk({avatar_path:r.path || '', avatar_data_url:r.dataUrl || ''}); openSettingsTab('avatar'); }
async function clearAvatarImage(){ await saveBulk({avatar_path:'', avatar_data_url:''}); openSettingsTab('avatar'); }
async function saveAvatarSettings(){ const values = {agent_name:$('#agent_name').value,user_name:$('#user_name').value,avatar_emotion:$('#avatar_emotion').value,avatar_color_1:$('#avatar_color_1').value,avatar_color_2:$('#avatar_color_2').value,avatar_eye_color:$('#avatar_eye_color').value,avatar_mouth_color:$('#avatar_mouth_color').value,avatar_inner_color:$('#avatar_inner_color').value}; await saveBulk(values); alert('Personaje guardado'); }
async function renderSkills(){
  const d = await j('/api/arkea/skills');
  $('#settingsContent').innerHTML = `<h3>⚡ Skills</h3><div class="card"><label>Crear skill con IA/reglas</label><textarea id="skillPrompt" placeholder="create skill para hacer tesis con estructura UCV..."></textarea><button data-action="create-skill">Crear skill .md</button></div><div class="card"><b>Subir skill .md</b><input type="file" id="skillFile" accept=".md,text/markdown,text/plain"/><button data-action="upload-skill">Subir e instalar Markdown</button></div>${(d.skills || []).map(s=>`<div class="card"><b>${esc(s.name)}</b><p>${esc(s.description || '')}</p><div class="path">${esc(s.folder_path)}</div></div>`).join('') || '<p>Sin skills.</p>'}`;
}
async function createSkillFromSettings(){ const prompt = $('#skillPrompt').value.trim(); if(!prompt) return alert('Escribe qué skill quieres crear.'); const s = await j('/api/arkea/skills/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt})}); alert('Skill creada: ' + (s.name || s.skill_id || 'OK')); openSettingsTab('skills'); }
async function uploadSkillMd(){ const f = $('#skillFile').files[0]; if(!f) return alert('Selecciona un .md'); const fd = new FormData(); fd.append('file', f); fd.append('name', f.name.replace(/\.md$/i,'')); const r = await fetch('/api/arkea/skills/upload-md',{method:'POST',body:fd}); if(!r.ok) return alert(await r.text()); alert('Skill instalada'); openSettingsTab('skills'); }
async function renderMcp(){ const d = await j('/api/arkea/mcp'); const a = await j('/api/arkea/automation/status'); $('#settingsContent').innerHTML = `<h3>🔌 MCP Hub + Automatización</h3><div class="card warn"><b>Control del ordenador y navegador</b><p>${esc(a.message)}</p><button data-action="toggle-control" data-enabled="${!a.computer_control_enabled}">${a.computer_control_enabled?'Desactivar':'Activar'} control de PC</button><button data-action="toggle-browser" data-enabled="${!a.browser_agent_enabled}">${a.browser_agent_enabled?'Desactivar':'Activar'} agente navegador</button></div><div class="form-grid card"><input id="mcp_name" placeholder="photoshop-mcp"/><input id="mcp_command" placeholder="node"/><input id="mcp_args" placeholder='["server.js"]'/><button data-action="add-mcp">Agregar MCP</button></div>${(d.mcp_servers || []).map(m=>`<div class="card"><b>${esc(m.name)}</b><div class="path">${esc(m.command)} ${esc(m.args || '')}</div></div>`).join('') || '<p>Sin MCPs.</p>'}`; }
async function setControl(enabled){ await j('/api/arkea/automation/computer-control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled})}); openSettingsTab('mcp'); }
async function setBrowserAgent(enabled){ await j('/api/arkea/automation/browser-agent',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled})}); openSettingsTab('mcp'); }
async function addMcp(){ const raw = ($('#mcp_args')?.value || '').trim(); let args=[]; if(raw){ try{ args=JSON.parse(raw); if(!Array.isArray(args)) args=[String(args)]; }catch{ args=raw.split(/\s+/).filter(Boolean); } } await j('/api/arkea/mcp/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('#mcp_name').value || 'mcp-personalizado',command:$('#mcp_command').value || 'npx',args})}); openSettingsTab('mcp'); }
async function renderMemory(){ const d = await j('/api/arkea/memory'); const v = await j('/api/arkea/obsidian/vault'); $('#settingsContent').innerHTML = `<h3>🗂️ Memoria local + Obsidian</h3><div class="card ok"><b>Vault Obsidian</b><div class="path">${esc(v.vault || '')}</div><div class="actions"><button data-action="choose-obsidian">Elegir Vault</button><button data-action="open-folder" data-path="${esc(v.vault || '')}">Abrir Vault</button><button data-action="obsidian-note">Nota prueba</button></div></div>${(d.memories || []).map(m=>`<div class="card"><b>${esc(m.scope)}</b> ${esc(m.title || '')}<p>${esc(m.content || '')}</p></div>`).join('') || '<p>Sin memoria.</p>'}`; }
async function chooseObsidianVault(){ let path = ''; if(window.arkeaDesktop?.selectFolder){ const r = await window.arkeaDesktop.selectFolder(); if(r?.canceled) return; path = r.path || ''; } else path = prompt('Ruta Vault:', settingsCache.obsidian_vault || '') || ''; if(!path) return; await j('/api/arkea/obsidian/configure',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path})}); await saveSetting('obsidian_vault', path); openSettingsTab('memory'); }
async function createObsidianTestNote(){ await j('/api/arkea/obsidian/note',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({section:'00_Global',title:'Arkea memoria inicial',content:'Nota creada por Arkea.'})}); alert('Nota creada'); }
function renderAppearance(){
  const custom = settingsCache.ui_background_custom || '';
  $('#settingsContent').innerHTML = `<h3>Apariencia y fondos</h3><div class="card"><label>Tema</label><select id="theme_mode"><option value="jade">Jade Glass (verde)</option><option value="sky">Cielo Aero ARKEA</option><option value="dark">Modo noche Liquid Glass</option><option value="light">Aero Glass claro</option></select><div class="wallpaper-options"><button data-action="bg-valley" class="wallpaper-card ${settingsCache.ui_background_preset!=='sky'&&!custom?'active':''}"><img src="/static/assets/arkea-wallpaper-valley.png"/><span>Valle Jade ARKEA</span></button><button data-action="bg-sky" class="wallpaper-card ${settingsCache.ui_background_preset==='sky'&&!custom?'active':''}"><img src="/static/assets/arkea-wallpaper-sky.png"/><span>Cielo Aero ARKEA</span></button>${custom?`<button class="wallpaper-card active"><img src="${custom}"/><span>Fondo personalizado</span></button>`:''}</div><div class="color-row"><div><label>Acento 1</label><input type="color" id="ui_accent_1" value="${esc(settingsCache.ui_accent_1 || '#10b981')}"/></div><div><label>Acento 2</label><input type="color" id="ui_accent_2" value="${esc(settingsCache.ui_accent_2 || '#22c55e')}"/></div><div><label>Vidrio</label><input type="color" id="ui_glass_tint" value="${esc(settingsCache.ui_glass_tint || '#dff7ff')}"/></div></div><div class="actions"><button data-action="choose-bg-image">Elegir imagen de fondo</button><button data-action="clear-bg-image">Quitar fondo personalizado</button><button data-action="save-appearance" class="primary">Guardar</button></div><p class="muted">Puedes cambiar al fondo de cielo, el valle o subir el que quieras. La miniatura queda visible y el cambio se aplica inmediatamente.</p></div><div class="card"><b>Contacto</b><p>robertmanuchojarapeche@gmail.com<br/>betomanuchobullicio@gmail.com</p></div>`;
  $('#theme_mode').value = settingsCache.theme_mode || 'jade';
  ['theme_mode','ui_accent_1','ui_accent_2','ui_glass_tint'].forEach(id=>$('#'+id).oninput = () => { settingsCache[id] = $('#'+id).value; if(id==='theme_mode'){ settingsCache.ui_background_preset = $('#'+id).value === 'sky' ? 'sky' : (settingsCache.ui_background_preset || 'valley'); } applyTheme(); });
}
async function chooseBackgroundImage(){ if(!window.arkeaDesktop?.selectImage) return alert('Funciona en la app de escritorio.'); const r = await window.arkeaDesktop.selectImage(); if(r?.canceled) return; await saveSetting('ui_background_custom', r.dataUrl || ''); settingsCache.ui_background_custom = r.dataUrl || ''; settingsCache.ui_background_preset = 'custom'; applyTheme(); openSettingsTab('appearance'); }
async function setBackgroundPreset(bg){ await saveBulk({ui_background_preset:bg, ui_background_custom:''}); settingsCache.ui_background_preset=bg; settingsCache.ui_background_custom=''; applyTheme(); openSettingsTab('appearance'); }
async function clearBackgroundImage(){ await saveSetting('ui_background_custom',''); settingsCache.ui_background_custom=''; applyTheme(); openSettingsTab('appearance'); }
async function saveAppearance(){ await saveBulk({theme_mode:$('#theme_mode').value, ui_accent_1:$('#ui_accent_1').value, ui_accent_2:$('#ui_accent_2').value, ui_glass_tint:$('#ui_glass_tint').value, ui_background_preset:settingsCache.ui_background_preset || 'valley', ui_background_custom:settingsCache.ui_background_custom || ''}); applyTheme(); alert('Apariencia guardada'); }

async function renderDiagnostics(){
  $('#settingsContent').innerHTML = `<h3>✅ Diagnóstico de botones y backend</h3>
  <div class="card"><button data-action="run-diagnostics" class="primary">Validar botones uno por uno</button><div id="diagResults" class="path"></div></div>
  <p class="muted">Esta prueba revisa que existan los botones principales, acciones registradas y endpoints básicos. No ejecuta acciones peligrosas.</p>`;
}
async function runDiagnostics(){
  const requiredIds = ['send','talkBtn','cameraBtn','screenBtn','newChat','openSettings','openSettingsTop','stopAllTop','previewLabel','download','voices','prompt'];
  const requiredActions = ['new-chat','choose-folder','open-folder','save-api','test-api','install-ollama','search-ollama-models','pull-by-id','create-skill','upload-skill','choose-obsidian','save-appearance'];
  const results = [];
  for(const id of requiredIds) results.push((document.getElementById(id) ? '✅ ' : '❌ ') + '#' + id);
  const handlerSource = handleAction.toString();
  for(const action of requiredActions){
    const registered = handlerSource.includes(`a === '${action}'`) || handlerSource.includes(`a === "${action}"`);
    results.push((registered ? '✅ ' : '❌ ') + 'action=' + action);
  }
  const endpoints = ['/api/health','/api/arkea/settings','/api/arkea/conversations','/api/arkea/apis','/api/arkea/ollama/catalog'];
  for(const ep of endpoints){
    try{ await j(ep); results.push('✅ ' + ep); }
    catch(e){ results.push('❌ ' + ep + ' → ' + e.message); }
  }
  const box = document.getElementById('diagResults');
  if(box) box.innerHTML = results.map(esc).join('<br>');
}

async function showCode(){ if(viewer.srcdoc){ code.textContent = viewer.srcdoc; code.hidden = false; viewer.hidden = true; return; } if(!currentPreviewUrl) return alert('No hay vista previa.'); try{ const t = await (await fetch(currentPreviewUrl)).text(); code.textContent = t; code.hidden = false; viewer.hidden = true; }catch(e){ alert(e.message); } }
function showView(){ code.hidden = true; viewer.hidden = false; }
async function openCurrentFolder(){ if(currentOutputFile && window.arkeaDesktop?.revealPath) return window.arkeaDesktop.revealPath(currentOutputFile); if(currentOutputFolder) return openPath(currentOutputFolder); if(currentConversationFolder) return openPath(currentConversationFolder); if(settingsCache.workspace) return openPath(settingsCache.workspace); alert('Selecciona primero una carpeta o crea un archivo.'); }

async function showOnboardingIfNeeded(){
  if(settingsCache.first_setup_done === '1') return;
  $('#onboardUserName').value = settingsCache.user_name || 'Manu';
  $('#onboardingModal').hidden = false;
}
async function finishOnboarding(){
  const name = ($('#onboardUserName').value || 'Manu').trim() || 'Manu';
  const installPack = $('#onboardInstallPack')?.checked;
  await saveBulk({user_name:name, first_setup_done:'1'});
  $('#onboardingModal').hidden = true;
  if(installPack) installRequiredPack();
  addMsg('assistant', `Perfecto, te llamaré ${name}. Puedes cambiarlo en Ajustes → Personaje.`);
  await speak(`Perfecto, te llamaré ${name}.`);
}

async function handleAction(e){
  const b = e.target.closest('[data-action]'); if(!b) return;
  const a = b.dataset.action;
  if(b.dataset.busy === '1') return;
  const longActions = new Set(['pull-model','pull-by-id','pull-defaults','install-required-pack','warm-selected-model','save-model-prefs','delete-selected-model','test-api','install-whisper','create-skill','upload-skill','save-api','load-eleven-voices']);
  const shouldBusy = longActions.has(a);
  if(shouldBusy && setButtonBusy(b, true, 'Trabajando...') === false) return;
  try{
    if(a === 'new-chat') await createNewChat();
    if(a === 'choose-folder') await chooseWorkspaceAndNewChat();
    if(a === 'open-folder') await openPath(b.dataset.path || '');
    if(a === 'open-chat') await openConversation(Number(b.dataset.id));
    if(a === 'preview') loadPreview(b.dataset.url, b.dataset.label || 'Vista previa');
    if(a === 'save-api') await saveApiConnection();
    if(a === 'apply-api-preset') await applyApiPreset(b.dataset.preset);
    if(a === 'delete-api') await deleteApi(Number(b.dataset.id));
    if(a === 'test-api') await testApiConnection(Number(b.dataset.id));
    if(a === 'save-eleven') await saveElevenQuick();
    if(a === 'load-eleven-voices') await loadElevenVoicesFromApi();
    if(a === 'select-eleven') await selectElevenVoice(b.dataset.id, b.dataset.name);
    if(a === 'install-whisper') await installWhisper();
    if(a === 'install-ollama') await installOllama();
    if(a === 'refresh-ollama') await refreshOllama();
    if(a === 'save-model-prefs') await saveModelPrefs();
    if(a === 'delete-selected-model') await deleteSelectedModel();
    if(a === 'warm-selected-model') await warmSelectedModel();
    if(a === 'install-required-pack') await installRequiredPack();
    if(a === 'install-required-pack') await installRequiredPack();
    if(a === 'search-ollama-models') await searchOllamaModels();
    if(a === 'choose-screen-source') await chooseScreenSource(b.dataset.id, b.dataset.name);
    if(a === 'choose-bg-image') await chooseBackgroundImage();
    if(a === 'bg-valley') await setBackgroundPreset('valley');
    if(a === 'bg-sky') await setBackgroundPreset('sky');
    if(a === 'clear-bg-image') await clearBackgroundImage();
    if(a === 'pull-defaults') await pullDefaults();
    if(a === 'pull-by-id') await pullModelById();
    if(a === 'pull-model') await pullModel(b.dataset.model);
    if(a === 'avatar-image') await chooseAvatarImage();
    if(a === 'avatar-clear') await clearAvatarImage();
    if(a === 'save-avatar') await saveAvatarSettings();
    if(a === 'create-skill') await createSkillFromSettings();
    if(a === 'upload-skill') await uploadSkillMd();
    if(a === 'toggle-control') await setControl(b.dataset.enabled === 'true');
    if(a === 'toggle-browser') await setBrowserAgent(b.dataset.enabled === 'true');
    if(a === 'add-mcp') await addMcp();
    if(a === 'choose-obsidian') await chooseObsidianVault();
    if(a === 'obsidian-note') await createObsidianTestNote();
    if(a === 'save-appearance') await saveAppearance();
    if(a === 'run-diagnostics') await runDiagnostics();
  }catch(err){
    addMsg('assistant','❌ Error en acción ' + a + ': ' + (err.message || err));
  }finally{
    if(shouldBusy) setButtonBusy(b, false);
  }

}

document.addEventListener('click', handleAction);
$('#newChat').onclick = () => createNewChat();
$('#uploadBtn').onclick = () => $('#fileUpload')?.click();
$('#fileUpload')?.addEventListener('change', e => { uploadSelectedFiles(e.target.files); e.target.value=''; });
$('#clear').onclick = () => { messages.innerHTML = ''; };
$('#visualMode').onclick = () => { visualMode = !visualMode; $('#visualMode').classList.toggle('active', visualMode); };
$('#talkBtn').onclick = startVoiceRecording;
$('#stopVoice').onclick = () => { try{ speechSynthesis.cancel(); if(currentAudio){ currentAudio.pause(); currentAudio.currentTime=0; currentAudio=null; } if(recording) stopVoiceRecording(false); setAvatarState('idle'); }catch{} };
$('#micHelpBtn').onclick = showMicGuide;
$('#cameraBtn').onclick = async (e) => { await toggleCameraLive(e.currentTarget); };
$('#screenBtn').onclick = async (e) => { const b=e.currentTarget; if(!setButtonBusy(b,true,'Pantalla...')) return; try{ await captureFrame('screen'); } finally{ setButtonBusy(b,false); } };
$('#closeScreenPicker').onclick = () => { $('#screenPickerModal').hidden = true; };
$('#refreshScreens').onclick = loadScreenSources;
$('#stopScreenLive').onclick = stopScreenLive;
$('#finishOnboarding').onclick = finishOnboarding;
$('#openSettings').onclick = () => openSettingsTab('workspace');
$('#openSettingsTop').onclick = () => openSettingsTab('workspace');
$('#stopAllTop').onclick = stopAllLive;
$('#closeSettings').onclick = closeSettings;
$('#previewLabel').onclick = chooseWorkspaceAndNewChat;
$('#tabView').onclick = showView;
$('#tabCode').onclick = showCode;
$('#download').onclick = downloadCurrentAsset;
$$('.settings-tabs button').forEach(b => b.onclick = () => openSettingsTab(b.dataset.tab));
bindChatSend();


function bindChatSend(){
  const sendBtn = $('#send');
  const promptEl = $('#prompt');
  if(sendBtn && !sendBtn.dataset.bound){
    sendBtn.dataset.bound = '1';
    sendBtn.addEventListener('click', e => { e.preventDefault(); send(); });
    sendBtn.addEventListener('pointerdown', e => { e.preventDefault(); send(); });
  }
  if(promptEl && !promptEl.dataset.bound){
    promptEl.dataset.bound = '1';
    promptEl.addEventListener('keydown', e => {
      if(e.key === 'Enter' && !e.shiftKey){
        e.preventDefault();
        send();
      }
    });
  }
}

Object.assign(window, {send, uploadSelectedFiles, createNewChat, openConversation, openPath, chooseWorkspaceAndNewChat, openSettingsTab, closeSettings, loadPreview, saveApiConnection, applyApiPreset, deleteApi, testApiConnection, saveElevenQuick, loadElevenVoicesFromApi, selectElevenVoice, installWhisper, installOllama, refreshOllama, installRequiredPack, saveModelPrefs, deleteSelectedModel, warmSelectedModel, stopAllLive, installRequiredPack, searchOllamaModels, pullDefaults, pullModel, pullModelById, chooseAvatarImage, clearAvatarImage, saveAvatarSettings, createSkillFromSettings, uploadSkillMd, setControl, setBrowserAgent, addMcp, chooseObsidianVault, createObsidianTestNote, saveAppearance, chooseBackgroundImage, clearBackgroundImage, setBackgroundPreset, renderDiagnostics, runDiagnostics, openScreenPicker, loadScreenSources, chooseScreenSource, stopScreenLive, finishOnboarding});


async function autoBootstrapRuntime(){
  if(autoBootstrapStarted) return;
  autoBootstrapStarted = true;
  // No bloquea el chat. Corre en segundo plano y prepara Ollama/modelos/Whisper.
  setTimeout(async ()=>{
    try{
      const st = await j('/api/arkea/ollama/quick-status');
      const models = st.models || [];
      const hasAnyModel = models.length > 0;
      const autoDone = settingsCache.auto_required_pack_done === '1';
      if(!st.installed && window.arkeaDesktop?.installBundledOllama){
        addMsg('assistant','⚙️ Preparando Ollama incluido en el instalador...');
        await window.arkeaDesktop.installBundledOllama();
      }
      if(!autoDone || !hasAnyModel){
        await installRequiredPack();
        await saveSetting('auto_required_pack_done','1');
      }
    }catch(e){
      // No interrumpir el chat.
      console.warn('autoBootstrapRuntime', e);
    }
  }, 3500);
}

async function warmOllamaFast(){
  try{
    const st = await j('/api/arkea/ollama/quick-status');
    if(st.running) $('#statusBadge').textContent = 'Backend activo · Ollama listo';
    else if(st.installed) $('#statusBadge').textContent = 'Backend activo · Ollama iniciando';
  }catch{}
}

async function boot(){
  bindChatSend();
  await loadSettings();
  try{ await j('/api/health'); $('#statusBadge').textContent = 'Backend activo'; }
  catch{ $('#statusBadge').textContent = 'Backend no responde'; }
  await refreshSideChats();
  if(!viewer.srcdoc && !viewer.src){ setPreviewHtml('<!doctype html><html><body style="font-family:Arial;padding:24px;background:#07111f;color:#e5f1ff"><h1>ARKEA AI</h1><p>Escribe o habla para empezar.</p></body></html>'); setPreviewLabel('Respuesta visual'); }
  warmOllamaFast();
  await showOnboardingIfNeeded();
}
boot();

try{$('#uploadBtn').onclick=()=>$('#fileUpload').click();$('#fileUpload').onchange=e=>uploadSelectedFiles(Array.from(e.target.files||[]));}catch{}

try{$('#openFolder').onclick=openCurrentOutputFolder;}catch{}
try{$('#download').onclick=downloadCurrentAsset;}catch{}
try{$('#zoomIn').onclick=()=>updateViewerZoom(0.2);$('#zoomOut').onclick=()=>updateViewerZoom(-0.2);$('#zoomReset').onclick=()=>{viewerZoom=1;updateViewerZoom(0);}; updateViewerZoomLabel();}catch{}
try{$('#stopVoiceTop').onclick=()=>{ try{ detenerVoz(); if(recording) stopVoiceRecording(false); }catch{} };}catch{}
try{$('#talkBtnInline').onclick=()=>startVoiceRecording(); $('#sendInline').onclick=()=>send(); $('#miniPrompt').addEventListener('keydown',e=>{if(e.key==='Enter'){ $('#prompt').value=$('#miniPrompt').value; send(); }});}catch{}
try{document.addEventListener('click',e=>{const a=e.target.closest('[data-action]'); if(!a)return; if(a.dataset.action==='bg-valley')setBackgroundPreset('valley'); if(a.dataset.action==='bg-sky')setBackgroundPreset('sky'); if(a.dataset.action==='open-image-api')openSettingsTab('apis');}); $('#quickTheme').onchange=e=>setBackgroundPreset(e.target.value==='sky'?'sky':'valley');}catch{}

try{$('#stopScreenTop').onclick=()=>stopScreenLive();$('#stopCameraTop').onclick=()=>stopCameraLive();}catch{}


// ===== FINAL UI WIRING: tabs, quick menu, footer search/weather/language =====
function setPanelTab(name){
  try{
    ['tabChat','tabVoice','tabSkills'].forEach(id=>$('#'+id)?.classList.remove('active'));
    if(name==='chat') $('#tabChat')?.classList.add('active');
    if(name==='voice') $('#tabVoice')?.classList.add('active');
    if(name==='skills') $('#tabSkills')?.classList.add('active');
  }catch{}
}
try{
  $('#tabChat').onclick=()=>{setPanelTab('chat'); $('#prompt')?.focus();};
  $('#tabVoice').onclick=()=>{setPanelTab('voice'); startVoiceRecording();};
  $('#tabSkills').onclick=()=>{setPanelTab('skills'); openSettingsTab('skills');};
  $('#quickMenuBtn').onclick=(e)=>{e.stopPropagation(); const m=$('#quickMenu'); if(m) m.hidden=!m.hidden;};
  document.addEventListener('click',e=>{ if(!e.target.closest('#quickMenu') && !e.target.closest('#quickMenuBtn')){ const m=$('#quickMenu'); if(m)m.hidden=true; }});
  $('#quickMenu')?.addEventListener('click',async e=>{
    const b=e.target.closest('[data-quick]'); if(!b)return;
    const q=b.dataset.quick;
    if(q==='clear') messages.innerHTML='';
    if(q==='new-chat') await createNewChat();
    if(q==='apis') openSettingsTab('apis');
    if(q==='skills') openSettingsTab('skills');
    if(q==='models') await refreshOllama();
    $('#quickMenu').hidden=true;
  });
  $('#miniSend').onclick=()=>{ const v=($('#miniPrompt')?.value||'').trim(); if(v){ $('#prompt').value=v; send(); }};
  $('#taskbarSearch').onclick=()=>{ if(window.arkeaDesktop?.openExternal) window.arkeaDesktop.openExternal('https://ollama.com/search'); else window.open('https://ollama.com/search','_blank'); };
  $('#languageToggle').onclick=async()=>{
    const order=['es','en','fr','it','pt','zh'];
    const cur=(settingsCache.ui_language||'es').slice(0,2); const next=order[(Math.max(0,order.indexOf(cur))+1)%order.length];
    await saveBulk({ui_language:next,input_language:ARKEA_LANGS[next].lang});
    settingsCache.ui_language=next; settingsCache.input_language=ARKEA_LANGS[next].lang;
    applyLanguage(); loadVoicesRetry();
  };
}catch(e){console.warn('ui wiring',e)}
function applyLanguage(){
  const lang=(settingsCache.ui_language||'es').slice(0,2);
  const profile=ARKEA_LANGS[lang] || ARKEA_LANGS.es;
  const ui=profile.ui;
  const map={talkBtn:ui.talk,cameraBtn:ui.camera,screenBtn:ui.screen,send:ui.send,uploadBtn:ui.upload,visualMode:ui.visual,clear:ui.clear,newChat:ui.newChat};
  for(const [id,txt] of Object.entries(map)){ const el=$('#'+id); if(el) el.textContent=txt; }
  if($('#prompt')) $('#prompt').placeholder=ui.placeholder;
  if($('#miniPrompt')) $('#miniPrompt').placeholder=ui.mini;
  if($('#languageToggle')) $('#languageToggle').textContent=lang.toUpperCase()+' · ARKEA AI';
  setLiveStatus(ui.live,false);
  loadVoicesRetry();
}
async function updateWeather(){
  try{
    const r=await fetch('https://wttr.in/?format=%t%20%C&lang=es',{cache:'no-store',headers:{'Accept':'text/plain'}});
    let t=(await r.text()).trim();
    if(!t || /<html|<!doctype|<style/i.test(t)) t='23°C Soleado';
    t=t.replace(/\+/g,' ').replace(/\s+/g,' ').slice(0,32);
    if($('#weatherText')) $('#weatherText').textContent=t || 'Clima activo';
  }catch{ if($('#weatherText')) $('#weatherText').textContent='23°C Soleado'; }
}
setTimeout(()=>{applyLanguage(); updateWeather();},800);
setInterval(updateWeather, 15*60*1000);


// ===== FINAL PATCH: controles de ventana y clima clicable =====
try{
  $('#winMin')?.addEventListener('click',()=>window.arkeaDesktop?.windowAction?.('minimize'));
  $('#winMax')?.addEventListener('click',()=>window.arkeaDesktop?.windowAction?.('maximize'));
  $('#winClose')?.addEventListener('click',()=>window.arkeaDesktop?.windowAction?.('close'));
  $('#weatherText')?.addEventListener('click',()=>updateWeather());
}catch{}


try{$('#testVoiceBtn').onclick=()=>hablar();$('#pauseVoiceBtn').onclick=()=>pausarVoz();$('#resumeVoiceBtn').onclick=()=>reanudarVoz();$('#stopBrowserVoiceBtn').onclick=()=>detenerVoz();}catch{}

try{$('#canvasToggle').onclick=()=>openCanvasEditor();}catch{}
