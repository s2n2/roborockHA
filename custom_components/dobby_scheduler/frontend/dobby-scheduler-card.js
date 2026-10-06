/* Dobby Scheduler 0.1.6. No external dependencies or remote assets. */

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
  window.dobbySchedulerCardStatus = {version:'0.1.6', stage:'waiting-for-home-assistant'};
  await window.customElements.whenDefined('home-assistant');
  // The global registry may have changed while the native promise was pending.
  // Always resolve against the CURRENT registry, never a cached reference.
  if (!window.customElements.get('home-assistant')) {
    await window.customElements.whenDefined('home-assistant');
  }
  window.dobbySchedulerCardStatus = {version:'0.1.6', stage:'registering'};
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
const reportingFields = [
 ['current_room_entity','Current-room sensor (automatic when blank)','sensor'],
 ['status_entity','Detailed robot status (optional; automatic when blank)','sensor'],
 ['dock_error_entity','Dock-error sensor (optional; automatic when blank)','sensor'],
 ['drying_entity','Mop-drying sensor (optional; automatic when blank)','binary_sensor']
];
const numericFields = [
 ['away_minutes','Away delay (minutes)',0,120], ['minimum_battery','Minimum battery (%)',10,100],
 ['gesture_seconds','Switch-cycle window (seconds)',0.5,5], ['gesture_cooldown','Gesture cooldown (seconds)',2,30],
 ['start_timeout','Start/mode confirmation timeout (seconds)',60,900], ['room_timeout','Room timeout (seconds)',600,21600],
 ['proof_timeout','Completion-record wait (seconds)',60,900], ['empty_timeout','Emptying timeout (seconds)',60,900],
 ['dock_timeout','Connection/recovery timeout (seconds)',60,1800], ['dock_settle','Dock settling time (seconds)',5,120]
];
const styles = `
:host {
  display:block; min-width:0;
  font-family:var(--primary-font-family,Roboto,Arial,sans-serif);
  font-size:14px; line-height:1.45;
  color:var(--primary-text-color,#213438);
  --ds-accent:var(--primary-color,#147d75);
  --ds-surface:var(--ha-card-background,var(--card-background-color,#fff));
  --ds-muted:var(--secondary-text-color,#627579);
  --ds-line:var(--divider-color,#dfe7e7);
  --ds-soft:var(--secondary-background-color,#f2f6f6);
  --ds-tint:color-mix(in srgb,var(--ds-accent) 8%,var(--ds-surface));
}
*,*::before,*::after {box-sizing:border-box}
#main {min-width:0;container-type:inline-size;container-name:dobby-card}
ha-card {
  display:block; min-width:0; overflow:hidden;
  background:var(--ds-surface); color:inherit;
  border:1px solid var(--ds-line);
  border-radius:var(--ha-card-border-radius,18px); box-shadow:none;
}
button,input,select,textarea {font-family:inherit;font-size:14px;line-height:1.4}
button {
  display:inline-flex; align-items:center; justify-content:center; gap:7px;
  min-height:42px; max-width:100%; padding:9px 13px;
  border:1px solid var(--ds-line); border-radius:10px;
  background:var(--ds-surface); color:inherit; cursor:pointer;
  text-align:center; white-space:normal; overflow-wrap:anywhere;
}
button:hover:not(:disabled) {background:var(--ds-tint);border-color:var(--ds-accent)}
button:disabled {opacity:.45;cursor:default}
button.primary {background:var(--ds-accent);color:var(--text-primary-color,#fff);border-color:var(--ds-accent);font-weight:600}
button.primary:hover:not(:disabled) {filter:brightness(.96);background:var(--ds-accent)}
button.icon {flex:0 0 40px;width:40px;min-width:40px;min-height:40px;padding:8px;border-color:transparent;background:transparent}
button.text-button {min-height:36px;padding:6px 8px;border-color:transparent;background:transparent;font-size:12px;color:var(--ds-accent)}
button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,summary:focus-visible {outline:2px solid var(--ds-accent);outline-offset:3px}
ha-icon {--mdc-icon-size:20px;width:20px;height:20px;flex:0 0 20px;display:inline-flex;align-items:center;justify-content:center;vertical-align:middle}
h2,h3,p {overflow-wrap:anywhere}
h2 {font-size:23px;line-height:1.2;margin:4px 0 0;letter-spacing:-.02em;font-weight:650}
h3 {font-size:16px;line-height:1.35;margin:0 0 12px;font-weight:650}
p {margin:0 0 12px;line-height:1.55}
p:last-child {margin-bottom:0}
.head {display:flex;align-items:center;gap:12px;padding:18px 18px 16px}
.robot {width:42px;height:42px;flex:0 0 42px;border-radius:13px;display:grid;place-items:center;background:var(--ds-tint);color:var(--ds-accent)}
.robot ha-icon {--mdc-icon-size:26px;width:26px;height:26px}
.titles {flex:1;min-width:0}
.eyebrow {font-size:10px;line-height:1.5;letter-spacing:.11em;text-transform:uppercase;color:var(--ds-muted);font-weight:650}
.body {padding:0 18px 18px}
.small {font-size:12px;line-height:1.5;color:var(--ds-muted);overflow-wrap:anywhere}
.summary {display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:0;border:1px solid var(--ds-line);border-radius:13px;margin-bottom:12px;overflow:hidden}
.summary .metric {min-width:0;padding:11px 13px;background:var(--ds-surface)}
.summary .metric-main {grid-column:1/-1;background:var(--ds-tint);border-bottom:1px solid var(--ds-line)}
.summary .metric-complete {border-right:1px solid var(--ds-line)}
.summary strong {display:block;min-width:0;margin-top:3px;font-size:18px;line-height:1.3;font-weight:650;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
.summary .metric-main strong {font-size:19px}
.summary .muted-value {font-size:16px;font-weight:500;color:var(--ds-muted)}
.summary .metric-label {font-size:11px;line-height:1.5;color:var(--ds-muted)}
.status {display:flex;align-items:flex-start;gap:8px;font-size:12px;line-height:1.5;margin-bottom:12px;color:var(--ds-muted)}
.activity-summary {display:flex;align-items:center;justify-content:flex-start;gap:9px;width:100%;text-align:left;border:0;background:var(--ds-tint);padding:10px 12px;margin-bottom:10px;min-width:0}
.activity-summary .activity-copy {min-width:0;flex:1;overflow-wrap:anywhere}
.activity-summary .activity-copy strong {display:block;font-size:14px;line-height:1.4}
.activity-summary .activity-copy small {display:block;font-size:10px;color:var(--ds-muted);margin-bottom:2px}
.dot {width:7px;height:7px;flex:0 0 7px;border-radius:50%;background:var(--ds-accent);margin-top:5px}
.controls {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:14px 0 18px}
.controls button {min-width:0;font-size:13px;min-height:44px}
.section {display:flex;align-items:center;justify-content:space-between;gap:10px;margin:18px 0 10px;min-width:0}
.section h3 {font-size:14px;margin:0;min-width:0;flex:1}
.section-tools {display:flex;align-items:center;gap:3px;min-width:0;flex:none}
.section .small {flex:none;font-size:11px}
.chipgrid {display:grid;grid-template-columns:repeat(auto-fit,minmax(min(140px,100%),1fr));gap:8px}
.roomchip {display:flex;align-items:center;justify-content:flex-start;gap:8px;padding:10px;min-width:0;min-height:60px;text-align:left;font-size:13px;border-radius:11px}
.roomchip .chip-copy {flex:1;min-width:0;overflow-wrap:anywhere}
.roomchip .chip-copy>span {display:block;font-weight:550}
.roomchip small {display:block;color:var(--ds-muted);font-size:11px;line-height:1.4;margin-top:3px}
.roomchip .chip-mark {flex:0 0 20px;color:var(--ds-muted)}
.roomchip.selected {border-color:var(--ds-accent);background:var(--ds-tint)}
.roomchip.selected .chip-mark {color:var(--ds-accent)}
.roomchip.done .chip-copy>span {text-decoration:line-through;color:var(--ds-muted)}
.job {display:flex;align-items:center;gap:8px;min-width:0;padding:11px 0;border-bottom:1px solid var(--ds-line)}
.job:last-child {border-bottom:0}
.job.active {background:var(--ds-tint);padding:11px 8px;border-radius:10px}
.job .num {font-size:11px;color:var(--ds-muted);width:20px;flex:0 0 20px;text-align:center;font-variant-numeric:tabular-nums}
.job .text {flex:1;min-width:0;overflow-wrap:anywhere}
.job .text strong {font-size:13px;line-height:1.4;font-weight:600}
.job .small {font-size:11px;margin-top:3px}
.job .actions {display:flex;gap:0;flex:none}
.job .actions button {min-height:36px;min-width:32px;width:32px;flex-basis:32px;padding:5px}
.job .actions ha-icon {--mdc-icon-size:18px;width:18px;height:18px;flex-basis:18px}
.job.done strong {text-decoration:line-through;color:var(--ds-muted)}
.job.done .num {color:var(--ds-accent)}
.empty {padding:18px;border:1px dashed var(--ds-line);border-radius:12px;line-height:1.55;font-size:13px;min-width:0}
.empty-onboarding {display:flex;flex-direction:column;align-items:flex-start;gap:10px;background:var(--ds-soft)}
.empty-onboarding .empty-title {display:flex;align-items:center;gap:9px;font-weight:600;font-size:14px}
.empty-onboarding .empty-title ha-icon {color:var(--ds-accent)}
.empty-onboarding p {margin:0;max-width:48ch}
.empty-onboarding button {margin-top:2px;min-height:40px}
.empty-queue {padding:12px 0;font-size:12px;color:var(--ds-muted)}
.warn {border:1px solid color-mix(in srgb,#b77524 27%,var(--ds-surface));border-left:3px solid #bb802e;background:color-mix(in srgb,#bb802e 7%,var(--ds-surface));padding:11px 12px;margin:12px 0;border-radius:9px;font-size:12px;line-height:1.5;overflow-wrap:anywhere;min-width:0}
.warn strong {font-weight:600}.warn p {margin:8px 0}
.error {border-left-color:#be5945;background:color-mix(in srgb,#be5945 7%,var(--ds-surface))}
.warn-legacy {display:flex;align-items:center;gap:8px}
.warn-legacy>ha-icon {align-self:flex-start;margin-top:1px;color:#bb802e}
.warn-legacy .warn-copy {flex:1;min-width:0}
.warn-legacy button {padding:5px 8px;min-height:34px;font-size:12px;flex:none;background:transparent}
.warn-actions {display:flex;gap:8px;flex-wrap:wrap;margin-top:9px}
.warn-actions button {font-size:12px}
.danger {color:var(--error-color,#ab4b30)}
.foot {margin-top:18px;padding-top:14px;border-top:1px solid var(--ds-line)}
.toggle {display:flex;align-items:center;gap:12px;font-size:13px;line-height:1.4;cursor:pointer}
.toggle input {appearance:none;-webkit-appearance:none;position:relative;margin:0;width:38px;height:22px;min-width:38px;flex:0 0 38px;border:1px solid var(--ds-line);border-radius:20px;background:var(--ds-muted);cursor:pointer}
.toggle input::before {content:'';position:absolute;left:2px;top:2px;width:16px;height:16px;border-radius:50%;background:var(--ds-surface);box-shadow:0 1px 3px #0003;transition:transform .15s ease}
.toggle input:checked {background:var(--ds-accent);border-color:var(--ds-accent)}
.toggle input:checked::before {transform:translateX(16px)}
.foot-note {display:flex;gap:8px;justify-content:space-between;flex-wrap:wrap;font-size:10px;color:var(--ds-muted);line-height:1.5;margin-top:11px}
.toast {position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:var(--primary-text-color,#183735);color:var(--ds-surface);max-width:min(90vw,600px);width:max-content;padding:13px 18px;border-radius:12px;box-shadow:0 8px 35px #0003;z-index:10000;font-size:13px;line-height:1.5;overflow-wrap:anywhere}
/* The modal is outside #main: its layout follows its OWN width, not a dashboard column. */
dialog {container-type:inline-size;container-name:dobby-dialog;padding:0;border:1px solid var(--ds-line);border-radius:18px;background:var(--ds-surface);color:inherit;width:min(920px,calc(100vw - 32px));max-width:none;max-height:calc(100vh - 40px);max-height:calc(100dvh - 40px);overflow:hidden;box-shadow:0 24px 90px #0005;font-size:14px}
dialog[open] {display:flex;flex-direction:column}
dialog::backdrop {background:#14252a88}
.dialogchrome {flex:none;min-width:0;background:var(--ds-surface)}
.dialoghead {padding:18px 22px 14px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex:none}
.dialoghead>div {min-width:0}
.dialoghead h2 {font-size:21px;line-height:1.3}
.tabs {display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:4px;padding:0 16px 12px;border-bottom:1px solid var(--ds-line)}
.tabs button {font-size:12px;line-height:1.35;padding:8px 6px;min-height:39px;border-color:transparent;border-radius:9px}
.tabs button.active {background:var(--ds-tint);color:var(--ds-accent);font-weight:650;border-color:color-mix(in srgb,var(--ds-accent) 25%,var(--ds-surface))}
.pane {padding:20px 22px;overflow-y:auto;overflow-x:hidden;min-height:0;min-width:0;overscroll-behavior:contain;scrollbar-gutter:stable}
.formgrid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px 16px}
.field {display:flex;flex-direction:column;gap:6px;font-size:12px;min-width:0}
.field label {font-weight:600;font-size:12px;line-height:1.45}
.field input,.field select,.field textarea {width:100%;max-width:100%;min-width:0;padding:10px;border:1px solid var(--ds-line);border-radius:9px;min-height:42px;color:inherit;background:var(--ds-surface);margin:0;font-size:13px}
.field textarea {resize:vertical;min-height:70px}
select[multiple] {min-height:168px;padding:6px!important}
select[multiple] option {padding:5px 7px;border-radius:4px}
.span2 {grid-column:1/-1;min-width:0}
.inline {display:flex;align-items:center;gap:10px;flex-wrap:wrap;min-width:0}
.inline label,label.inline {display:flex;align-items:flex-start;gap:8px;line-height:1.5;font-size:12px;min-width:0}
.inline input[type=checkbox] {width:18px;height:18px;flex:0 0 18px;margin:1px 0 0;accent-color:var(--ds-accent)}
.checkbox-grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.savebar {display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;margin-top:20px;padding-top:15px;border-top:1px solid var(--ds-line)}
.savebar button {font-size:13px}
.roomlayout {display:grid;grid-template-columns:minmax(140px,190px) minmax(0,1fr);gap:20px;min-width:0}
.roomlayout>section {min-width:0}
.roomnav {display:flex;flex-direction:column;gap:5px;max-height:620px;overflow:auto;padding-right:3px;min-width:0}
.roomnav button {display:block;text-align:left;font-size:12px;padding:9px 10px;flex:none}
.roomnav button.active {border-color:var(--ds-accent);background:var(--ds-tint)}
.roomnav small {display:block;font-size:10px;line-height:1.4;color:var(--ds-muted);margin-top:3px}
.room-choice {display:none}
.room-toolbar {display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.room-toolbar button {font-size:12px}
.room-toolbar .small {flex-basis:100%;font-size:11px}
.room-queue-actions {display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}
.room-queue-actions button {font-size:12px}
.badge {font-size:10px;border-radius:6px;background:var(--ds-tint);padding:3px 6px;display:inline-block}
code {font:12px ui-monospace,monospace;background:var(--ds-soft);padding:2px 5px;border-radius:4px;overflow-wrap:anywhere}
pre {font:11px/1.55 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;padding:13px;border-radius:9px;background:var(--ds-soft);max-height:340px;max-width:100%;overflow:auto}
.instructions {font-size:13px;line-height:1.6;overflow-wrap:anywhere;min-width:0}
.instructions h3 {margin-top:23px;font-size:15px}.instructions h3:first-child {margin-top:0}
.instructions table,.maptable {width:100%;border-collapse:collapse;font-size:12px;table-layout:fixed}
.instructions td,.instructions th,.maptable td,.maptable th {text-align:left;vertical-align:top;padding:9px 7px;border-bottom:1px solid var(--ds-line);overflow-wrap:anywhere}
.logrow {padding:8px 0;border-bottom:1px solid var(--ds-line);font-size:12px;line-height:1.5;overflow-wrap:anywhere}
.logrow time {font-size:10px;display:block;color:var(--ds-muted)}
.settings-section {padding-bottom:20px;margin-bottom:20px;border-bottom:1px solid var(--ds-line)}
.settings-section h3 {font-size:15px}.settings-section:last-of-type {margin-bottom:0}
details {border:1px solid var(--ds-line);border-radius:10px;padding:12px;margin-top:16px}
summary {cursor:pointer;font-size:13px;line-height:1.5}
a {color:var(--ds-accent)}.muted {color:var(--ds-muted)}
@container dobby-card (min-width:480px) {
  .summary {grid-template-columns:minmax(0,1.7fr) repeat(2,minmax(0,1fr))}
  .summary .metric-main {grid-column:auto;border-bottom:0;border-right:1px solid var(--ds-line)}
  .summary .metric-main strong {font-size:18px}
}
@container dobby-card (max-width:350px) {
  .head {padding:16px 14px 14px;gap:10px}.body {padding:0 14px 15px}
  .job {flex-wrap:wrap;column-gap:6px}.job .text {flex-basis:calc(100% - 34px)}
  .job .actions {margin-left:auto;padding-top:1px}
  .section {flex-wrap:wrap}.section-tools {margin-left:auto}
}
@container dobby-dialog (max-width:720px) {
  .roomlayout {grid-template-columns:minmax(0,1fr);gap:0}
  .roomnav {display:none}.room-choice {display:flex;margin-bottom:16px}
}
@container dobby-dialog (max-width:550px) {
  .dialoghead {padding:16px 16px 12px}.dialoghead h2 {font-size:19px}
  .tabs {grid-template-columns:repeat(3,minmax(0,1fr));padding:0 12px 12px;gap:3px}
  .tabs button {font-size:11px;padding:7px 4px;min-height:37px}
  .pane {padding:16px;scrollbar-gutter:auto}
  .formgrid {grid-template-columns:minmax(0,1fr);gap:14px}
  .checkbox-grid {grid-template-columns:minmax(0,1fr)}
  .span2 {grid-column:1/-1}
  .savebar button {flex:1 1 150px}
  .room-toolbar {display:grid;grid-template-columns:minmax(0,1fr)}
  .room-toolbar button {width:100%;justify-content:flex-start}
  .room-queue-actions button {flex:1 1 120px}
}
@media(max-width:600px) {
  dialog {width:calc(100vw - 16px);max-height:calc(100vh - 16px);max-height:calc(100dvh - 16px);border-radius:14px}
}
@media(prefers-reduced-motion:reduce) {.toggle input::before {transition:none}}
@media(forced-colors:active) {.toggle input {appearance:auto;width:auto}.toggle input::before {display:none}.roomchip.selected {outline:2px solid Highlight}}
`;

class DobbySchedulerCard extends HTMLElement {
  static get version(){return '0.1.6';}
  constructor() {
    super(); this.attachShadow({mode:'open'}); this.tab='rooms'; this.data=null; this.configData=null;
    this.gestureDraft={entity_id:'',label:'dobby_room_double_toggle',event_type:''};
    this.loading=false; this.draft=null; this.roomDraft=null; this.selectedArea=null;
    this.shadowRoot.innerHTML=`<style>${styles}</style><div id="main"></div><dialog id="setup"></dialog><div id="toast" hidden></div>`;
    this.shadowRoot.addEventListener('click', e => this.click(e));
    this.shadowRoot.addEventListener('change', e => this.change(e));
  }
  setConfig(config) { this.config={title:'Dobby',...config}; this.render(); }
  getCardSize(){
    const height=this.shadowRoot?.getElementById('main')?.getBoundingClientRect().height;
    return height?Math.ceil(height/50):8;
  }
  getGridOptions(){return {columns:12,min_columns:6};}
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
    if(!this.data){target.innerHTML=`<ha-card><div class="head"><div class="robot">${icon('mdi:robot-vacuum')}</div><div class="titles"><div class="eyebrow">Room scheduler</div><h2>${esc(this.config?.title||'Dobby')}</h2></div></div><div class="body"><div class="empty empty-onboarding"><strong>${esc(this.error||'Connecting to the local scheduler...')}</strong><p class="small">The Dobby integration must be loaded in Home Assistant. Existing rooms and settings will appear once connected.</p><button data-action="refresh">Reconnect</button></div></div></ha-card>`;return;}
    const d=this.data,jobs=d.jobs||[],pending=jobs.filter(j=>j.status!=='completed'),done=jobs.length-pending.length;
    const current=d.active?.name,next=pending.find(j=>j.uid!==d.active?.uid)?.name;
    const available=(d.rooms||[]).filter(r=>r.cleanable).sort((a,b)=>a.priority-b.priority||a.name.localeCompare(b.name));
    const battery=d.telemetry?.battery;
    const hasBattery=battery!==null&&battery!==undefined&&battery!==''&&Number.isFinite(Number(battery));
    const batteryLabel=hasBattery?Math.round(Number(battery))+'%':'Unknown';
    const roomLabel=current||next||'No rooms queued';
    const fallbackJob=d.active?jobs.find(j=>j.uid===d.active.uid&&j.water_fallback):pending.find(j=>j.water_fallback);
    const skipped=jobs.filter(j=>j.status==='completed'&&j.mopping_skipped);
    target.innerHTML=`<ha-card>
      <div class="head"><div class="robot">${icon('mdi:robot-vacuum')}</div><div class="titles"><div class="eyebrow">Today's room plan</div><h2>${esc(this.config?.title||d.name)}</h2></div><button class="icon" data-action="setup" aria-label="Setup and instructions" title="Setup and instructions">${icon('mdi:cog-outline')}</button></div>
      <div class="body">
        <div class="summary">
          <div class="metric metric-main"><span class="metric-label">${current?'Cleaning / servicing':'Next room'}</span><strong title="${esc(roomLabel)}" ${!current&&!next?'class="muted-value"':''}>${esc(roomLabel)}</strong></div>
          <div class="metric metric-complete"><span class="metric-label">Completed</span><strong>${done} <span class="small">/ ${jobs.length}</span></strong></div>
          <div class="metric"><span class="metric-label">Battery</span><strong ${!hasBattery?'class="muted-value" title="No battery reading is available. Check the robot settings."':''}>${esc(batteryLabel)}</strong></div>
        </div>
        ${d.activity?`<button class="activity-summary" data-action="entity-info" data-id="${esc(d.entities?.activity||'')}" title="Open activity sensor">${icon(d.activity.icon||'mdi:robot-vacuum')}<span class="activity-copy"><small>Robot activity</small><strong>${esc(d.activity.text||'Unknown')}</strong></span></button>`:''}
        <div class="status"><span class="dot" style="${d.enabled||d.manual?'':'background:var(--ds-muted)'}"></span><span>${esc(d.reason)}</span></div>
        ${d.fault?`<div class="warn error" role="alert">${esc(d.fault)}<div class="warn-actions"><button data-action="retry">Retry after checking</button><button data-action="diagnostics">Details</button></div></div>`:''}
        ${fallbackJob&&!d.fault?`<div class="warn water-fallback" role="status"><strong>Vacuum-only fallback</strong><div>${esc(fallbackJob.name)}: water tank needs attention, so mopping is skipped for this run. Room labels stay unchanged.</div></div>`:''}
        ${skipped.length?`<p class="small skipped-mopping">Vacuumed only; mopping skipped: ${esc(skipped.map(j=>j.name).join(', '))}.</p>`:''}
        ${d.telemetry?.legacy?.length?`<div class="warn warn-legacy">${icon('mdi:alert-outline')}<div class="warn-copy"><strong>Old automations are enabled</strong><div>Review them before running Dobby.</div></div><button data-action="diagnostics" aria-label="Review conflicting old Dobby automations">Review</button></div>`:''}
        <div class="controls"><button class="primary" data-action="run" ${!pending.length||d.active?'disabled':''}>${icon('mdi:play')}<span>Run now</span></button><button data-action="pause">${icon('mdi:home-import-outline')}<span>Pause &amp; dock</span></button></div>
        <div class="section"><h3>Today's rooms</h3><div class="section-tools">${available.length?`<button class="text-button" data-action="reset" ${d.active?'disabled':''} title="Restore daily rooms in their default order">Daily defaults</button>`:''}<button class="icon" data-action="setup" aria-label="Configure rooms">${icon('mdi:tune')}</button></div></div>
        ${available.length?`<div class="chipgrid">${available.map(r=>{const j=jobs.find(j=>j.area_id===r.area_id),selected=j?.status==='needs_action',complete=j?.status==='completed';return `<button class="roomchip ${selected?'selected':''} ${complete?'done':''}" data-action="toggle-room" data-id="${esc(r.area_id)}" aria-pressed="${!!selected}" title="${esc(r.name)}: ${complete?'request another clean':selected?'remove from today':'add to today'}"><span class="chip-mark">${icon(complete?'mdi:check-circle-outline':selected?'mdi:check-circle':'mdi:circle-outline')}</span><span class="chip-copy"><span>${esc(r.name)}</span><small>${complete?(j.mopping_skipped?'Vacuumed only - mop skipped':'Done - tap to repeat'):j?.water_fallback?'Vacuum only - mop skipped':esc(modes[r.mode]||'Mode conflict')}</small></span></button>`}).join('')}</div>`:`<div class="empty empty-onboarding"><div class="empty-title">${icon('mdi:floor-plan')}<span>Set up your rooms</span></div><p class="small">Choose Areas, check the room numbers, and set vacuum or mop. No per-room YAML needed.</p><button data-action="setup">Configure rooms ${icon('mdi:arrow-right')}</button></div>`}
        ${available.length||jobs.length?`<div class="section"><h3>Execution order</h3><span class="small">${pending.length} pending</span></div>
        ${jobs.map((j,i)=>`<div class="job ${j.status==='completed'?'done':''} ${d.active?.uid===j.uid?'active':''}"><span class="num">${j.status==='completed'?'&#10003;':d.active?.uid===j.uid?'&#9654;':i+1}</span><div class="text"><strong>${esc(j.name)}</strong><div class="small">${j.water_fallback?'Vacuum only &bull; mopping skipped':esc(modes[j.effective_mode||j.mode]||'Check mode labels')}${j.source==='wall_toggle'?' &bull; wall request':''}${j.urgent?' &bull; priority':''}${d.active?.uid===j.uid?' &bull; '+esc(d.active.phase):''}</div></div><div class="actions"><button class="icon" data-action="promote" data-id="${esc(j.uid)}" title="Make next" aria-label="Make ${esc(j.name)} next" ${j.status==='completed'||d.active?.uid===j.uid?'disabled':''}>${icon('mdi:priority-high')}</button><button class="icon" data-action="up" data-id="${esc(j.uid)}" aria-label="Move ${esc(j.name)} up" ${i===0?'disabled':''}>${icon('mdi:chevron-up')}</button><button class="icon" data-action="down" data-id="${esc(j.uid)}" aria-label="Move ${esc(j.name)} down" ${i===jobs.length-1?'disabled':''}>${icon('mdi:chevron-down')}</button><button class="icon" data-action="job" data-id="${esc(j.uid)}" aria-label="${esc(j.name)} details">${icon('mdi:dots-horizontal')}</button></div></div>`).join('')||'<div class="empty-queue">Select rooms above, or use Daily defaults.</div>'}`:''}
        <div class="foot"><label class="toggle"><input type="checkbox" role="switch" data-setting="auto" ${d.enabled?'checked':''}><span>Automatic when away</span></label><div class="foot-note"><span>Local queue &middot; ${esc(d.day||'Not initialised')}</span><span title="Single press, one cycle or two cycles, selected by the input label.">Button / switch requests make a room next</span></div></div>
        ${this.error?`<div class="warn error" role="alert">Connection warning: ${esc(this.error)}</div>`:''}
      </div></ha-card>`;
  }
  async openSetup(tab='rooms'){
    this.tab=tab;await this.refresh(true);this.renderDialog();const dialog=this.shadowRoot.getElementById('setup');if(!dialog.open)dialog.showModal();
  }
  renderDialog(){
    const d=this.data;if(!d)return;
    const dialog=this.shadowRoot.getElementById('setup');
    dialog.innerHTML=`<div class="dialogchrome"><div class="dialoghead"><div><div class="eyebrow">DOBBY SCHEDULER</div><h2>Setup &amp; instructions</h2></div><button class="icon" data-action="close" aria-label="Close setup">${icon('mdi:close')}</button></div><div class="tabs">${[['rooms','Rooms & map'],['settings','Robot & schedule'],['switches','Buttons & switches'],['help','Instructions'],['diagnostics','Diagnostics']].map(([id,label])=>`<button data-action="tab" data-id="${id}" class="${this.tab===id?'active':''}" aria-pressed="${this.tab===id}">${label}</button>`).join('')}</div></div><div class="pane">${this.pane()}</div>`;
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
    return `<div class="warn">Save the robot settings first, then fetch maps under Rooms &amp; map. Finding controls never enables cleaning.</div><section class="settings-section"><h3>Robot &amp; presence</h3><div class="formgrid">${entityFields.slice(0,2).map(f=>this.field(...f)).join('')}<div class="span2"><button data-action="detect">Find controls for this vacuum</button> <button data-action="vacuum-info">Open vacuum controls</button></div>${entityFields.slice(2,9).map(f=>this.field(...f)).join('')}<div class="field"><label>Mop intensity for wet rooms</label><input data-cfg="mop_intensity" value="${esc(c.mop_intensity)}"><span class="small">Use an exact supported option, e.g. medium. Not changed for vacuum-only rooms.</span></div><div class="field span2"><label>Water problem entities (comma-separated)</label><textarea data-cfg="water_problem_entities">${esc(c.water_problem_entities.join(', '))}</textarea><span class="small">Use only water-tank problem sensors: clean tank empty/missing, robot water shortage, dirty tank full/missing. on = tank alert; unknown/offline still blocks wet jobs.</span><label class="inline"><input type="checkbox" data-cfg="vacuum_on_water_problem" ${c.vacuum_on_water_problem!==false?'checked':''}> Vacuum instead when a water tank needs attention</label><span class="small">Enabled by default for mop and vacuum + mop rooms. Confirms vacuum mode before starting, keeps labels unchanged, and records mopping skipped. Other vacuum faults still block.</span></div><div class="field span2"><label>Extra pause entities (comma-separated)</label><textarea data-cfg="blocking_entities">${esc(c.blocking_entities.join(', '))}</textarea><span class="small">on or unavailable blocks cleaning, e.g. a babysitter or manual pause helper. Never add the alarm here to try to disable it.</span></div></div></section><section class="settings-section"><h3>Schedule &amp; gestures</h3><div class="formgrid"><div class="field"><label>Nightly reset</label><input type="time" data-cfg="reset_time" value="${esc(c.reset_time)}"></div><div class="field"><label>Cleaning starts after</label><input type="time" data-cfg="window_start" value="${esc(c.window_start)}"></div><div class="field"><label>Cleaning stops at</label><input type="time" data-cfg="window_end" value="${esc(c.window_end)}"></div>${numericFields.slice(0,4).map(([k,l,a,b])=>`<div class="field"><label>${esc(l)}</label><input type="number" step="${k.includes('gesture')?'.1':'1'}" min="${a}" max="${b}" data-cfg="${k}" value="${esc(c[k])}"></div>`).join('')}<div class="span2 inline checkbox-grid">${[['acknowledge','Locate voice acknowledgement'],['reject_automation_context','Ignore known automation-generated switch changes'],['empty_after_room','Empty after every room'],['empty_after_mop','Also empty after mop-only rooms']].map(([k,l])=>`<label><input type="checkbox" data-cfg="${k}" ${c[k]?'checked':''}> ${esc(l)}</label>`).join('')}</div></div></section><section class="settings-section"><h3>Activity &amp; room history</h3><p class="small">A room must be reported unchanged for a full minute before it appears in the activity text. Brief hallway crossings keep the last confirmed room; return-to-dock, errors and dock operations update without this delay. These are read-only observations, not proof of a completed clean.</p><div class="formgrid">${reportingFields.map(f=>this.field(...f)).join('')}<div class="field"><label>Room confirmation (seconds)</label><input type="number" min="1" max="600" step="1" data-cfg="room_confirm_seconds" value="${esc(c.room_confirm_seconds??60)}"><span class="small">Default 60. Applied on the next local update; no extra robot polling.</span></div><div class="field small"><strong>Reusable sensors</strong><code>${esc(this.data.entities?.activity||'sensor.dobby_scheduler_activity')}</code><code>${esc(this.data.entities?.room_stable||'sensor.dobby_scheduler_room_stable')}</code><span>Use just Activity in a logbook card. Including the original room sensor or whole robot device brings back the unfiltered events.</span></div></div></section><details><summary>Advanced timeouts and completion adapter</summary><div class="formgrid" style="margin-top:14px">${numericFields.slice(4).map(([k,l,a,b])=>`<div class="field"><label>${l}</label><input type="number" min="${a}" max="${b}" data-cfg="${k}" value="${esc(c[k])}"></div>`).join('')}${this.field(...entityFields[9])}<div class="small span2">Normally leave the completed-record entity blank. The included read-only adapter uses the official Roborock V1 completed-clean record. An optional custom sensor must expose begin/end epoch seconds, complete=1, error=0, area&gt;0 and optionally map_flag. A last-clean timestamp alone is not enough.</div></div></details><div class="savebar"><button class="primary" data-action="save-settings">Save settings</button></div>`;
  }
  roomsPane(){
    const d=this.data, labels=d.labels||{};
    if(Object.keys(labels).length<8)return `<div class="empty"><h3>Create the Dobby labels</h3><p>These will be ordinary Home Assistant labels, editable in Home Assistant as well as here.</p><button class="primary" data-action="create-labels">Create missing Dobby labels</button><p class="small">No rooms will be selected automatically and Dobby will not start.</p></div>`;
    const areas=[...d.rooms].sort((a,b)=>a.priority-b.priority||a.name.localeCompare(b.name));
    if(!areas.length)return `<div class="empty">Create your rooms as Home Assistant Areas first, then return here.</div>`;
    if(!this.selectedArea||!areas.some(a=>a.area_id===this.selectedArea))this.selectedArea=areas[0].area_id;
    if(!this.roomDraft||this.roomDraft.area_id!==this.selectedArea)this.roomDraft=structuredClone(areas.find(a=>a.area_id===this.selectedArea));
    const r=this.roomDraft, m=d.maps.find(m=>String(m.flag)===String(r.map_flag)), checked=(r.segments||[]).map(String);
    return `<div class="room-toolbar"><button data-action="maps">${icon('mdi:map-search-outline')} Fetch/check maps</button><button data-action="mop-order">Use mopping-first defaults</button><span class="small">${d.maps_at?'Map data fetched '+new Date(d.maps_at*1000).toLocaleString():'No map data fetched yet'}</span></div><div class="warn">Confirm numbers against the live Roborock map, not an old floor-plan card. Saving a row writes the Area's Dobby labels and stores only its mapping/order here. The selected robot map must match before a room can run.</div><div class="field room-choice"><label for="room-choice">Room to configure</label><select id="room-choice" data-room-choice>${areas.map(a=>`<option value="${esc(a.area_id)}" ${a.area_id===r.area_id?'selected':''}>${esc(a.name)}</option>`).join('')}</select></div><div class="roomlayout"><nav class="roomnav">${areas.map(a=>`<button data-action="area" data-id="${esc(a.area_id)}" class="${a.area_id===r.area_id?'active':''}">${esc(a.name)}<small>${a.cleanable?(a.verified&&!a.mapping_error?'Mapped':'Needs mapping'):'Not in picker'} &bull; ${esc(modes[a.mode]||'Mode conflict')}</small></button>`).join('')}</nav><section><h3>${esc(r.name)}</h3><div class="room-queue-actions"><button data-action="popup-queue" data-id="${esc(r.area_id)}" ${!d.rooms.find(a=>a.area_id===r.area_id)?.cleanable?'disabled':''}>${d.jobs.some(j=>j.area_id===r.area_id&&j.status!=='completed')?'Remove from today':'Add to today'}</button><button data-action="popup-next" data-id="${esc(r.area_id)}" ${!d.rooms.find(a=>a.area_id===r.area_id)?.cleanable?'disabled':''}>Make next</button></div><div class="formgrid"><div class="inline span2"><label><input type="checkbox" data-room="cleanable" ${r.cleanable?'checked':''}> Available to Dobby</label><label><input type="checkbox" data-room="daily" ${r.daily?'checked':''}> Daily default</label></div><div class="field"><label>Cleaning-mode label</label><select data-room="mode_label"><option value="" ${!r.mode_label?'selected':''}>No label (defaults to vacuum)</option><option value="dobby_vacuum" ${r.mode_label==='dobby_vacuum'?'selected':''}>Dobby vacuum</option><option value="dobby_vacuum_mop" ${r.mode_label==='dobby_vacuum_mop'?'selected':''}>Dobby vacuum and mop</option><option value="dobby_mop" ${r.mode_label==='dobby_mop'?'selected':''}>Dobby mop</option></select></div><div class="field"><label>Default priority (lower first)</label><input type="number" min="0" max="10000" data-room="priority" value="${esc(r.priority)}"></div><div class="field span2"><label>Roborock map</label><select data-room="map_flag"><option value="">Choose fetched map</option>${d.maps.map(m=>`<option value="${m.flag}" ${String(m.flag)===String(r.map_flag)?'selected':''}>${esc(m.name)} (map ${m.flag})</option>`).join('')}</select><span class="small">Currently selected on Dobby: ${esc(d.telemetry?.map_name||'Unknown')}</span></div><div class="field span2"><label>Room number(s)</label><select multiple data-room="segments">${m?Object.entries(m.rooms).sort((a,b)=>Number(a[0])-Number(b[0])).map(([n,name])=>`<option value="${n}" ${checked.includes(n)?'selected':''}>${n} - ${esc(name)}</option>`).join(''):''}</select><span class="small">Multiple segments in one Area share a mode. Use separate Areas for hallway carpet and hallway tiles if their cleaning modes differ.</span></div><label class="inline span2"><input type="checkbox" data-room="verified" ${r.verified?'checked':''}> I checked that these numbers really are ${esc(r.name)} on this map.</label></div>${r.mapping_error?`<div class="warn error">${esc(r.mapping_error)}</div>`:''}<div class="savebar"><button class="primary" data-action="save-room">Save this room</button></div></section></div>`;
  }
  switchPane(){
    const d=this.data,g=this.gestureDraft;
    const names={dobby_room_press:'Single press',dobby_room_toggle:'One switch cycle',dobby_room_double_toggle:'Two switch cycles'};
    const inputs=['switch','light','binary_sensor','input_boolean'];
    const candidates=(this.configData?.candidates||[]).filter(e=>(g.label==='dobby_room_press'?[...inputs,'button','input_button','event']:inputs).includes(e.entity_id.split('.')[0]));
    const selected=candidates.find(e=>e.entity_id===g.entity_id);
    const pattern=g.label==='dobby_room_press'?'One short press or OFF → ON. Button release is not another request.':g.label==='dobby_room_toggle'?'OFF → ON → OFF, or ON → OFF → ON.':'OFF → ON → OFF → ON → OFF, or the opposite.';
    const entries=d.gesture_entities||Object.fromEntries(Object.entries(d.toggle_entities||{}).map(([e,a])=>[e,{area_id:a,label:'dobby_room_double_toggle'}]));
    const missing=['dobby_room_toggle','dobby_room_double_toggle','dobby_room_press'].some(k=>!d.labels?.[k]);
    return `<div class="instructions"><h3>One label, one room request</h3><p>Give the input its room's Area and choose the gesture below. The room becomes <strong>next</strong>, without interrupting the room Dobby is already cleaning.</p></div>
      ${missing?'<div class="warn">Add the new labels before assigning gestures. Existing room labels are preserved.<div class="savebar"><button data-action="create-labels">Create missing Dobby labels</button></div></div>':''}
      <div class="warn"><strong>Upgrading from 0.1.3?</strong> <code>dobby_room_toggle</code> now means one cycle, not two. Change existing inputs to <code>dobby_room_double_toggle</code> to keep their old behaviour.</div>
      <section class="settings-section"><h3>Configure a button or switch</h3><div class="formgrid">
      <div class="field"><label for="gesture-label">Gesture</label><select id="gesture-label" data-gesture="label">${Object.entries(names).map(([v,n])=>`<option value="${v}" ${g.label===v?'selected':''}>${n}</option>`).join('')}</select><span class="small"><code>${esc(g.label)}</code></span></div>
      <div class="field"><label for="toggle-choice">Input entity</label><input id="toggle-choice" data-gesture="entity_id" list="toggle-list" value="${esc(g.entity_id)}" placeholder="Choose a button, event or physical input"><datalist id="toggle-list">${candidates.map(e=>`<option value="${esc(e.entity_id)}">${esc(e.name)}</option>`).join('')}</datalist><span class="small">The entity's Area overrides its device's Area. Do not label both a switch input and its mirrored light output.</span></div>
      <div class="span2 small">${esc(pattern)} ${g.label!=='dobby_room_press'?`Complete within ${esc(this.draft.gesture_seconds)} seconds.`:''} A ${esc(this.draft.gesture_cooldown)}-second cooldown suppresses repeats.</div>
      ${g.label==='dobby_room_press'?`<div class="field span2"><label for="press-event-type">Event type (event entities only, optional)</label><input id="press-event-type" data-gesture="event_type" list="press-event-types" value="${esc(g.event_type)}" placeholder="Automatic short-press detection"><datalist id="press-event-types">${(selected?.event_types||[]).map(t=>`<option value="${esc(t)}"></option>`).join('')}</datalist><span class="small">Blank accepts common short-press types, including press_end, single, single_press and press. Holds/doubles are not included. Set an exact type if your integration uses another name. ${selected?.event_type?`Last reported: ${esc(selected.event_type)}.`:''}</span></div>`:''}
      </div><div class="savebar"><button class="primary" data-action="add-toggle">Save gesture label</button></div></section>
      <section class="settings-section"><h3>Locate acknowledgement: ${this.draft.acknowledge?'on':'off'}</h3><p class="small">Every accepted request uses <code>vacuum.locate</code> to play Dobby's usual locator sound. The queue is saved first; a sound failure does not remove the room. Robot volume and Do Not Disturb can suppress the sound.</p><div class="inline"><button data-action="locate">Test Locate</button><button data-action="tab" data-id="settings">Change feedback settings</button></div></section>
      <h3>Currently labelled</h3>${Object.entries(entries).map(([e,c])=>`<div class="job"><div class="text"><strong>${esc(e)}</strong><div class="small">${esc(d.rooms.find(r=>r.area_id===c.area_id)?.name||'No Area assigned')} · ${esc(names[c.label]||c.label)}${c.event_type?` · ${esc(c.event_type)}`:''}</div></div><div class="actions"><button data-action="edit-gesture" data-id="${esc(e)}" class="icon" aria-label="Edit gesture">${icon('mdi:pencil-outline')}</button><button data-action="entity-info" data-id="${esc(e)}" class="icon" aria-label="Open entity settings">${icon('mdi:cog-outline')}</button><button data-action="remove-toggle" data-id="${esc(e)}" class="icon" aria-label="Remove gesture labels">${icon('mdi:close')}</button></div></div>`).join('')||'<p class="small">No gestures are enabled yet.</p>'}
      ${(d.gesture_issues||[]).map(i=>`<div class="warn"><code>${esc(i.entity_id)}</code><p>${esc(i.message)}</p><button data-action="remove-toggle" data-id="${esc(i.entity_id)}">Remove gesture labels</button></div>`).join('')}
      <details><summary>Other button types and avoiding accidental requests</summary><p class="small">A momentary binary input triggers only OFF → ON, not its release. Button and input_button timestamps must be fresh; old timestamps restored at startup are ignored. An input_button can also bridge raw ZHA or Shelly button events through one normal Home Assistant UI automation. Raw event-bus messages alone cannot carry entity labels.</p><p class="small">Cloud switches may be too slow for a two-second cycle. Use one local physical input where possible. Only one gesture label per input; conflicting labels are blocked. The short alias <code>room_press</code> is accepted for <code>dobby_room_press</code>.</p></details>`;
  }
  help(){return `<div class="instructions"><h3>One-time setup</h3><p>1. Under <strong>Robot &amp; schedule</strong>, select the vacuum and home-presence sensor. Use Find controls, check each proposed entity and save.</p><p>2. Under <strong>Rooms &amp; map</strong>, create the labels, fetch maps, select each Area's mode, priority and exact segment numbers, and confirm the mapping.</p><p>3. Label wall-switch inputs under <strong>Buttons &amp; switches</strong>. Their entity Area takes precedence over their device Area.</p><p>4. Disable the old vacuum scheduler and any automatic map-reset routine. Restore Daily defaults and test one room under supervision before enabling Automatic when away.</p><h3>Labels</h3><table><tr><th>Label</th><th>Apply to</th><th>Meaning</th></tr>${[['dobby_cleanable','Area','Show this room in the picker'],['dobby_daily','Area','Include in each new cleaning day'],['dobby_vacuum','Area','Vacuum only'],['dobby_vacuum_mop','Area','Vacuum and mop'],['dobby_mop','Area','Mop only'],['dobby_room_toggle','One on/off input','One complete switch cycle (2 changes)'],['dobby_room_double_toggle','One on/off input','Two complete cycles (4 changes)'],['dobby_room_press','Button/event or momentary input','One press; room_press is also recognised']].map(r=>`<tr><td><code>${r[0]}</code></td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join('')}</table><p>Only one mode label per Area. With no mode label, vacuum is used and the room's details show a warning. Conflicting modes block that room.</p><h3>Queue behaviour</h3><p>The to-do list is the persistent plan. Select rooms on the card, use the arrows to reorder today, or use the priority button to make a room next. None of these changes modifies tomorrow's default priorities.</p><p>A wall request promotes an existing job without duplicates; a request for an already completed room makes it pending again. The active room is never interrupted by a priority request.</p><p>On arrival home, an owned run returns to the dock and its unfinished room stays pending. On leaving again, it is eligible after the away delay. Run now can explicitly allow a supervised run at home; that override is not restored after a restart.</p><h3>When a room is done</h3><p>Automatic completion requires an observed cleaning run, a new successful Roborock clean record for this job, return to dock, and confirmation of required dust emptying. Docking for mop washing or recharge is not completion. No timeout is treated as success.</p><p>Mop wash decisions remain with the robot's firmware. This scheduler sets the room mode before starting and never explicitly starts a mop wash. Vacuum-only mode avoids requesting mopping; it cannot promise to override all dock firmware behaviour.</p><h3>Water-tank fallback</h3><p>With Vacuum instead when a water tank needs attention enabled, confirmed configured tank alerts switch mop and vacuum + mop jobs to vacuum for that attempt only. Unavailable water sensors are not assumed to mean an empty tank. Room labels and normal priorities remain unchanged.</p><p>If the water problem appears during a wet clean, Dobby docks and restarts that room from the beginning in vacuum-only mode. It is completed only after the normal successful record, dock and required emptying checks. The queue says Vacuumed only - mop skipped; refilling does not silently repeat completed rooms. Tap a room to repeat it, or let the next daily reset use its original mode. Robot errors, pause/presence rules and unsuccessful records still block.</p><h3>Overnight reset</h3><p>At the configured local reset time, daily-labelled Areas replace yesterday's list in their default priority order. Ad-hoc requests expire. Reset is deferred while a job is active, and a missed reset is caught after startup.</p><h3>Activity and room history</h3><p>The Activity sensor shows what the robot reports, even when this scheduler is disabled. A new cleaning spell starts as Cleaning (or Mopping) and gains its room name only after a continuous confirmation window. The scheduled target is kept separately; it is not treated as observed location.</p><p>The Confirmed room sensor holds the last accepted room during shorter changes. An unknown/disconnected room source clears the confirmation window. A restart or map/source change begins a fresh window. Faults and dock operations are not delayed. Historical entries are recorded when confirmed, not backdated.</p><p>In a native Activity/logbook card, target only the Activity sensor for clean history. A whole-device target includes the original noisy room readings too. Reporting changes do not start, stop, or complete jobs.</p><h3>Safety and limitations</h3><p>Use the official Roborock integration with segment-cleaning support. Completion uses a guarded, read-only V1 coordinator adapter; a future API change may block completion until updated. Never run Roborock app schedules or another automation concurrently with this queue.</p><p>Review motion alarms before unattended cleaning. This integration never disarms your alarm, switches lights for feedback, changes maps, or disables Do Not Disturb. The Locate acknowledgement may be suppressed by DND.</p><p>The queue and settings live locally in Home Assistant's storage and are covered by a Home Assistant backup. This bundle contains no third-party trackers, remote scripts or separate robot credentials.</p><p class="small">Version 0.1.6 &bull; locally simulated, not hardware-certified. See README and TESTING.md in the bundle.</p></div>`;}
  diagnostics(){const d=this.data;return `<div class="instructions"><h3>Current status</h3><p>${esc(d.reason)}</p><p><strong>Completion source:</strong> ${esc(d.backend)}</p>${d.telemetry?.legacy?.length?`<div class="warn"><strong>Conflicting legacy automations</strong>${d.telemetry.legacy.map(a=>`<p>${esc(a.name)}<br><code>${esc(a.entity_id)}</code></p>`).join('')}<button data-action="disable-legacy">Disable these old Dobby automations</button><p class="small">Only these recognised automations will be turned off, not deleted. This action requires an administrator.</p></div>`:''}<div class="inline"><button data-action="locate">Test Locate acknowledgement</button><button data-action="export">Download diagnostic snapshot</button><button data-action="queue-info">Open native to-do list</button></div><h3>Activity &amp; confirmed room</h3><pre>${esc(JSON.stringify(d.activity||{},null,2))}</pre><h3>Latest robot readings</h3><pre>${esc(JSON.stringify(d.telemetry,null,2))}</pre><h3>Current job</h3><pre>${esc(JSON.stringify(d.active,null,2))}</pre><h3>Recent events</h3>${[...(d.log||[])].reverse().map(l=>`<div class="logrow"><time>${new Date(l.at*1000).toLocaleString()}</time>${esc(l.message)}</div>`).join('')||'<p>No events yet.</p>'}</div>`;}
  jobDialog(uid){const j=this.data.jobs.find(j=>j.uid===uid);if(!j)return;this.jobId=uid;const dialog=this.shadowRoot.getElementById('setup');dialog.innerHTML=`<div class="dialoghead"><h2>${esc(j.name)}</h2><button class="icon" data-action="close" aria-label="Close">${icon('mdi:close')}</button></div><div class="pane"><p>${esc(modes[j.mode]||'Mode conflict')} &bull; ${esc(j.map_name)} &bull; room ${esc(j.segments.join(', '))}</p>${j.water_fallback?`<div class="warn water-fallback"><strong>Vacuum only - mopping skipped</strong><p>Requested: ${esc(modes[j.requested_mode||j.mode]||'Unknown')}. ${esc(j.fallback_reason||'Water tank needs attention')}. The room label is unchanged.</p></div>`:''}<p class="small">${esc(j.reason||'Waiting for its turn')}</p><div class="field"><label>Note</label><textarea id="job-note" rows="3">${esc(j.note||'')}</textarea></div><div class="savebar"><button data-action="remove-job" data-id="${uid}">Remove from today</button><button data-action="manual-done" data-id="${uid}">Manually confirm cleaned</button><button class="primary" data-action="save-note" data-id="${uid}">Save note</button></div><p class="small">Manual completion is permitted only while docked and is recorded as a user confirmation, not a successful robot report.</p></div>`;if(!dialog.open)dialog.showModal();}
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
    if(a==='add-toggle'){this.gestureDraft.entity_id=this.shadowRoot.getElementById('toggle-choice').value.trim();this.gestureDraft.event_type=this.shadowRoot.getElementById('press-event-type')?.value.trim()||'';await this.command('set_gesture',{...this.gestureDraft,enabled:true});this.renderDialog();this.toast('Gesture saved. Its Area will be queued next.');return;}
    if(a==='edit-gesture'){const spec=this.data.gesture_entities?.[id];if(spec){this.gestureDraft={entity_id:id,label:spec.label,event_type:spec.event_type||''};this.renderDialog();}return;}
    if(a==='remove-toggle'){await this.command('set_gesture',{entity_id:id,enabled:false});this.renderDialog();return;}
    if(a==='disable-legacy'){if(window.confirm('Turn OFF only the old Dobby automations listed here? They will not be deleted.')){await this.command('disable_legacy');this.renderDialog();}return;}
    if(a==='vacuum-info')return this.moreInfo(this.draft.vacuum_entity);
    if(a==='entity-info')return this.moreInfo(id);
    if(a==='queue-info')return this.moreInfo(this.data.entities?.queue);
    if(a==='locate'){await this.command('locate');this.toast('Locate command sent.');return;}
    if(a==='export'){const snapshot=structuredClone(this.data);delete snapshot.candidates;const blob=new Blob([JSON.stringify(snapshot,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='dobby-scheduler-diagnostics.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);return;}
  }catch(e){/* command() displays an actionable error; no optimistic success. */}}
  async change(event){const e=event.target;try{
    if(e.dataset.gesture){this.gestureDraft[e.dataset.gesture]=e.value;if(e.dataset.gesture==='label')this.renderDialog();if(e.dataset.gesture==='entity_id'){const item=(this.configData?.candidates||[]).find(c=>c.entity_id===e.value);const list=this.shadowRoot.getElementById('press-event-types');if(list)list.innerHTML=(item?.event_types||[]).map(t=>`<option value="${esc(t)}"></option>`).join('');}return;}
    if(e.dataset.setting==='auto'){await this.command('enable',{enabled:e.checked});return;}
    if(e.matches('[data-room-choice]')){this.selectedArea=e.value;this.roomDraft=null;this.renderDialog();return;}
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
  version:'0.1.6', stage:'registered',
  elementVersion:registeredDobbyCard.version || 'older-build',
  cardRegistered:true
};
if (registeredDobbyCard !== DobbySchedulerCard && registeredDobbyCard.version !== '0.1.6') {
  console.warn('[Dobby Scheduler 0.1.6] An older card is already registered. Fully refresh this page to use the new card.');
} else {
  console.info('[Dobby Scheduler 0.1.6] Card registered after Home Assistant frontend initialisation.');
}
}
registerDobbySchedulerCard().catch(error => {
  window.dobbySchedulerCardStatus = {version:'0.1.6', stage:'failed', error:String(error)};
  console.error('[Dobby Scheduler 0.1.6] Could not register the card:', error);
});
