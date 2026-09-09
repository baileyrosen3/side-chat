/** Side Chat's observable computer tools. Uses the installed CLI's own permission policy. */
import { spawn } from 'node:child_process';

const properties: any = {
  op: {type:'string', enum:['windows','screenshot','focus','move','click','drag','scroll','type','key','browser','inspect_app','accessible_action','config_read','config_write','undo_list','undo_restore']},
  target:{type:'string'}, actionName:{type:'string'}, path:{type:'string'}, expected:{type:'string'}, id:{type:'string'}, frame:{type:'string'}, screen:{type:'string'}, window:{type:'string'},
  x:{type:'number'}, y:{type:'number'}, toX:{type:'number'}, toY:{type:'number'},
  button:{type:'string',enum:['left','right','middle']}, count:{type:'integer'}, amount:{type:'integer'},
  horizontal:{type:'boolean'}, text:{type:'string'}, key:{type:'string'}, args:{type:'array',items:{type:'string'}}
};
const description = `Control the user's computer through Peek with visible, interruptible actions. Use windows to list window addresses and monitors; focus a window, then screenshot. Screenshot returns an image and frame ID. All mouse/keyboard input requires that fresh frame; x/y and toX/toY are pixels in that screenshot, never guessed global coordinates. Re-observe after actions. key accepts Ctrl+l, Return, etc.; type accepts Unicode. scroll amount positive means up. browser args is an array of agent-browser CLI arguments (open URL, snapshot -i, click @e1, fill @e2 text, press Enter, etc.) whose routing follows the selected mode. DESKTOP: only open URL, launching the visible default Omarchy browser with its normal profile; use screenshot and native input afterward. BROWSER: isolated headless Chromium with DOM commands. Never use a built-in hidden browser in Desktop mode. Prefer inspect_app for accessible app controls, then accessible_action with returned target and actionName (or text for an editable target). Targets expire; re-inspect after acting. If no accessibility tree is exposed, use screenshots and native input. For small user config edits use config_read(path) then config_write(path,text,expected=sha256 returned by read). This verifies and records an undo point; undo_list and undo_restore(id) restore only when the file has not changed since. Use browser DOM only in Browser mode; Desktop mode uses native input for websites and apps. Tool availability does not imply an action succeeded: inspect each result. Desktop control must be enabled in Peek.`;

export default function(pi: any) {
  // Both OMP and Pi expose this hook. Keep computer actions on the mode-aware broker,
  // even when a resumed session still remembers its built-in headless browser.
  pi.on('tool_call', async (event: any) => {
    const path = String(event.input?.path || '');
    if (['browser','computer','playwright'].includes(event.toolName) ||
        (event.toolName === 'write' && /^xd:\/\/(browser|computer|playwright)(\/|$)/.test(path)))
      return {block:true,reason:'Peek owns browser/desktop control in this session. Use jarvis_computer; its browser open command follows the current Desktop or Browser mode. Do not substitute a hidden browser.'};
  });
  let parameters: any = {type:'object',properties,required:['op'],additionalProperties:false};
  if (pi.zod) {
    const z=pi.zod;
    parameters=z.object({op:z.enum(properties.op.enum),target:z.string().optional(),actionName:z.string().optional(),path:z.string().optional(),expected:z.string().optional(),id:z.string().optional(),frame:z.string().optional(),screen:z.string().optional(),window:z.string().optional(),x:z.number().optional(),y:z.number().optional(),toX:z.number().optional(),toY:z.number().optional(),button:z.enum(['left','right','middle']).optional(),count:z.number().optional(),amount:z.number().optional(),horizontal:z.boolean().optional(),text:z.string().optional(),key:z.string().optional(),args:z.array(z.string()).optional()});
  }
  pi.registerTool({name:'jarvis_computer',label:'Computer',description,parameters,
    async execute(id: string, params: any, ...rest: any[]) {
      const signal=rest.find((value: any)=>value && typeof value.addEventListener==='function' && typeof value.aborted==='boolean');
      const command=process.env.SIDE_CHAT_CONTROL_CLIENT;
      const socket=process.env.SIDE_CHAT_CONTROL_SOCKET;
      if (!command || !socket) throw new Error('Peek desktop controller is not connected.');
      const result=await new Promise<any>((resolve,reject)=>{
        const child=spawn('python3',['-B',command,'--socket',socket,JSON.stringify({...params,callId:id})],{stdio:['ignore','pipe','pipe']});
        let stdout='',stderr='';
        child.stdout.on('data',(b:Buffer)=>{stdout+=b.toString();if(stdout.length>8000000)child.kill();});
        child.stderr.on('data',(b:Buffer)=>stderr=(stderr+b.toString()).slice(-2000));
        const stop=()=>child.kill();
        signal?.addEventListener('abort',stop,{once:true});
        child.on('error',reject);
        child.on('close',(code:number)=>{
          signal?.removeEventListener('abort',stop);
          if(signal?.aborted)return reject(new Error('Computer action cancelled.'));
          try {const data=JSON.parse(stdout);if(data.error)reject(new Error(data.error));else resolve(data);}
          catch(e){reject(new Error(stderr||`Computer controller exited (${code})`));}
        });
      });
      return result.content ? result : {content:[{type:'text',text:JSON.stringify(result)}],details:result};
    }
  });
}
