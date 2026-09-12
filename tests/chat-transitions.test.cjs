const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {test} = require('node:test');
const source = readFileSync(require('node:path').join(__dirname, '../Main.qml'), 'utf8');
function fixture() {
  const commands = [];
  const state = vm.createContext({
    connected:true, busy:false, terminalOpen:false, current:{id:'one'},
    draft:'An unfinished question', draftSource:{kind:'note',id:'note-one'}, attachments:['/tmp/draft.txt'],
    editIndex:-1, editBackup:null, restoring:false, page:'notes', pageHistory:[], returnPage:'chat',
    error:'', notice:'', excludeScreen:false, messageTarget:null, peek:{enabled:false},
    messages:[{role:'user',text:'Original prompt',attachments:[{path:'/tmp/original.txt'}]}],
    draftSave:{stop(){}}, noticeClear:{restart(){}}, focusComposer(){}, pin(){},
    backend:{write(line){commands.push(JSON.parse(line));}},
  });
  for (const method of ['request','visit','back','saveDraft','startNew','selectChat','submit','edit','cancelEdit']) {
    const start = source.indexOf('    function '+method+'(');
    const end = source.indexOf('\n    function ',start+1);
    assert(start >= 0 && end > start);
    vm.runInContext(source.slice(start,end),state);
  }
  const receiveStart=source.indexOf('    function receive(');
  vm.runInContext(source.slice(receiveStart,source.indexOf('\n    onDraftChanged',receiveStart)),state);
  return {state,commands};
}
test('New saves the outgoing draft and attachment references before switching',()=>{
  const {state,commands}=fixture(); state.startNew();
  assert.deepEqual(commands.map(c=>c.action),['draft','new']);
  assert.equal(commands[0].text,'An unfinished question');
  assert.deepEqual(commands[0].attachments,['/tmp/draft.txt']);
  assert.equal(state.draft,'An unfinished question'); // Clear only when the new conversation is acknowledged.
});
test('Cancel edit restores the entire unsent draft',()=>{
  const {state,commands}=fixture(); state.edit(0);
  assert.equal(state.draft,'Original prompt');
  assert.deepEqual(Array.from(state.attachments),['/tmp/original.txt']);
  state.draft='Changed prompt'; state.cancelEdit();
  assert.equal(state.draft,'An unfinished question');
  assert.deepEqual(Array.from(state.attachments),['/tmp/draft.txt']);
  assert.equal(state.draftSource.id,'note-one');
  assert.equal(state.editIndex,-1);
  assert.equal(commands.at(-1).text,'An unfinished question');
});
test('Sending an edit carries the previous draft through acknowledgment',()=>{
  const {state,commands}=fixture(); state.edit(0); state.submit();
  const command=commands.at(-1);
  assert.equal(command.action,'send');
  assert.equal(command.nextDraft.text,'An unfinished question');
  assert.equal(command.replaceAttachments,true);
});
test('Nested preferences return to the originating Notes tab',()=>{
  const {state}=fixture(); state.visit('settings'); state.visit('peek_settings');
  state.back(); assert.equal(state.page,'settings');
  state.back(); assert.equal(state.page,'notes');
});
test('Disconnected actions retain drafts and attachments',()=>{
  const {state,commands}=fixture(); state.connected=false;state.startNew();
  state.busy=true;state.peek.enabled=true;state.submit();
  assert.equal(state.draft,'An unfinished question');
  assert.equal(state.attachments.length,1);
  assert.equal(commands.length,0);
});
test('Redirect keeps the text until the backend accepts it',()=>{
  const {state,commands}=fixture(); state.busy=true;state.peek.enabled=true;state.submit();
  assert.equal(commands.at(-1).action,'peek_redirect');
  assert.equal(state.draft,'An unfinished question');
});
test('Reopening a conversation recovers the edit and its original draft separately',()=>{
  const {state}=fixture();state.current=null;
  const current={id:'recovered',draft:'Next question',draftSource:{},draftAttachments:['/tmp/next.txt'],
    draftEdit:{index:0,text:'Unfinished edit',source:{},attachments:['/tmp/edit.txt']}};
  state.receive({type:'state',current,meta:{},chats:[],busy:false});
  assert.equal(state.draft,'Unfinished edit');
  assert.equal(state.editBackup.text,'Next question');
  assert.equal(state.editIndex,0);
  state.cancelEdit();
  assert.equal(state.draft,'Next question');
});
test('Repeated edit actions do not overwrite an unfinished edit',()=>{
  const {state}=fixture();state.edit(0);state.draft='Unfinished edit';state.edit(0);state.edit(1);
  assert.equal(state.draft,'Unfinished edit');assert.equal(state.editIndex,0);
});
