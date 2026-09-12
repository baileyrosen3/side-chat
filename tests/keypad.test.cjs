const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname, '../Keypad.js'), 'utf8').replace('.pragma library', ''), context);
const calls = [];
const spy = name => (...args) => calls.push([name, ...args]);
const chat = {
  peek: { enabled: false }, navigate: spy('navigate'), toggle: spy('toggle'), close: spy('close'),
  openHistory: spy('history'), openPreferences: spy('settings'), setPeek: spy('peek'),
  toggleMicrophone: spy('microphone'), toggleChatListening: spy('listen-chat'), openWorkspacePeek: spy('controls'), stopWorkspace: spy('stop'),
  thoughts: { newNote: spy('new-note'), startCapture: spy('record'), stopCapture: spy('record-stop'), toggleCapture: spy('toggle-record') },
  workspace: { capture: spy('selection'), toggleSearch: spy('search') },
  submit: () => { throw Error('The keypad router submitted the typed chat draft'); },
};
for (const section of ['chat', 'notes', 'todos']) {
  context.run(chat, section); assert.deepEqual(calls.pop(), ['navigate', section]);
}
context.run(chat, 'note'); assert.deepEqual(calls.pop(), ['new-note']);
context.run(chat, 'selection'); assert.deepEqual(calls.pop(), ['selection', false]);
context.run(chat, 'record'); assert.deepEqual(calls.pop(), ['record', 'note']);
context.run(chat, 'record-stop'); assert.deepEqual(calls.pop(), ['record-stop']);
context.run(chat, 'listen-chat'); assert.deepEqual(calls.pop(), ['listen-chat']);
context.run(chat, 'listen-notes'); assert.deepEqual(calls.pop(), ['toggle-record', 'note']);
context.run(chat, 'listen-todos'); assert.deepEqual(calls.pop(), ['toggle-record', 'todo']);
context.run(chat, 'peek'); assert.deepEqual(calls.pop(), ['peek', true, false]);
chat.peek.enabled = true;
context.run(chat, 'peek'); assert.deepEqual(calls.pop(), ['peek', false, false]);
for (const [action, expected] of Object.entries({ workspace:'toggle', history:'history', settings:'settings', search:'search', microphone:'microphone', controls:'controls', stop:'stop', hide:'close' })) {
  context.run(chat, action); assert.deepEqual(calls.pop(), [expected]);
}
context.run(chat, 'unknown'); assert.equal(calls.length, 0);
console.log('Keypad destinations, voice toggles, companion controls, and typed-draft isolation passed.');
