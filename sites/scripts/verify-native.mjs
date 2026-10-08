import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import {chromium} from 'playwright';

const origin=process.env.DOVE_TEST_URL||'http://127.0.0.1:5174';
assert(['http://127.0.0.1:5174','http://localhost:5173'].includes(origin),'Use a local Dove preview.');
await mkdir('outputs',{recursive:true});
const browser=await chromium.launch({...(process.env.DOVE_TEST_EXECUTABLE?{executablePath:process.env.DOVE_TEST_EXECUTABLE}:{channel:process.env.DOVE_TEST_CHANNEL||'chrome'}),headless:true,args:['--enable-features=WebMCPTesting']});
const major=Number(browser.version().split('.')[0]);
assert([154,155].includes(major),'Verify the executeTool input contract before testing another Chrome major.');
const page=await browser.newPage({viewport:{width:1440,height:1000}});
const report={browser:browser.version(),origin,scope:'Native landing-page illustration only; no document processing, model calls or approvals.',checks:[],calls:[],errors:[],consoleErrors:[],expectedInvalidConsole:[],posts:[]};
let invalid=false;
page.on('pageerror',e=>report.errors.push(e.message));
page.on('console',m=>{if(m.type()==='error'){if(invalid&&m.text().includes('WebMCP tool execution failed: Uncaught Error: Choose step 1, 2 or 3.'))report.expectedInvalidConsole.push(m.text());else report.consoleErrors.push(m.text())}});
page.on('request',request=>{if(request.method()!=='GET')report.posts.push({url:request.url(),method:request.method()})});
const check=(name,value)=>{report.checks.push({name,passed:!!value});assert(value,name)};
try{
 await page.goto(origin+'/');await page.getByRole('tab',{name:/Gather/}).waitFor();
 const capability=await page.evaluate(()=>({secure:isSecureContext,native:['registerTool','getTools','executeTool'].every(name=>typeof document.modelContext?.[name]==='function'&&Function.prototype.toString.call(document.modelContext[name]).includes('[native code]'))}));
 check('actual native ModelContext methods',capability.secure&&capability.native);
 await page.waitForFunction(async()=>typeof document.modelContext?.getTools==='function'&&(await document.modelContext.getTools()).length===1);
 const tools=await page.evaluate(async()=>await document.modelContext.getTools());
 check('single declared native tool',tools.length===1&&tools[0].name==='show_dove_workflow_step');
 const schema=typeof tools[0].inputSchema==='string'?JSON.parse(tools[0].inputSchema):tools[0].inputSchema;
 assert.deepEqual(schema,{type:'object',properties:{step:{type:'integer',minimum:1,maximum:3}},required:['step'],additionalProperties:false});
 for(const [step,label] of [[1,'Gather'],[2,'Resolve'],[3,'Approve']]){
  const result=await page.evaluate(async({step,major})=>{const tool=(await document.modelContext.getTools()).find(tool=>tool.name==='show_dove_workflow_step');return document.modelContext.executeTool(tool,major===154?JSON.stringify({step}):{step})},{step,major});
  report.calls.push({step,result});
  check('native step '+step+' renders '+label,await page.getByRole('tab',{name:new RegExp(label)}).getAttribute('aria-selected')==='true');
 }
 invalid=true;
 const rejected=await page.evaluate(async major=>{const tool=(await document.modelContext.getTools()).find(tool=>tool.name==='show_dove_workflow_step');try{await document.modelContext.executeTool(tool,major===154?'{"step":4}':{step:4});return false}catch{return true}},major);
 await page.waitForTimeout(250);invalid=false;
 check('invalid native input rejected',rejected);check('invalid input leaves selected stage unchanged',await page.getByRole('tab',{name:/Approve/}).getAttribute('aria-selected')==='true');
 await page.reload();await page.waitForFunction(async()=>(await document.modelContext.getTools()).length===1);check('reload registers one tool without duplicates',(await page.evaluate(async()=>await document.modelContext.getTools())).length===1);
 await page.goto(origin+'/workspace/');await page.getByRole('heading',{name:'Good work. Ready to wrap up.'}).waitFor();check('workspace exposes no processing or approval tool',(await page.evaluate(async()=>await document.modelContext.getTools())).length===0);
 check('native illustration has no POST requests',report.posts.length===0);check('no page or unexpected console errors',report.errors.length===0&&report.consoleErrors.length===0);report.outcome='passed';
}catch(error){report.outcome='failed';report.failure=error.stack;process.exitCode=1}
finally{await writeFile('outputs/dove-native-verification.json',JSON.stringify(report,null,2));await browser.close();console.log(JSON.stringify({outcome:report.outcome,checks:report.checks.length}))}
