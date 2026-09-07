import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
ShellRoot {
 id: fixture
 QtObject {
  id: chat
  property var jarvis: {"preview": true, "scope": "desktop", "source": "", "sink": "", "voice": "alba", "handsFree": true, "muted": false, "reducedMotion": false, "bargeIn": true, "echoCancellation": true, "asrModel": "parakeet-unified", "modelPath": "", "asrThreads": 4, "streamingProfile": "balanced", "endSilence": 0.65, "minSpeech": 0.18, "vadThreshold": 0.55, "maxUtterance": 25, "ttsModel": "pocket", "ttsThreads": 4, "volume": 1.0, "speechRate": 1.0, "wakeEnabled": false, "wakeThreshold": 0.97, "followupSeconds": 12, "screenContext": "on-request", "selectionContext": false, "screenImages": true, "memoryEnabled": true, "quickCommands": true, "personality": "balanced", "expressiveness": 1.0, "companionPosition": 0.16, "enabled": true, "ready": true, "listening": true, "speaking": false, "stage": "listening", "caption": "", "partial": "", "inputLevel": 0.35, "outputLevel": 0.3, "devices": [], "memories": [], "routines": [], "watches": [], "restorePoints": []}
  property string companionScreen: Quickshell.screens[Quickshell.screens.length-1].name
  property string openScreen: companionScreen
  property string page: "chat"
  property real panelWidth: 350
  property bool pinned: true
  property bool connected: true
  property bool busy: false
  property bool terminalOpen: false
  property bool nativeSession: true
  property string agentName: "Oh My Pi"
  property var meta: ({agent:"omp",agentName:"Oh My Pi",available:true,settings:{cwd:"/home/blr/Work/side-chat",model:"",thinking:"default"}})
  property var current: ({id:"preview",title:"Theme",agent:"omp",options:{cwd:"/home/blr/Work/side-chat"},native:{},messages:[{role:"user",text:"Keep everything in my Omarchy theme.",status:"complete",time:Date.now()/1000},{role:"assistant",text:"The colors, font, and spacing follow your desktop.\n\nI’m here when you need me.",status:"complete",time:Date.now()/1000,model:""}]})
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
  property string notice: "Design preview · no microphone or agent"
  property string error: ""
  property var lastRequest: ({})
  signal focusComposer()
  signal companionControlsRequested()
  function request(c) {
   lastRequest=c
   if(c.action === "appearance") meta=Object.assign({},meta,{appearance:c.settings})
   if(c.action === "jarvis_settings") jarvis=Object.assign({},jarvis,c.settings)
   if(c.action === "jarvis_listen") jarvis=Object.assign({},jarvis,{listening:c.enabled})
  }
  function hover(screen,inside) { }
  function pin() { pinned=true }
  function close() { openScreen="" }
  function show(screen,persistent) { openScreen=screen;pinned=persistent }
  function setJarvis(v,reopen) { jarvis=Object.assign({},jarvis,{enabled:v});if(v) close();else if(reopen !== false) openConversation() }
  function openConversation() { openScreen=companionScreen;page="chat" }
  function openJarvisSettings() { openConversation();page="jarvis_settings" }
  function startNew() { current=Object.assign({},current,{messages:[]});draft="";page="chat" }
  function submit() { lastRequest={action:"send",text:draft};draft="" }
  function edit(i) { draft=messages[i].text;editIndex=i }
  function retry() { }
  function addAttachment(p) { }
  function removeAttachment(i) { }
 }
 ChatWindow { id: panel; screen: Quickshell.screens[Quickshell.screens.length-1]; chat: chat }
 CompanionWindow { id: buddy; screen: panel.screen; chat: chat }
 IpcHandler {
  target: "side-chat-design"
  function mode(stage: string): void { chat.jarvis=Object.assign({},chat.jarvis,{stage:stage,standby:stage === "standby",speaking:stage === "speaking",caption:stage === "speaking" ? "Ready when you are." : ""});chat.busy=stage === "thinking" || stage === "acting" }
  function page(name: string): void { chat.openConversation();chat.page=name }
  function controls(): void { chat.companionControlsRequested() }
  function show(): void { chat.jarvis=Object.assign({},chat.jarvis,{enabled:true});chat.openConversation() }
  function hide(): void { chat.close() }
  function empty(): void { chat.startNew() }
  function status(): string { return JSON.stringify({request:chat.lastRequest,voice:chat.jarvis,open:chat.openScreen,page:chat.page,buddy:{left:buddy.margins.left,bottom:buddy.margins.bottom,width:buddy.width,height:buddy.height},panel:{width:panel.width,height:panel.height}}) }
  function capture(): void {
   panel.contentItem.children.find(c=>c.objectName === "chat-drawer").grabToImage(r=>r.saveToFile("/tmp/side-chat-design-panel.png"))
   buddy.contentItem.children.find(c=>c.objectName === "jarvis-surface").grabToImage(r=>r.saveToFile("/tmp/side-chat-design-buddy.png"))
  }
 }
}
