import { generate } from './browser-model.mjs';
import { analysisInstructions, analysisSchema } from './analysis-contract.mjs';
const normalized=s=>s.replace(/\s+/g,' ').trim();
export function verifyProposals(work, proposals){
 if(!Array.isArray(proposals)||proposals.length>20)throw Error('The checklist is too large. Review requirements manually.');
 for(const p of proposals){
  if(!['missing','received','conflict'].includes(p.status)||!Array.isArray(p.evidence)||!p.evidence.length)throw Error('Each proposed requirement needs source evidence and human review.');
  for(const e of p.evidence){const doc=work.documents.find(d=>d.id===e.documentId);if(!doc||!Number.isInteger(e.page)||e.page<1||e.page>doc.pages.length||normalized(e.quote).length<3||!normalized(doc.pages[e.page-1]).includes(normalized(e.quote)))throw Error('A proposed quote did not match its source. Your existing checklist is unchanged.');}
 }
 return proposals;
}
function chunks(work){const out=[];for(const d of work.documents)for(let page=0;page<d.pages.length;page++){const text=d.pages[page];for(let offset=0;offset<text.length;offset+=6000)out.push({documentId:d.id,name:d.name,page:page+1,text:text.slice(offset,offset+6000)});}return out;}
export async function analyzeDocumentsBrowser(work,{signal,onProgress=()=>{},runGeneration=generate,location='on your device'}={}){
 const sections=[];for(const section of chunks(work)){let batch=sections.at(-1);if(!batch||batch.reduce((sum,s)=>sum+s.text.length,0)+section.text.length>8000){batch=[];sections.push(batch);}batch.push(section);}const proposals=[];
 if(!sections.length)throw Error('Upload a document with readable text first.');
 for(let i=0;i<sections.length;i++){
  signal?.throwIfAborted();const source=sections[i];onProgress(`Reading source section ${i+1} of ${sections.length} ${location}…`);
  const schema=analysisSchema(source);
  if(!schema)continue;
  const output=await runGeneration([{role:'system',content:analysisInstructions+' /no_think'},{role:'user',content:JSON.stringify({source,earlierProposals:proposals.map(p=>({title:p.title,category:p.category,reason:p.reason}))})}],{schema,maxTokens:2400,signal});
  signal?.throwIfAborted();
  verifyProposals(work,output.value.requirements);
  for(const p of output.value.requirements){const existing=proposals.find(q=>q.category===p.category&&normalized(q.title).toLowerCase()===normalized(p.title).toLowerCase());if(existing){for(const e of p.evidence)if(!existing.evidence.some(x=>x.documentId===e.documentId&&x.page===e.page&&x.quote===e.quote))existing.evidence.push(e);if(existing.evidence.length>10)throw Error('Too many source references for one requirement. Review this checklist manually.');if(p.status==='conflict'){existing.status='conflict';existing.reason=p.reason;}else if(existing.status==='missing'&&p.status==='received'){existing.status='received';existing.reason=p.reason;}}else proposals.push(p);}
  if(proposals.length>20)throw Error('More than 20 requirements were found. Add and review requirements manually; the prior checklist is unchanged.');
 }
 return verifyProposals(work,proposals);
}
