const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.resolve(__dirname,'../../Main.qml'),'utf8');
const methods=['startNew','edit','submit'];
let declarations='';
for(const method of methods){
 const start=source.indexOf('    function '+method+'(');
 const end=source.indexOf('\n    function ',start+1);
 declarations+=source.slice(start,end)+'\n';
}
const requests=[];
const context=vm.createContext({busy:false,terminalOpen:false,draft:'An unsaved next question',draftSource:{},attachments:[],editIndex:-1,page:'chat',error:'',peek:{enabled:false},messages:[{role:'user',text:'Original prompt'}],draftSave:{stop(){}},noticeClear:{restart(){}},focusComposer(){},pin(){},request(c){requests.push(c)}});
vm.runInContext(declarations,context);
context.startNew();
console.log(JSON.stringify({case:'new_chat_before_debounce',draft:context.draft,requests}));
context.draft='Keep this separate draft';requests.length=0;context.edit(0);
console.log(JSON.stringify({case:'edit_replaces_unsent_draft',draft:context.draft,requests}));
