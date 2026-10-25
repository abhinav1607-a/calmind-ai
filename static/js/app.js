const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
let selectedMood = null;
const escapeHtml = (s='') => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(url, options={}) {
  const response = await fetch(url, {credentials:'same-origin', headers:{'Content-Type':'application/json', ...(options.headers||{})}, ...options});
  const type = response.headers.get('content-type') || '';
  const data = type.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) throw new Error(data.error || 'Something went wrong. Please try again.');
  return data;
}
function feedback(id, message, bad=false) { const el=$(id); if(el){el.textContent=message;el.classList.toggle('error-text',bad);} }
function renderMoods(rows) {
 const el=$('#mood-history'); if(!el)return;
 el.innerHTML=rows.length?rows.slice(0,6).map(r=>'<div class="history-row"><span>'+escapeHtml(r.mood)+'</span><small>'+escapeHtml((r.created_at||'').replace('T',' ').slice(0,16))+'</small></div>').join(''):'No check-ins yet. Your next moment can start here.';
}
function renderJournals(rows) {
 const el=$('#journal-history'); if(!el)return;
 el.innerHTML=rows.length?rows.slice(0,4).map(r=>'<div class="history-entry"><b>'+escapeHtml(r.title||'Reflection')+'</b><p>'+escapeHtml((r.body||'').slice(0,160))+'</p><small>'+escapeHtml((r.created_at||'').replace('T',' ').slice(0,16))+' · '+escapeHtml(r.sentiment||'Reflection')+'</small></div>').join(''):'Your saved reflections will appear here.';
}
async function refresh() {
 try {
  const [summary,moodRows,journalRows]=await Promise.all([api('/api/summary'),api('/api/moods'),api('/api/journals')]);
  $('#mood-count').textContent=summary.mood_count; $('#journal-count').textContent=summary.journal_count; $('#average-mood').textContent=summary.average_mood||'—';
  renderMoods(moodRows); renderJournals(journalRows);
 } catch(e) { console.warn(e); }
}
$$('.mood-option').forEach(btn=>btn.addEventListener('click',()=>{$$('.mood-option').forEach(b=>b.classList.remove('selected'));btn.classList.add('selected');selectedMood=btn.dataset.mood;$('#save-mood').disabled=false;feedback('#mood-feedback','');}));
$('#save-mood')?.addEventListener('click',async()=>{if(!selectedMood)return;const btn=$('#save-mood');btn.disabled=true;try{await api('/api/moods',{method:'POST',body:JSON.stringify({mood:selectedMood,note:$('#mood-note').value})});$('#mood-note').value='';selectedMood=null;$$('.mood-option').forEach(b=>b.classList.remove('selected'));feedback('#mood-feedback','Check-in saved. Thank you for noticing how you feel.');await refresh();}catch(e){feedback('#mood-feedback',e.message,true);}finally{btn.disabled=!selectedMood;}});
$('#save-journal')?.addEventListener('click',async()=>{const btn=$('#save-journal');btn.disabled=true;try{const r=await api('/api/journals',{method:'POST',body:JSON.stringify({title:$('#journal-title').value,body:$('#journal-body').value})});$('#journal-title').value='';$('#journal-body').value='';feedback('#journal-feedback','Reflection saved. Text sentiment estimate: '+r.sentiment+'.');await refresh();}catch(e){feedback('#journal-feedback',e.message,true);}finally{btn.disabled=false;}});
function addBubble(text,who){const el=document.createElement('div');el.className='chat-bubble '+who;el.textContent=text;$('#chat-messages').appendChild(el);$('#chat-messages').scrollTop=$('#chat-messages').scrollHeight;}
$('#chat-form')?.addEventListener('submit',async ev=>{ev.preventDefault();const input=$('#chat-input'),message=input.value.trim();if(!message)return;input.value='';addBubble(message,'user');const btn=$('#chat-form button');btn.disabled=true;feedback('#chat-feedback','Calmind is thinking…');try{const r=await api('/api/chat',{method:'POST',body:JSON.stringify({message})});addBubble(r.reply,'assistant');feedback('#chat-feedback','');}catch(e){feedback('#chat-feedback',e.message,true);}finally{btn.disabled=false;input.focus();}});
if ($('#mood-count')) refresh();