import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
ShellRoot {
 id: fixture
 QtObject {
  id: chat
  property var peek: {"preview": true, "scope": "desktop", "source": "", "sink": "", "voice": "alba", "handsFree": true, "muted": false, "reducedMotion": false, "bargeIn": true, "echoCancellation": true, "asrModel": "parakeet-unified", "modelPath": "", "asrThreads": 4, "streamingProfile": "balanced", "endSilence": 0.65, "minSpeech": 0.18, "vadThreshold": 0.55, "maxUtterance": 25, "ttsModel": "pocket", "ttsThreads": 4, "volume": 1.0, "speechRate": 1.0, "wakeEnabled": false, "wakeThreshold": 0.97, "followupSeconds": 12, "screenContext": "on-request", "selectionContext": false, "screenImages": true, "memoryEnabled": true, "quickCommands": true, "personality": "balanced", "expressiveness": 1.0, "companionPosition": 0.16, "defaults": {"endSilence": 0.45, "streamingProfile": "fast", "handsFree": true, "wakeEnabled": false, "noiseRejection": "balanced", "scope": "desktop"}, "enabled": false, "ready": true, "listening": false, "speaking": false, "stage": "listening", "caption": "", "partial": "", "inputLevel": 0.35, "outputLevel": 0.3, "devices": [], "memories": [], "routines": [], "watches": [], "restorePoints": []}
  property string companionScreen: Quickshell.screens[Quickshell.screens.length-1].name
  property string openScreen: companionScreen
  property string page: "chat"
  property string returnPage: "chat"
  property real panelWidth: 350
  property bool pinned: true
  property bool connected: true
  property bool busy: false
  property bool terminalOpen: false
  property bool nativeSession: true
  property string uiVersion: "development"
  property string agentName: "Codex"
  property var permissionModes: [{id:"default",label:"CLI default",description:"Use the CLI's configured permissions."}, {id:"read-only",label:"Read-only",description:"Inspect files without changing the workspace."}, {id:"workspace-write",label:"Workspace",description:"Read and write inside the working folder."}, {id:"auto-review",label:"Auto review",description:"Keep the workspace sandbox and review escalation requests."}]
  readonly property string permissionLabel: (permissionModes.find(m => m.id === (current.permissionMode || "default")) || permissionModes[0]).label
  property var meta: ({agent:"codex",agentName:"Codex",available:true,permissionModes:{codex:permissionModes},settings:{cwd:"/home/demo/Projects/side-chat",model:"",thinking:"default"}})
  property var current: ({id:"preview",title:"Ship Side Chat",agent:"codex",options:{cwd:"/home/demo/Projects/side-chat"},native:{},messages:[{role:"user",text:"Review this repo, fix the failing tests, and explain what changed.",status:"complete",time:Date.now()/1000},{role:"assistant",text:"Fixed the session handoff race and verified the full suite.\n\n170 checks passed. Ready for your next task.",status:"complete",time:Date.now()/1000,model:""}]})
  readonly property var messages: current.messages
  property var chats: []
  property var agentRequests: []
  property var attachments: []
  property var aiPointer: ({visible:false})
  property int editIndex: -1
  property string draft: ""
  property string activity: "Thinking…"
  property string streamingText: ""
  property var streamingTools: []
  property string notice: ""
  property string error: ""
  property var lastRequest: ({})
  signal focusComposer()
  signal companionControlsRequested()
  signal settingsSaved()
  function settleNotice() { notice="" }
  function request(c) {
   lastRequest=c
   if(c.action === "settings") settingsSaved()
   if(c.action === "appearance") meta=Object.assign({},meta,{appearance:Object.assign({},meta.appearance || {},c.settings)})
   if(c.action === "permission_mode") current=Object.assign({},current,{permissionMode:c.mode})
   if(c.action === "peek_settings") peek=Object.assign({},peek,c.settings)
   if(c.action === "peek_listen") peek=Object.assign({},peek,{listening:c.enabled})
  }
  function hover(screen,inside) { }
  function pin() { pinned=true }
  function close() { openScreen="" }
  function show(screen,persistent) { openScreen=screen;pinned=persistent }
  function setPeek(v,reopen) { peek=Object.assign({},peek,{enabled:v});if(v) close();else if(reopen !== false) openConversation() }
  function openConversation() { openScreen=companionScreen;page="chat" }
  function openPeekSettings(from) { openConversation();returnPage=from === "settings" ? "settings" : "chat";page="peek_settings" }
  function startNew() { current=Object.assign({},current,{messages:[]});draft="";page="chat" }
  function submit() { lastRequest={action:"send",text:draft};draft="" }
  function edit(i) { draft=messages[i].text;editIndex=i }
  function retry() { }
  function agentLabel(agent) { return {claude:"Claude",codex:"Codex",omp:"Oh My Pi"}[agent] || agent }
  function selectChat(id) { page="chat" }
  function findItem(item, name) {
   if(item.objectName === name) return item
   for(var child of (item.children || [])) { var found=findItem(child,name);if(found) return found }
   return null
  }
  function addAttachment(p) { }
  function removeAttachment(i) { }
 }
 FileView {
  path: String(Qt.resolvedUrl("manifest.json")).replace("file://", "")
  printErrors: false
  onLoaded: {
   try { chat.uiVersion=String(JSON.parse(text()).version || "development") }
   catch(e) { chat.uiVersion="development" }
  }
 }
 ChatWindow { id: panel; screen: Quickshell.screens[Quickshell.screens.length-1]; chat: chat }
 CompanionWindow { id: buddy; screen: panel.screen; chat: chat }
 IpcHandler {
  target: "side-chat-design"
  function mode(stage: string): void { chat.peek=Object.assign({},chat.peek,{stage:stage,standby:stage === "standby",speaking:stage === "speaking",caption:stage === "speaking" ? "Ready when you are." : ""});chat.busy=stage === "thinking" || stage === "acting" }
  function page(name: string): void { chat.openConversation();if(name === "settings") panel.showSettings();else chat.page=name }
  function controls(): void { chat.companionControlsRequested() }
  function show(): void { chat.peek=Object.assign({},chat.peek,{enabled:true});chat.openConversation() }
  function hide(): void { chat.close() }
  function empty(): void { chat.startNew() }
  function status(): string { return JSON.stringify({request:chat.lastRequest,voice:chat.peek,open:chat.openScreen,page:chat.page,buddy:{left:buddy.margins.left,bottom:buddy.margins.bottom,width:buddy.width,height:buddy.height},panel:{width:panel.width,height:panel.height}}) }
  function section(name: string): void {
   var settings=chat.findItem(panel.contentItem,"peek-settings")
   if(settings) settings.section=name
  }
  function companion(name: string): void {
   var settings=chat.findItem(panel.contentItem,"companion-settings")
   if(settings) settings.section=name
  }
  function expand(enabled: bool): void { chat.request({action:"appearance",settings:{expanded:enabled}}) }
  function finish(): void { Qt.quit() }
  function peek(enabled: bool): void { chat.peek=Object.assign({},chat.peek,{enabled:enabled}) }
  function taskScenario(name: string): void {
   var working=name === "working" || name === "question"
   var steps=[{id:"read",label:"Read settings",state:"observed",kind:"observation",evidence:""},
              {id:"write",label:"Update settings",state:name === "working" ? "running" : name === "review" ? "performed" : "verified",kind:"action",evidence:name === "review" ? "" : "File contents checked after the update"}]
   var task={turn:"preview-"+name,state:working ? "running" : name,label:working ? "Update settings" : name === "verified" ? "Actions verified" : "Review the result",detail:name === "verified" ? "Action results matched their checks." : name === "review" ? "Some results still need checking." : "",total:2,checked:name === "verified" ? 1 : 0,steps:steps}
   chat.busy=working;chat.agentRequests=name === "question" ? [{id:"preview",method:"confirm",title:"Apply these settings?"}] : []
   chat.peek=Object.assign({},chat.peek,{enabled:true,previewScenario:true,stage:name === "question" ? "needs_input" : working ? "acting" : "idle",taskCaption:task.label,task:task,caption:"",speaking:false,partial:"",completedAt:name === "verified" ? Date.now()/1000 : 0})
   chat.close()
  }
  function taskDetails(enabled: bool): void { buddy.contentItem.children.find(c=>c.objectName === "peek-surface").details.expanded=enabled }
  function latest(visible: bool): void { panel.followBottom=!visible }
  function jumpLatest(): void { var button=chat.findItem(panel.contentItem,"jump-to-latest");if(button) button.clicked() }
  function geometry(): string {
   var thread=chat.findItem(panel.contentItem,"message-thread")
   var composer=chat.findItem(panel.contentItem,"chat-composer")
   var latest=chat.findItem(panel.contentItem,"jump-to-latest")
   return JSON.stringify({width:panel.width,height:panel.height,threadHeight:thread.height,composerY:composer.mapToItem(panel.contentItem,0,0).y,latestVisible:latest.visible,scrollY:thread.contentY})
  }
  function scenario(name: string): void {
   chat.openConversation();chat.agentRequests=[];chat.busy=false
   if(name === "empty") chat.startNew()
   if(name === "long") chat.current=Object.assign({},chat.current,{messages:Array.from({length:10},(_,i)=>({role:i%2 ? "assistant" : "user",text:"Message "+(i+1)+". A long conversation to check scrolling, the latest-reply button, and stable composer positioning.",status:"complete",time:Date.now()/1000}))})
   if(name === "approval") chat.agentRequests=[{id:"preview-request",method:"confirm",title:"Allow Bash?",message:"git diff --stat\n\nReview the working tree before running the project checks.",allowAlwaysBash:true}]
   if(name === "long-approval") chat.agentRequests=[{id:"preview-request",method:"confirm",title:"Allow Bash?",message:Array(25).fill("printf 'A long command to inspect before approval'").join("\n"),allowAlwaysBash:true}]
   if(name === "history") {
    chat.chats=[{id:"one",agent:"claude",title:"Polish the Side Chat interface",updated:Date.now()/1000},{id:"two",agent:"codex",title:"Add CLI permission controls",updated:Date.now()/1000},{id:"three",agent:"omp",title:"Plan the next release",updated:Date.now()/1000}];chat.page="history"
   }
   if(name === "tools") chat.current=Object.assign({},chat.current,{messages:[{role:"assistant",text:"The checks passed. Ready to install.",status:"complete",time:Date.now()/1000,tools:[{name:"bash",status:"complete",args:{command:"python3 -m unittest"},output:"All tests passed."},{name:"read",status:"complete",args:{path:"ChatWindow.qml"},output:"Layout reviewed."}]}]})
  }
  function snapshot(name: string): void {
   if(!/^[a-z-]+$/.test(name)) return
   panel.contentItem.children.find(c=>c.objectName === "chat-drawer").grabToImage(r=>r.saveToFile("/tmp/side-chat-"+name+".png"))
  }
  function snapshotCompanion(name: string): void {
   if(!/^[a-z-]+$/.test(name)) return
   var body=chat.findItem(buddy.contentItem,"companion-body")
   if(body) body.grabToImage(r=>r.saveToFile("/tmp/side-chat-"+name+".png"))
  }
  function snapshotControls(name: string): void {
   if(!/^[a-z-]+$/.test(name)) return
   var dock=chat.findItem(buddy.contentItem,"companion-dock")
   if(dock) dock.grabToImage(r=>r.saveToFile("/tmp/side-chat-"+name+".png"))
  }
  function capture(): void {
   panel.contentItem.children.find(c=>c.objectName === "chat-drawer").grabToImage(r=>r.saveToFile("/tmp/side-chat-design-panel.png"))
   buddy.contentItem.children.find(c=>c.objectName === "peek-surface").grabToImage(r=>r.saveToFile("/tmp/side-chat-design-buddy.png"))
  }
 }
}
