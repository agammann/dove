import {chromium} from 'playwright';
import {mkdir,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
await mkdir('outputs',{recursive:true});
const browser=await chromium.launch({...(process.env.DOVE_TEST_EXECUTABLE?{executablePath:process.env.DOVE_TEST_EXECUTABLE}:{channel:process.env.DOVE_TEST_CHANNEL||'chrome'}),headless:process.env.DOVE_TEST_HEADLESS==='1'});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
const report={date:new Date().toISOString(),browser:browser.version(),models:[],errors:[],transmissions:[],checks:[]};
const source='Fictional agreement. Example Customer accepted the finished logo and style guide on September 30, 2026. The agreed final billing amount is USD 2400.00 including applicable taxes. Purchase order PO-1042 must accompany the invoice. The customer has supplied purchase order PO-1042.';
page.on('pageerror',e=>report.errors.push(e.message));
page.context().on('request',r=>{if(r.method()!=='GET')report.transmissions.push({url:r.url(),method:r.method(),hasSource:r.postData()?.includes('Example Customer')||false});});
let timer,lastStatus='';
try{
 await page.goto('http://127.0.0.1:5174/workspace');
 report.gpu=await page.evaluate(async()=>{const adapter=await navigator.gpu?.requestAdapter();return {available:!!adapter,features:adapter?[...adapter.features]:[],info:adapter?{vendor:adapter.info?.vendor,architecture:adapter.info?.architecture,device:adapter.info?.device,description:adapter.info?.description}:null};});
 assert(report.gpu.available,'A real WebGPU adapter is required; this test has no mock fallback');
 await page.getByRole('button',{name:'New work item',exact:true}).click();
 for(const [label,value] of [['Work title','Fictional model verification'],['Customer business','Example Customer'],['Billing contact name','Example Contact'],['Billing contact email','contact@example.invalid'],['What was completed?','Completed a fictional logo and style guide.']])await page.getByLabel(label,{exact:true}).fill(value);
 await page.getByRole('checkbox').check();
 await page.getByRole('button',{name:'Create work item',exact:true}).click();
 await page.getByLabel('PDF or TXT, up to 4 MB',{exact:true}).setInputFiles({name:'Agreement.txt',mimeType:'text/plain',buffer:Buffer.from(source)});
 await page.getByRole('button',{name:'Add document',exact:true}).click();
 await page.getByText('Document saved. Review any earlier decisions against the new evidence.',{exact:true}).waitFor();
 report.checks.push('Actual create and TXT upload forms persist the fictional source');
 const panel=page.getByRole('region',{name:'Browser model',exact:true});
 timer=setInterval(async()=>{try{const text=await panel.getByRole('status').innerText({timeout:1000});if(text!==lastStatus){lastStatus=text;console.log('MODEL',text);}}catch{}},5000);
 // Exercise cancellation before downloading the complete model.
 await panel.getByRole('combobox').selectOption('Qwen3-1.7B-q4f16_1-MLC');
 await panel.getByRole('button',{name:'Download model',exact:true}).click();
 await panel.getByRole('button',{name:'Stop download',exact:true}).click();
 await panel.getByText('Download stopped. You can try again.',{exact:true}).waitFor({timeout:30000});
 report.checks.push('Real download cancellation returns to a retryable idle state');
 for(const id of ['Qwen3-1.7B-q4f16_1-MLC','Qwen3-4B-q4f16_1-MLC']){
  await page.getByRole('tab',{name:/Documents/}).click();
  await panel.getByRole('combobox').selectOption(id);
  const result={id,started:new Date().toISOString()};report.models.push(result);
  await panel.getByRole('button',{name:'Download model',exact:true}).click();
  await page.waitForFunction(()=>{const p=document.querySelector('section[aria-label="Browser model"]');return p?.textContent.includes('Model ready.')||p?.querySelector('[role="alert"]')},null,{timeout:920000});
  const errors=await panel.getByRole('alert').allTextContents();
  if(errors.length){result.error=errors.join(' ');throw Error(id+': '+result.error);}
  result.loaded=new Date().toISOString();console.log('LOADED',id);
  await page.getByRole('button',{name:'Analyze documents',exact:true}).click();
  await page.waitForFunction(()=>document.body.textContent.includes('Analysis saved. Review every proposed requirement and check for omissions.')||document.querySelector('main [role="alert"]'),null,{timeout:340000});
  const alerts=await page.getByRole('alert').allTextContents();
  assert.equal(alerts.length,0,alerts.join(' '));
  result.analysis=await page.getByRole('tabpanel',{name:'Review',exact:true}).innerText();
  result.completed=new Date().toISOString();
  const quotes=await page.locator('.d-requirement blockquote').allTextContents();
  assert(quotes.length>0,'The real model should propose source-linked requirements');
  for(const quote of await page.locator('.d-requirement blockquote').evaluateAll(es=>es.map(e=>e.firstChild.textContent)))assert(source.includes(quote),'Every model quote matches the uploaded document');
  assert.equal(await page.locator('.d-requirement .d-tag').getByText(/^(satisfied|waived)$/).count(),0);
  assert(!/\bconflict\b/.test(result.analysis),'Consistent fictional sources should not conflict');
  await page.screenshot({path:'outputs/real-model-'+id+'.png',fullPage:true});
  console.log('ANALYZED',id,result.analysis);
  await page.getByRole('tab',{name:/Documents/}).click();
  await page.getByRole('button',{name:'Analyze documents',exact:true}).click();
  await page.getByRole('button',{name:'Stop analysis',exact:true}).click();
  await page.getByText('Analysis stopped. Your prior checklist is unchanged.',{exact:true}).waitFor({timeout:30000});
  await page.getByRole('tab',{name:/Review/}).click();
  assert.equal(await page.getByRole('tabpanel',{name:'Review',exact:true}).innerText(),result.analysis);
  result.cancelPreservesChecklist=true;
 }
 assert.equal(report.transmissions.filter(r=>r.hasSource).length,0,'No prompt/source posted to an external service');
 report.checks.push('Both offered model downloads and inference results use real WebGPU with no mock or paid fallback');
}catch(e){report.failure=e.stack;console.error('FAILED',e.stack);process.exitCode=1;await page.screenshot({path:'outputs/real-model-failure.png',fullPage:true}).catch(()=>{});}
finally{clearInterval(timer);await writeFile('outputs/real-model-verification.json',JSON.stringify(report,null,2));await browser.close();}
