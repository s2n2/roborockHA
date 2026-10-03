/* Dobby Scheduler 0.1.2. No external dependencies or remote assets. */

// Integration extra modules can execute before HA's app bundle installs the
// scoped-custom-element-registry polyfill. Registering (or even constructing
// the class against HTMLElement) before that point strands it in the native
// registry: window.customCards is visible, but customElements.get() is not.
// HA imports its scoped-registry polyfill before defining home-assistant.
// Keep this a non-blocking bootstrap; do not delay other extra modules.
// Primary references:
// https://github.com/home-assistant/frontend/issues/52960
// https://github.com/home-assistant/frontend/blob/dev/src/entrypoints/app.ts
async function registerDobbySchedulerCard() {
  window.dobbySchedulerCardStatus = {version:'0.1.2', stage:'waiting-for-home-assistant'};
  await window.customElements.whenDefined('home-assistant');
  // The global registry may have changed while the native promise was pending.
  // Always resolve against the CURRENT registry, never a cached reference.
  if (!window.customElements.get('home-assistant')) {
    await window.customElements.whenDefined('home-assistant');
  }
  window.dobbySchedulerCardStatus = {version:'0.1.2', stage:'registering'};
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const modes = {vacuum:'Vacuum', vac_and_mop:'Vacuum + mop', mop:'Mop'};
const modeIcon = m => m === 'vacuum' ? 'mdi:vacuum' : m === 'mop' ? 'mdi:water' : 'mdi:water-plus';
const icon = (name) => `<ha-icon icon="${esc(name)}"></ha-icon>`;
const entityFields = [
 ['vacuum_entity','Vacuum','vacuum'], ['presence_entity','Someone is home (on = home)','binary_sensor,input_boolean'],
 ['mode_entity','Cleaning-mode selector','select'], ['battery_entity','Battery sensor','sensor'],
 ['error_entity','Vacuum-error sensor','sensor'], ['map_entity','Selected-map selector','select'],
 ['empty_entity','Dust-emptying switch','switch'], ['wash_entity','Mop-washing switch','switch'],
 ['mop_intensity_entity','Mop-intensity selector (optional)','select'],
 ['completion_entity','Advanced: completed-record sensor (normally blank)','sensor']
];
const numericFields = [
 ['away_minutes','Away delay (minutes)',0,120], ['minimum_battery','Minimum battery (%)',10,100],
 ['gesture_seconds','Double-toggle window (seconds)',0.5,5], ['gesture_cooldown','Gesture cooldown (seconds)',2,30],
 ['start_timeout','Start/mode confirmation timeout (seconds)',60,900], ['room_timeout','Room timeout (seconds)',600,21600],
 ['proof_timeout','Completion-record wait (seconds)',60,900], ['empty_timeout','Emptying timeout (seconds)',60,900],
 ['dock_timeout','Connection/recovery timeout (seconds)',60,1800], ['dock_settle','Dock settling time (seconds)',5,120]
];
const styles = `
:host{display:block;font-family:var(--primary-font-family,Arial,sans-serif);color:var(--primary-text-color,#193239)}
*{box-sizing:border-box}ha-card{display:block;border-radius:22px;overflow:hidden;background:var(--ha-card-background,var(--card-background-color,#fff));border:1px solid var(--divider-color,#dce6e6);box-shadow:none}
.head{padding:22px 22px 14px;display:flex;align-items:center;gap:12px}.robot{width:46px;height:46px;border-radius:15px;display:grid;place-items:center;background:#137f7b18;color:#117975}.robot ha-icon{--mdc-icon-size:28px}.titles{flex:1}.eyebrow{font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:var(--secondary-text-color,#648087);font-weight:700}h2{font-size:23px;margin:3px 0 0;letter-spacing:-.03em}h3{font-size:17px;margin:0 0 12px}p{line-height:1.5}button,input,select,textarea{font:inherit}button{cursor:pointer;border:1px solid var(--divider-color,#dbe5e5);border-radius:11px;background:var(--card-background-color,#fff);color:inherit;padding:10px 13px;min-height:40px}button:hover{background:#137f7b12}button:disabled{opacity:.45;cursor:default}button.primary{background:#167e78;color:white;border-color:#167e78;font-weight:700}button.icon{padding:7px;min-width:38px;min-height:38px;border-color:transparent;background:transparent}.danger{color:#ab4b30}.body{padding:0 22px 20px}.summary{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;padding:13px;background:var(--secondary-background-color,#f2f7f7);border-radius:15px;margin-bottom:12px}.summary strong{display:block;font-size:17px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.small{font-size:12px;line-height:1.5;color:var(--secondary-text-color,#64787c)}.status{display:flex;align-items:flex-start;gap:8px;font-size:13px;line-height:1.5;padding:0 2px 14px}.dot{width:8px;height:8px;border-radius:50%;background:#167e78;flex:none;margin-top:5px}.controls{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:18px}.controls button{flex:1;white-space:nowrap;font-size:12px}.section{display:flex;align-items:center;justify-content:space-between;margin:17px 0 9px}.section h3{font-size:14px;margin:0}.chipgrid{display:flex;gap:7px;flex-wrap:wrap}.roomchip{border-radius:12px;text-align:left;font-size:12px;padding:8px 10px;min-height:54px;min-width:92px}.roomchip small{display:block;font-size:10px;opacity:.75;margin-top:3px}.roomchip.selected{border-color:#16867e;background:#16867e15}.roomchip.done{opacity:.65}.job{display:flex;align-items:center;gap:9px;padding:12px 0;border-bottom:1px solid var(--divider-color,#e3ecec)}.job:last-child{border-bottom:0}.job.active{background:#16867e09;margin:0 -10px;padding:12px 10px;border-radius:10px}.job .num{font-size:12px;color:var(--secondary-text-color,#718284);width:20px;text-align:center}.job .text{flex:1;min-width:0}.job .text strong{font-size:13px}.job .small{font-size:10px}.job .actions{display:flex;gap:0}.job .actions button{min-height:32px;min-width:30px;padding:3px}.job .actions ha-icon{--mdc-icon-size:17px}.job.done strong{text-decoration:line-through;opacity:.65}.job.done .num{color:#16867e}.empty{padding:18px;border:1px dashed var(--divider-color,#c7dada);border-radius:13px;line-height:1.6;font-size:13px}.toggle{display:flex;align-items:center;gap:8px;font-size:12px}.toggle input{width:18px;height:18px;accent-color:#16867e}.warn{border-left:3px solid #cb8532;background:#cb853214;padding:11px 13px;margin:10px 0;border-radius:7px;font-size:12px;line-height:1.55}.error{border-left-color:#bd5945;background:#bd594511}.foot{margin-top:15px;display:flex;justify-content:space-between;align-items:center;gap:10px}.foot .small{font-size:10px}.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#183735;color:white;max-width:min(90vw,600px);padding:13px 20px;border-radius:12px;box-shadow:0 8px 35px #0003;z-index:10000;font-size:13px;line-height:1.5}
dialog{padding:0;border:1px solid var(--divider-color,#d7e4e4);border-radius:20px;background:var(--card-background-color,#fff);color:var(--primary-text-color,#193239);width:min(900px,calc(100vw - 28px));max-height:90vh;box-shadow:0 24px 90px #0005}dialog::backdrop{background:#14252a88}.dialoghead{padding:20px 24px 14px;display:flex;align-items:center;justify-content:space-between;gap:12px;position:sticky;top:0;background:var(--card-background-color,#fff);z-index:2}.dialoghead h2{font-size:21px}.tabs{display:flex;gap:5px;padding:0 20px 12px;border-bottom:1px solid var(--divider-color,#e2e9e9);overflow:auto;position:sticky;top:78px;background:var(--card-background-color,#fff);z-index:2}.tabs button{font-size:12px;white-space:nowrap;border-color:transparent}.tabs button.active{background:#16867e18;color:#117975;font-weight:700}.pane{padding:22px 24px}.formgrid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.field{display:flex;flex-direction:column;gap:5px;font-size:12px}.field label{font-weight:600}.field input,.field select,.field textarea{width:100%;padding:9px 10px;border:1px solid var(--divider-color,#ccdddd);border-radius:8px;min-height:39px;color:inherit;background:var(--card-background-color,#fff)}select[multiple]{min-height:160px}.span2{grid-column:1/-1}.inline{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.inline input[type=checkbox]{width:18px;height:18px;accent-color:#16867e}.savebar{display:flex;justify-content:flex-end;gap:8px;margin-top:20px}.savebar button{font-size:12px}.roomlayout{display:grid;grid-template-columns:200px 1fr;gap:24px}.roomnav{display:flex;flex-direction:column;gap:6px;max-height:540px;overflow:auto}.roomnav button{text-align:left;font-size:12px}.roomnav button.active{border-color:#16867e;background:#16867e12}.roomnav small{display:block;font-size:10px;opacity:.7;margin-top:3px}.badge{font-size:10px;border-radius:6px;background:#16867e18;padding:3px 6px;display:inline-block}code{font:12px ui-monospace,monospace;background:var(--secondary-background-color,#edf3f3);padding:2px 5px;border-radius:4px;overflow-wrap:anywhere}pre{font:11px ui-monospace,monospace;white-space:pre-wrap;word-break:break-word;padding:13px;border-radius:8px;background:var(--secondary-background-color,#f1f6f6);max-height:340px;overflow:auto}.instructions{font-size:13px;line-height:1.65}.instructions h3{margin-top:22px}.instructions table,.maptable{width:100%;border-collapse:collapse;font-size:12px}.instructions td,.instructions th,.maptable td,.maptable th{text-align:left;padding:9px 7px;border-bottom:1px solid var(--divider-color,#e1eaea)}.logrow{padding:8px 0;border-bottom:1px solid var(--divider-color,#e1eaea);font-size:12px;line-height:1.5}.logrow time{font-size:10px;display:block;opacity:.6}a{color:#137e78}.muted{opacity:.65}
@media(max-width:600px){.head{padding:17px 16px 12px}.body{padding:0 16px 17px}.controls{gap:6px}.controls button{padding:9px 8px}.summary strong{font-size:14px}.job .actions button{min-width:28px}.roomlayout{grid-template-columns:1fr;gap:14px}.roomnav{flex-direction:row;max-height:none;padding-bottom:7px}.roomnav button{min-width:115px}.formgrid{grid-template-columns:1fr}.span2{grid-column:auto}.pane{padding:16px}.tabs{padding-left:12px}.dialoghead{padding:16px}.job .small{max-width:180px}.foot{align-items:flex-start}.roomchip{flex:1;min-width:90px}dialog{max-height:94vh;width:calc(100vw - 14px)}h2{font-size:21px}}
`;

class DobbySchedulerCard extends HTMLElement {
  static get version(){return '0.1.2';}
  constructor() {
    super(); this.attachShadow({mode:'open'}); this.tab='rooms'; this.data=null; this.configData=null;
    this.loading=false; this.draft=null; this.roomDraft=null; this.selectedArea=null;
    this.shadowRoot.innerHTML=`<style>${styles}</style><div id="main"></div><dialog id="setup"></dialog><div id="toast" hidden></div>`;
    this.shadowRoot.addEventListener('click', e => this.click(e));
    this.shadowRoot.addEventListener('change', e => this.change(e));
  }
  setConfig(config) { this.config={title:'Dobby',...config}; this.render(); }
  getCardSize(){return 9;}
  getGridOptions(){return {columns:12,rows:10,min_columns:6,min_rows:6};}
  static getStubConfig(){return {type:'custom:dobby-scheduler-card',title:'Dobby'};}
  set hass(hass){this._hass=hass;if(!this.data&&!this.loading)this.refresh();}
  connectedCallback(){this.timer=setInterval(()=>this.refresh(),5000);if(this._hass)this.refresh();}
  disconnectedCallback(){clearInterval(this.timer);clearTimeout(this.toastTimer);}
  async refresh(config=false) {
    if(!this._hass||this.loading)return;
    this.loading=true;
    try{
      const result=await this._hass.callWS({type:'dobby_scheduler/get',include_config:config,...(this.config?.entry_id?{entry_id:this.config.entry_id}:{})});
      this.data=result;this.error='';if(result.settings){this.configData=result;this.draft=structuredClone(result.settings);}
      this.render();
    }catch(e){this.error=e.message||String(e);this.render();}
    finally{this.loading=false;}
  }
  async command(action,data={}){
    try {
      const result=await this._hass.callWS({type:'dobby_scheduler/command',entry_id:this.data?.entry_id,action,data});
      // Bypass a concurrent status refresh only by allowing it to finish, never fake success.
      while(this.loading)await new Promise(r=>setTimeout(r,30));
      await this.refresh(false);return result;
    }catch(e){this.toast(e.message||String(e));throw e;}
  }
  toast(message){this.shadowRoot.getElementById('toast')?.remove();const t=document.createElement('div');t.id='toast';t.textContent=message;t.className='toast';t.setAttribute('role','status');const dialog=this.shadowRoot.getElementById('setup');(dialog?.open?dialog:this.shadowRoot).append(t);clearTimeout(this.toastTimer);this.toastTimer=setTimeout(()=>t.remove(),7000);}
  moreInfo(entity){if(!entity)return;this.shadowRoot.getElementById('setup').close();this.dispatchEvent(new CustomEvent('hass-more-info',{detail:{entityId:entity},bubbles:true,composed:true}));}
  render(){
    const target=this.shadowRoot.getElementById('main');if(!target)return;
    if(!this.data){target.innerHTML=`<ha-card><div class="head"><div class="robot">${icon('mdi:robot-vacuum')}</div><div class="titles"><div class="eyebrow">ROOM SCHEDULER</div><h2>${esc(this.config?.title||'Dobby')}</h2></div></div><div class="body"><div class="empty">${esc(this.error||'Connecting to the local scheduler...')}<p class="small">Install the bundled integration, restart Home Assistant, and add Dobby Scheduler under Devices &amp; services (or use its package bootstrap).</p><button data-action="refresh">Reconnect</button></div></div></ha-card>`;return;}
    const d=this.data, jobs=d.jobs||[], pending=jobs.filter(j=>j.status!=='completed'), done=jobs.length-pending.length;
    const current=d.active?.name, next=pending.find(j=>j.uid!==d.active?.uid)?.name;
    const available=d.rooms.filter(r=>r.cleanable).sort((a,b)=>a.priority-b.priority||a.name.localeCompare(b.name));
    target.innerHTML=`<ha-card><div class="head"><div class="robot">${icon('mdi:robot-vacuum')}</div><div class="titles"><div class="eyebrow">TODAY'S ROOM PLAN</div><h2>${esc(this.config?.title||d.name)}</h2></div><button class="icon" data-action="setup" aria-label="Setup and instructions" title="Setup & instructions">${icon('mdi:cog-outline')}</button></div><div class="body">
      <div class="summary"><div><span class="small">${current?'Cleaning / servicing':'Next room'}</span><strong>${esc(current||next||'No rooms queued')}</strong></div><div><span class="small">Completed</span><strong>${done} / ${jobs.length}</strong></div><div><span class="small">Battery</span><strong>${d.telemetry?.battery==null?'Unknown':Math.round(d.telemetry.battery)+'%'}</strong></div></div>
      <div class="status"><span class="dot" style="${d.enabled||d.manual?'':'background:#879d9e'}"></span><span>${esc(d.reason)}</span></div>
      ${d.fault?`<div class="warn error">${esc(d.fault)}<div style="margin-top:8px"><button data-action="retry">Retry after checking</button><button data-action="diagnostics">Details</button></div></div>`:''}
      ${d.telemetry?.legacy?.length?`<div class="warn">Old Dobby automations are still enabled. Open Setup to review them before running.</div>`:''}
      <div class="controls"><button class="primary" data-action="run" ${!pending.length||d.active?'disabled':''}>${icon('mdi:play')} Run now</button><button data-action="pause">${icon('mdi:home-import-outline')} Pause &amp; dock</button><button data-action="reset" ${d.active?'disabled':''}>Daily defaults</button></div>
      <div class="section"><h3>Choose today's rooms</h3><button class="icon" data-action="setup" aria-label="Configure rooms">${icon('mdi:tune')}</button></div>
      ${available.length?`<div class="chipgrid">${available.map(r=>{const j=jobs.find(j=>j.area_id===r.area_id);return `<button class="roomchip ${j?.status==='needs_action'?'selected':''} ${j?.status==='completed'?'done':''}" data-action="toggle-room" data-id="${esc(r.area_id)}" aria-pressed="${!!j&&j.status==='needs_action'}">${esc(r.name)}<small>${j?.status==='completed'?'Done - tap to repeat':modes[r.mode]||'Mode conflict'}</small></button>`}).join('')}</div>`:`<div class="empty">No rooms are labelled yet. <button data-action="setup">Open setup</button><p class="small">Select Areas, their cleaning modes and daily defaults. No per-room YAML is needed.</p></div>`}
      <div class="section"><h3>Execution order</h3><span class="small">${pending.length} pending</span></div>
      ${jobs.map((j,i)=>`<div class="job ${j.status==='completed'?'done':''} ${d.active?.uid===j.uid?'active':''}"><span class="num">${j.status==='completed'?'&#10003;':d.active?.uid===j.uid?'&#9654;':i+1}</span><div class="text"><strong>${esc(j.name)}</strong><div class="small">${esc(modes[j.mode]||'Check mode labels')}${j.source==='wall_toggle'?' &bull; wall request':''}${j.urgent?' &bull; priority':''}${d.active?.uid===j.uid?' &bull; '+esc(d.active.phase):''}</div></div><div class="actions"><button class="icon" data-action="promote" data-id="${j.uid}" title="Make next" aria-label="Make ${esc(j.name)} next" ${j.status==='completed'||d.active?.uid===j.uid?'disabled':''}>${icon('mdi:priority-high')}</button><button class="icon" data-action="up" data-id="${j.uid}" aria-label="Move ${esc(j.name)} up" ${i===0?'disabled':''}>${icon('mdi:chevron-up')}</button><button class="icon" data-action="down" data-id="${j.uid}" aria-label="Move ${esc(j.name)} down" ${i===jobs.length-1?'disabled':''}>${icon('mdi:chevron-down')}</button><button class="icon" data-action="job" data-id="${j.uid}" aria-label="${esc(j.name)} details">${icon('mdi:dots-horizontal')}</button></div></div>`).join('')||`<div class="small">Add rooms above or restore your daily defaults.</div>`}
      <div class="foot"><label class="toggle"><input type="checkbox" data-setting="auto" ${d.enabled?'checked':''}>Automatic when away</label><span class="small">Local queue &bull; ${esc(d.day||'Not initialised')}<br>Four switch changes / ${esc(this.draft?.gesture_seconds||2)} seconds = next room</span></div>
      ${this.error?`<div class="warn error">Connection warning: ${esc(this.error)}</div>`:''}
    </div></ha-card>`;
  }
  async openSetup(tab='rooms'){
    this.tab=tab;await this.refresh(true);this.renderDialog();const dialog=this.shadowRoot.getElementById('setup');if(!dialog.open)dialog.showModal();
  }
  renderDialog(){
    const d=this.data;if(!d)return;
    const dialog=this.shadowRoot.getElementById('setup');
    dialog.innerHTML=`<div class="dialoghead"><div><div class="eyebrow">DOBBY SCHEDULER &bull; SETUP</div><h2>Rooms, rules &amp; instructions</h2></div><button class="icon" data-action="close" aria-label="Close setup">${icon('mdi:close')}</button></div><div class="tabs">${[['rooms','Rooms & map'],['settings','Robot & schedule'],['switches','Switch gestures'],['help','Instructions'],['diagnostics','Diagnostics']].map(([id,label])=>`<button data-action="tab" data-id="${id}" class="${this.tab===id?'active':''}">${label}</button>`).join('')}</div><div class="pane">${this.pane()}</div>`;
  }
  pane(){
    if(this.tab==='help')return this.help();
    if(this.tab==='diagnostics')return this.diagnostics();
    if(!this.draft)return `<div class="empty">Room and connection configuration requires an administrator account. The room queue remains available to users with control permission.</div>`;
    if(this.tab==='settings')return this.settingsPane();
    if(this.tab==='switches')return this.switchPane();
    return this.roomsPane();
  }
  field(key,label,domain){
    const v=this.draft[key]||'';const candidates=(this.configData?.candidates||[]).filter(e=>domain.split(',').includes(e.entity_id.split('.')[0]));
    return `<div class="field"><label for="cfg-${key}">${esc(label)}</label><input id="cfg-${key}" data-cfg="${key}" list="list-${key}" value="${esc(v)}" placeholder="Select or type entity ID"><datalist id="list-${key}">${candidates.map(e=>`<option value="${esc(e.entity_id)}">${esc(e.name)} (${esc(e.state)})</option>`).join('')}</datalist></div>`;
  }
  settingsPane(){
    const c=this.draft;
    return `<div class="warn">Save the robot settings first, then fetch maps under Rooms &amp; map. Detect controls suggests existing Dobby entities but does not enable cleaning.</div><div class="formgrid">${entityFields.slice(0,2).map(f=>this.field(...f)).join('')}<div class="span2"><button data-action="detect">Find controls for this vacuum</button> <button data-action="vacuum-info">Open vacuum controls</button></div>${entityFields.slice(2,9).map(f=>this.field(...f)).join('')}<div class="field"><label>Mop intensity for wet rooms</label><input data-cfg="mop_intensity" value="${esc(c.mop_intensity)}"><span class="small">Use an exact supported option, e.g. medium. Not changed for vacuum-only rooms.</span></div><div class="field span2"><label>Water problem entities (comma-separated)</label><textarea data-cfg="water_problem_entities">${esc(c.water_problem_entities.join(', '))}</textarea><span class="small">on = problem. Only blocks mop / vacuum + mop rooms.</span></div><div class="field span2"><label>Extra pause entities (comma-separated)</label><textarea data-cfg="blocking_entities">${esc(c.blocking_entities.join(', '))}</textarea><span class="small">on or unavailable blocks cleaning, e.g. a babysitter or manual pause helper. Never add the alarm here to try to disable it.</span></div><div class="field"><label>Nightly reset</label><input type="time" data-cfg="reset_time" value="${esc(c.reset_time)}"></div><div class="field"><label>Cleaning starts after</label><input type="time" data-cfg="window_start" value="${esc(c.window_start)}"></div><div class="field"><label>Cleaning stops at</label><input type="time" data-cfg="window_end" value="${esc(c.window_end)}"></div>${numericFields.slice(0,4).map(([k,l,a,b])=>`<div class="field"><label>${esc(l)}</label><input type="number" step="${k.includes('gesture')?'.1':'1'}" min="${a}" max="${b}" data-cfg="${k}" value="${esc(c[k])}"></div>`).join('')}<div class="span2 inline">${[['acknowledge','Locate voice acknowledgement'],['reject_automation_context','Ignore known automation-generated switch changes'],['empty_after_room','Empty after every room'],['empty_after_mop','Also empty after mop-only rooms']].map(([k,l])=>`<label><input type="checkbox" data-cfg="${k}" ${c[k]?'checked':''}> ${esc(l)}</label>`).join('')}</div></div><details style="margin-top:20px"><summary>Advanced timeouts and completion adapter</summary><div class="formgrid" style="margin-top:14px">${numericFields.slice(4).map(([k,l,a,b])=>`<div class="field"><label>${l}</label><input type="number" min="${a}" max="${b}" data-cfg="${k}" value="${esc(c[k])}"></div>`).join('')}${this.field(...entityFields[9])}<div class="small span2">Normally leave the completed-record entity blank. The included read-only adapter uses the official Roborock V1 completed-clean record. An optional custom sensor must expose begin/end epoch seconds, complete=1, error=0, area&gt;0 and optionally map_flag. A last-clean timestamp alone is not enough.</div></div></details><div class="savebar"><button class="primary" data-action="save-settings">Save settings</button></div>`;
  }
  roomsPane(){
    const d=this.data, labels=d.labels||{};
    if(Object.keys(labels).length<6)return `<div class="empty"><h3>Create the Dobby labels</h3><p>These will be ordinary Home Assistant labels, editable in Home Assistant as well as here.</p><button class="primary" data-action="create-labels">Create the six labels</button><p class="small">No rooms will be selected automatically and Dobby will not start.</p></div>`;
    const areas=[...d.rooms].sort((a,b)=>a.priority-b.priority||a.name.localeCompare(b.name));
    if(!areas.length)return `<div class="empty">Create your rooms as Home Assistant Areas first, then return here.</div>`;
    if(!this.selectedArea||!areas.some(a=>a.area_id===this.selectedArea))this.selectedArea=areas[0].area_id;
    if(!this.roomDraft||this.roomDraft.area_id!==this.selectedArea)this.roomDraft=structuredClone(areas.find(a=>a.area_id===this.selectedArea));
    const r=this.roomDraft, m=d.maps.find(m=>String(m.flag)===String(r.map_flag)), checked=(r.segments||[]).map(String);
    return `<div class="inline" style="margin-bottom:16px"><button data-action="maps">${icon('mdi:map-search-outline')} Fetch/check maps</button><button data-action="mop-order">Use mopping-first defaults</button><span class="small">${d.maps_at?'Map data fetched '+new Date(d.maps_at*1000).toLocaleString():'No map data fetched yet'}</span></div><div class="warn">Confirm numbers against the live Roborock map, not an old floor-plan card. Saving a row writes the Area's Dobby labels and stores only its mapping/order here. The selected robot map must match before a room can run.</div><div class="roomlayout"><nav class="roomnav">${areas.map(a=>`<button data-action="area" data-id="${esc(a.area_id)}" class="${a.area_id===r.area_id?'active':''}">${esc(a.name)}<small>${a.cleanable?(a.verified&&!a.mapping_error?'Mapped':'Needs mapping'):'Not in picker'} &bull; ${esc(modes[a.mode]||'Mode conflict')}</small></button>`).join('')}</nav><section><h3>${esc(r.name)}</h3><div class="inline" style="margin-bottom:14px"><button data-action="popup-queue" data-id="${esc(r.area_id)}" ${!d.rooms.find(a=>a.area_id===r.area_id)?.cleanable?'disabled':''}>${d.jobs.some(j=>j.area_id===r.area_id&&j.status!=='completed')?'Remove from today':'Add to today'}</button><button data-action="popup-next" data-id="${esc(r.area_id)}" ${!d.rooms.find(a=>a.area_id===r.area_id)?.cleanable?'disabled':''}>Make next</button></div><div class="formgrid"><div class="inline span2"><label><input type="checkbox" data-room="cleanable" ${r.cleanable?'checked':''}> Available to Dobby</label><label><input type="checkbox" data-room="daily" ${r.daily?'checked':''}> Daily default</label></div><div class="field"><label>Cleaning-mode label</label><select data-room="mode_label"><option value="" ${!r.mode_label?'selected':''}>No label (defaults to vacuum)</option><option value="dobby_vacuum" ${r.mode_label==='dobby_vacuum'?'selected':''}>Dobby vacuum</option><option value="dobby_vacuum_mop" ${r.mode_label==='dobby_vacuum_mop'?'selected':''}>Dobby vacuum and mop</option><option value="dobby_mop" ${r.mode_label==='dobby_mop'?'selected':''}>Dobby mop</option></select></div><div class="field"><label>Default priority (lower first)</label><input type="number" min="0" max="10000" data-room="priority" value="${esc(r.priority)}"></div><div class="field span2"><label>Roborock map</label><select data-room="map_flag"><option value="">Choose fetched map</option>${d.maps.map(m=>`<option value="${m.flag}" ${String(m.flag)===String(r.map_flag)?'selected':''}>${esc(m.name)} (map ${m.flag})</option>`).join('')}</select><span class="small">Currently selected on Dobby: ${esc(d.telemetry?.map_name||'Unknown')}</span></div><div class="field span2"><label>Room number(s)</label><select multiple data-room="segments">${m?Object.entries(m.rooms).sort((a,b)=>Number(a[0])-Number(b[0])).map(([n,name])=>`<option value="${n}" ${checked.includes(n)?'selected':''}>${n} - ${esc(name)}</option>`).join(''):''}</select><span class="small">Multiple segments in one Area share a mode. Use separate Areas for hallway carpet and hallway tiles if their cleaning modes differ.</span></div><label class="inline span2"><input type="checkbox" data-room="verified" ${r.verified?'checked':''}> I checked that these numbers really are ${esc(r.name)} on this map.</label></div>${r.mapping_error?`<div class="warn error">${esc(r.mapping_error)}</div>`:''}<div class="savebar"><button class="primary" data-action="save-room">Save this room</button></div></section></div>`;
  }
  switchPane(){
    const d=this.data;const candidates=(this.configData?.candidates||[]).filter(e=>['switch','light','binary_sensor','input_boolean'].includes(e.entity_id.split('.')[0]));
    return `<div class="instructions"><h3>Label the physical input, not both input and light</h3><p>A new wall switch only needs the right Home Assistant Area and <code>dobby_room_toggle</code>. A recognised gesture adds or promotes that Area to <strong>next</strong>; it does not abandon the current room or start cleaning in an occupied house.</p><p>Four actual on/off changes in ${esc(this.draft.gesture_seconds)} seconds means two complete cycles. Unknown/unavailable and attribute-only changes do not count.</p></div><div class="field"><label>Physical switch/input entity</label><input id="toggle-choice" list="toggle-list" placeholder="binary_sensor... or switch..."><datalist id="toggle-list">${candidates.map(e=>`<option value="${esc(e.entity_id)}">${esc(e.name)}</option>`).join('')}</datalist></div><div class="savebar"><button class="primary" data-action="add-toggle">Add gesture label</button></div><h3>Currently labelled</h3>${Object.entries(d.toggle_entities).map(([e,a])=>`<div class="job"><div class="text"><strong>${esc(e)}</strong><div class="small">${esc(d.rooms.find(r=>r.area_id===a)?.name||'No Area assigned')}</div></div><button data-action="entity-info" data-id="${esc(e)}" class="icon" aria-label="Open entity settings">${icon('mdi:cog-outline')}</button><button data-action="remove-toggle" data-id="${esc(e)}" class="icon" aria-label="Remove label">${icon('mdi:close')}</button></div>`).join('')||'<p class="small">No switch gestures have been enabled.</p>'}<div class="warn">Cloud-delayed wall switches may not report quickly enough for a two-second gesture. Prefer local physical input events. Home Assistant can filter known automation contexts, but cannot always distinguish a device's own firmware actions from physical use.</div>`;
  }
  help(){return `<div class="instructions"><h3>One-time setup</h3><p>1. Under <strong>Robot &amp; schedule</strong>, select the vacuum and home-presence sensor. Use Find controls, check each proposed entity and save.</p><p>2. Under <strong>Rooms &amp; map</strong>, create the labels, fetch maps, select each Area's mode, priority and exact segment numbers, and confirm the mapping.</p><p>3. Label wall-switch inputs under <strong>Switch gestures</strong>. Their entity Area takes precedence over their device Area.</p><p>4. Disable the old vacuum scheduler and any automatic map-reset routine. Restore Daily defaults and test one room under supervision before enabling Automatic when away.</p><h3>Labels</h3><table><tr><th>Label</th><th>Apply to</th><th>Meaning</th></tr>${[['dobby_cleanable','Area','Show this room in the picker'],['dobby_daily','Area','Include in each new cleaning day'],['dobby_vacuum','Area','Vacuum only'],['dobby_vacuum_mop','Area','Vacuum and mop'],['dobby_mop','Area','Mop only'],['dobby_room_toggle','One input entity','Four state changes request its room next']].map(r=>`<tr><td><code>${r[0]}</code></td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join('')}</table><p>Only one mode label per Area. With no mode label, vacuum is used and the room's details show a warning. Conflicting modes block that room.</p><h3>Queue behaviour</h3><p>The to-do list is the persistent plan. Select rooms on the card, use the arrows to reorder today, or use the priority button to make a room next. None of these changes modifies tomorrow's default priorities.</p><p>A wall request promotes an existing job without duplicates; a request for an already completed room makes it pending again. The active room is never interrupted by a priority request.</p><p>On arrival home, an owned run returns to the dock and its unfinished room stays pending. On leaving again, it is eligible after the away delay. Run now can explicitly allow a supervised run at home; that override is not restored after a restart.</p><h3>When a room is done</h3><p>Automatic completion requires an observed cleaning run, a new successful Roborock clean record for this job, return to dock, and confirmation of required dust emptying. Docking for mop washing or recharge is not completion. No timeout is treated as success.</p><p>Mop wash decisions remain with the robot's firmware. This scheduler sets the room mode before starting and never explicitly starts a mop wash. Vacuum-only mode avoids requesting mopping; it cannot promise to override all dock firmware behaviour.</p><h3>Overnight reset</h3><p>At the configured local reset time, daily-labelled Areas replace yesterday's list in their default priority order. Ad-hoc requests expire. Reset is deferred while a job is active, and a missed reset is caught after startup.</p><h3>Safety and limitations</h3><p>Use the official Roborock integration with segment-cleaning support. Completion uses a guarded, read-only V1 coordinator adapter; a future API change may block completion until updated. Never run Roborock app schedules or another automation concurrently with this queue.</p><p>Review motion alarms before unattended cleaning. This integration never disarms your alarm, switches lights for feedback, changes maps, or disables Do Not Disturb. The Locate acknowledgement may be suppressed by DND.</p><p>The queue and settings live locally in Home Assistant's storage and are covered by a Home Assistant backup. This bundle contains no third-party trackers, remote scripts or separate robot credentials.</p><p class="small">Version 0.1.2 &bull; locally simulated, not hardware-certified. See README and TESTING.md in the bundle.</p></div>`;}
  diagnostics(){const d=this.data;return `<div class="instructions"><h3>Current status</h3><p>${esc(d.reason)}</p><p><strong>Completion source:</strong> ${esc(d.backend)}</p>${d.telemetry?.legacy?.length?`<div class="warn"><strong>Conflicting legacy automations</strong>${d.telemetry.legacy.map(a=>`<p>${esc(a.name)}<br><code>${esc(a.entity_id)}</code></p>`).join('')}<button data-action="disable-legacy">Disable these old Dobby automations</button><p class="small">Only these recognised automations will be turned off, not deleted. This action requires an administrator.</p></div>`:''}<div class="inline"><button data-action="locate">Test Locate acknowledgement</button><button data-action="export">Download diagnostic snapshot</button><button data-action="queue-info">Open native to-do list</button></div><h3>Latest robot readings</h3><pre>${esc(JSON.stringify(d.telemetry,null,2))}</pre><h3>Current job</h3><pre>${esc(JSON.stringify(d.active,null,2))}</pre><h3>Recent events</h3>${[...(d.log||[])].reverse().map(l=>`<div class="logrow"><time>${new Date(l.at*1000).toLocaleString()}</time>${esc(l.message)}</div>`).join('')||'<p>No events yet.</p>'}</div>`;}
  jobDialog(uid){const j=this.data.jobs.find(j=>j.uid===uid);if(!j)return;this.jobId=uid;const dialog=this.shadowRoot.getElementById('setup');dialog.innerHTML=`<div class="dialoghead"><h2>${esc(j.name)}</h2><button class="icon" data-action="close" aria-label="Close">${icon('mdi:close')}</button></div><div class="pane"><p>${esc(modes[j.mode]||'Mode conflict')} &bull; ${esc(j.map_name)} &bull; room ${esc(j.segments.join(', '))}</p><p class="small">${esc(j.reason||'Waiting for its turn')}</p><div class="field"><label>Note</label><textarea id="job-note" rows="3">${esc(j.note||'')}</textarea></div><div class="savebar"><button data-action="remove-job" data-id="${uid}">Remove from today</button><button data-action="manual-done" data-id="${uid}">Manually confirm cleaned</button><button class="primary" data-action="save-note" data-id="${uid}">Save note</button></div><p class="small">Manual completion is permitted only while docked and is recorded as a user confirmation, not a successful robot report.</p></div>`;if(!dialog.open)dialog.showModal();}
  async click(event){const b=event.target.closest?.('[data-action]');if(!b||b.disabled)return;const a=b.dataset.action,id=b.dataset.id;try{
    if(a==='setup')return await this.openSetup();
    if(a==='diagnostics')return await this.openSetup('diagnostics');
    if(a==='close')return this.shadowRoot.getElementById('setup').close();
    if(a==='tab'){this.tab=id;this.renderDialog();return;}
    if(a==='refresh')return await this.refresh();
    if(a==='run'){const home=this.data.telemetry?.home!==false;if(home&&!window.confirm('Start this queue while someone is home? The cleaning window and safety checks still apply.'))return;await this.command('run',{allow_home:home});return;}
    if(a==='pause'){await this.command('pause');return;}
    if(a==='reset'){if(window.confirm('Replace today\'s list with the daily-labelled rooms in their default order?'))await this.command('reset');return;}
    if(a==='retry'){await this.command('retry');return;}
    if(a==='popup-queue'){const j=this.data.jobs.find(j=>j.area_id===id&&j.status!=='completed');await this.command(j?'remove':'enqueue',j?{uid:j.uid}:{area_id:id});this.renderDialog();return;}
    if(a==='popup-next'){await this.command('enqueue',{area_id:id,urgent:true});this.renderDialog();return;}
    if(a==='toggle-room'){const j=this.data.jobs.find(j=>j.area_id===id&&j.status!=='completed');await this.command(j?'remove':'enqueue',j?{uid:j.uid}:{area_id:id});return;}
    if(a==='promote'){const j=this.data.jobs.find(j=>j.uid===id);await this.command('enqueue',{area_id:j.area_id,urgent:true});return;}
    if(a==='up'||a==='down'){const list=this.data.jobs,i=list.findIndex(j=>j.uid===id),p=a==='up'?(i>1?list[i-2].uid:null):list[i+1]?.uid;await this.command('move',{uid:id,previous_uid:p});return;}
    if(a==='job')return this.jobDialog(id);
    if(a==='save-note'){await this.command('update_note',{uid:id,note:this.shadowRoot.getElementById('job-note').value});this.shadowRoot.getElementById('setup').close();return;}
    if(a==='remove-job'){await this.command('remove',{uid:id});this.shadowRoot.getElementById('setup').close();return;}
    if(a==='manual-done'){if(window.confirm('Confirm you have checked this room was cleaned? This bypasses automatic proof and will be logged as manual.')){await this.command('complete',{uid:id});this.shadowRoot.getElementById('setup').close();}return;}
    if(a==='create-labels'){await this.command('create_labels');this.renderDialog();return;}
    if(a==='detect'){const r=await this.command('detect',{vacuum_entity:this.draft.vacuum_entity});Object.assign(this.draft,r);this.renderDialog();this.toast('Controls suggested. Check them and Save settings.');return;}
    if(a==='save-settings'){await this.command('settings',this.draft);this.toast('Settings saved.');return;}
    if(a==='maps'){await this.command('maps');this.roomDraft=null;this.renderDialog();this.toast('Map data fetched. Review each room and confirm its mapping.');return;}
    if(a==='area'){this.selectedArea=id;this.roomDraft=null;this.renderDialog();return;}
    if(a==='save-room'){const r=this.roomDraft;await this.command('save_room',{area_id:r.area_id,cleanable:r.cleanable,daily:r.daily,mode_label:r.mode_label,priority:r.priority,map_flag:r.map_flag,segments:r.segments,verified:r.verified});this.roomDraft=null;this.renderDialog();this.toast('Room mapping, labels and default priority saved.');return;}
    if(a==='mop-order'){const list=this.data.rooms.filter(r=>r.cleanable).sort((a,b)=>{const rank=r=>r.mode==='vacuum'?100:r.name.toLowerCase()==='kitchen'?0:r.name.toLowerCase().includes('hallway')?1:10;return rank(a)-rank(b)||a.priority-b.priority||a.name.localeCompare(b.name)});if(window.confirm('Save this default order?\n\n'+list.map(r=>r.name).join('\n'))){await this.command('default_order',{area_ids:list.map(r=>r.area_id)});this.roomDraft=null;this.renderDialog();}return;}
    if(a==='add-toggle'){await this.command('set_toggle',{entity_id:this.shadowRoot.getElementById('toggle-choice').value.trim(),enabled:true});this.renderDialog();return;}
    if(a==='remove-toggle'){await this.command('set_toggle',{entity_id:id,enabled:false});this.renderDialog();return;}
    if(a==='disable-legacy'){if(window.confirm('Turn OFF only the old Dobby automations listed here? They will not be deleted.')){await this.command('disable_legacy');this.renderDialog();}return;}
    if(a==='vacuum-info')return this.moreInfo(this.draft.vacuum_entity);
    if(a==='entity-info')return this.moreInfo(id);
    if(a==='queue-info')return this.moreInfo(this.data.entities?.queue);
    if(a==='locate'){await this.command('locate');this.toast('Locate command sent.');return;}
    if(a==='export'){const snapshot=structuredClone(this.data);delete snapshot.candidates;const blob=new Blob([JSON.stringify(snapshot,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='dobby-scheduler-diagnostics.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);return;}
  }catch(e){/* command() displays an actionable error; no optimistic success. */}}
  async change(event){const e=event.target;try{
    if(e.dataset.setting==='auto'){await this.command('enable',{enabled:e.checked});return;}
    if(e.dataset.cfg){const key=e.dataset.cfg;this.draft[key]=e.type==='checkbox'?e.checked:e.type==='number'?Number(e.value):key.endsWith('_entities')?e.value.split(',').map(s=>s.trim()).filter(Boolean):e.value;return;}
    if(e.dataset.room){const key=e.dataset.room;this.roomDraft[key]=e.type==='checkbox'?e.checked:key==='segments'?[...e.selectedOptions].map(o=>Number(o.value)):key==='priority'?Number(e.value):e.value;if(key==='map_flag'){this.roomDraft.segments=[];this.roomDraft.verified=false;this.renderDialog();}else if(key==='segments'){this.roomDraft.verified=false;const box=this.shadowRoot.querySelector('[data-room="verified"]');if(box)box.checked=false;}return;}
  }catch(e){}}
}
if(!customElements.get('dobby-scheduler-card'))customElements.define('dobby-scheduler-card',DobbySchedulerCard);
window.customCards=window.customCards||[];
const dobbyCardInfo = {
  type:'dobby-scheduler-card',
  name:'Dobby Scheduler',
  description:'Label-driven room queue, map setup and vacuum/mop scheduling.',
  documentationURL:'https://github.com/s2n2/roborockHA',
  preview:false
};
// A previous manually added resource can load the same module via another URL.
// Keep both the custom element and the card-picker registration idempotent.
const existingDobbyCard = window.customCards.find(card => card.type === dobbyCardInfo.type);
if (existingDobbyCard) Object.assign(existingDobbyCard, dobbyCardInfo);
else window.customCards.push(dobbyCardInfo);

const registeredDobbyCard = window.customElements.get('dobby-scheduler-card');
if (!registeredDobbyCard) throw new Error('Dobby card definition is missing from the active element registry.');
window.dobbySchedulerCardStatus = {
  version:'0.1.2', stage:'registered',
  elementVersion:registeredDobbyCard.version || 'older-build',
  cardRegistered:true
};
if (registeredDobbyCard !== DobbySchedulerCard && registeredDobbyCard.version !== '0.1.2') {
  console.warn('[Dobby Scheduler 0.1.2] An older card is already registered. Fully refresh this page to use the new card.');
} else {
  console.info('[Dobby Scheduler 0.1.2] Card registered after Home Assistant frontend initialisation.');
}
}
registerDobbySchedulerCard().catch(error => {
  window.dobbySchedulerCardStatus = {version:'0.1.2', stage:'failed', error:String(error)};
  console.error('[Dobby Scheduler 0.1.2] Could not register the card:', error);
});
