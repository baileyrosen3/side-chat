const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {test} = require('node:test');
const path = require('node:path');

function fixture() {
  const source = readFileSync(path.join(__dirname, '../Main.qml'), 'utf8');
  const state = vm.createContext({panels:[], openScreen:'', pinned:false, error:'',
    workspaceModel:{mode:'search'}, saved:0, pings:0, focused:0,
    saveDraft(){state.saved++}, request(){state.pings++}, focusWorkspace(){state.focused++},
    Qt:{callLater(fn){fn()}}});
  state.root=state;
  for(const method of ['show','panelOpened','panelClosed','close']) {
    const start=source.indexOf('    function '+method+'(');
    const end=source.indexOf('\n    function ',start+1);
    vm.runInContext(source.slice(start,end),state);
  }
  function panel(screenName,available=true) {
    const p={screenName,available,opened:false,
      open(){if(!this.opened){this.opened=true;state.panelOpened(this)}},
      close(){if(this.opened){this.opened=false;state.panelClosed(this)}}};
    state.panels.push(p);return p;
  }
  return {state,panel};
}

test('keyboard routing chooses requested monitor and falls back from hidden bars',()=>{
  const {state,panel}=fixture();const left=panel('left'),right=panel('right');panel('hidden',false);
  state.show('right',true);assert(right.opened);assert.equal(state.openScreen,'right');
  state.show('hidden',true);assert(left.opened);assert(!right.opened);assert.equal(state.openScreen,'left');
  assert.equal(state.workspaceModel.mode,'search'); // Monitor handoff preserves the active search.
});
test('outside dismissal saves once and leaves all windows closed',()=>{
  const {state,panel}=fixture();const p=panel('left');p.open();p.close();
  assert.equal(state.saved,1);assert.equal(state.openScreen,'');assert.equal(state.workspaceModel.mode,'');
  p.open();state.close();assert(!p.opened);assert.equal(state.saved,2);
});
test('missing widget never reports an invisible open workspace',()=>{
  const {state}=fixture();assert.equal(state.show('missing',true),false);
  assert.equal(state.openScreen,'');assert.match(state.error,/bar/);
});
test('shared service handles both load orders and ignores stale destruction',()=>{
  const bridge=vm.createContext({});
  vm.runInContext(readFileSync(path.join(__dirname,'../ChatBridge.js'),'utf8').replace('.pragma library',''),bridge);
  const p={},q={},first={},second={};
  bridge.add(p);assert.equal(p.chat,null);
  bridge.setService(first);bridge.add(q);assert.equal(p.chat,first);assert.equal(q.chat,first);
  assert.equal(first.panels.length,2);
  bridge.setService(second);bridge.clearService(first);assert.equal(p.chat,second);
  bridge.remove(q);assert.equal(second.panels.length,1);
  bridge.clearService(second);assert.equal(p.chat,null);
});

test('disabled Peek shortcuts open settings without starting workers or moving the companion',()=>{
  const source=readFileSync(path.join(__dirname,'../Main.qml'),'utf8');
  const state=vm.createContext({peek:{runtimeEnabled:false},settingsOpened:0,
    openPeekSettings(){state.settingsOpened++},request(){throw Error('Started disabled Peek')}});
  state.root=state;
  for(const method of ['requirePeek','setPeek','openWorkspacePeek','toggleMicrophone','toggleChatListening']) {
    const start=source.indexOf('    function '+method+'(');
    const end=source.indexOf('\n    function ',start+1);
    vm.runInContext(source.slice(start,end),state);
  }
  state.setPeek(true);state.openWorkspacePeek();state.toggleMicrophone();state.toggleChatListening();
  assert.equal(state.settingsOpened,4);
  state.peek={runtimeEnabled:true,runtimeStopping:true};state.setPeek(true);
  assert.equal(state.settingsOpened,5);
});
