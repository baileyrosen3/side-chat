const {readFileSync}=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const logic=vm.createContext({});
vm.runInContext(readFileSync(require('node:path').join(__dirname,'../Thoughts.js'),'utf8').replace('.pragma library',''),logic);
const notes=[
 {id:'a',body:'A walking idea',created:'2026-09-11',kind:'note',trashed:false},
 {id:'b',body:'Buy groceries',created:'2026-09-09',kind:'todo',done:false,trashed:false},
 {id:'c',body:'Read a book',created:'2026-09-08',kind:'todo',done:true,trashed:false},
 {id:'d',body:'Deleted',created:'2026-09-07',trashed:true},
];
const ids=rows=>Array.from(rows,n=>n.id);
assert.deepEqual(ids(logic.rows(notes,{},'note','',false)),['a']);
assert.deepEqual(ids(logic.rows(notes,{},'todo','',false)),['b']);
assert.deepEqual(ids(logic.rows(notes,{},'todo','',true)),['c']);
assert.deepEqual(ids(logic.rows(notes,{},'note','walking idea',false)),['a']);
assert.deepEqual(ids(logic.rows(notes,{},'note','missing',false)),[]);
const drafts={'draft-a':{key:'draft-a',id:'a',body:'Updated walking idea',kind:'note',updated:1}};
assert.equal(logic.rows(notes,drafts,'note','',false)[0].isDraft,true);
assert.equal(logic.rows(notes,drafts,'note','',false).length,1);
console.log('Notes, to-dos, completion, search, and recovery passed.');
