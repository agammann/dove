import { z } from "zod";
import { uid, now, digest, event, invalidate, validEvidence, requirementInput, validateAnalysis, need, Problem } from "./dove-core";
import { extract, cents, money, invoice, archive } from "./dove-files";
import { readState, readFile, commit } from "./dove-storage";
import type { StoredFile } from "./dove-storage";
import type { Work, DocumentRecord, Packet } from "./dove-types";
export const createInput=z.object({title:z.string().trim().min(1).max(200),customer:z.string().trim().min(1).max(200),contactName:z.string().trim().min(1).max(200),email:z.string().email().max(254),authorized:z.boolean(),currency:z.enum(["USD","EUR","GBP","CAD","AUD"]),description:z.string().trim().min(1).max(2000)}).strict();
const packageInput=z.object({total:z.string(),issue:z.string().regex(/^\d{4}-\d{2}-\d{2}$/),due:z.string().regex(/^\d{4}-\d{2}-\d{2}$/),summary:z.string().trim().min(5).max(2000),evidence:requirementInput.shape.evidence.min(1),documents:z.array(z.string().uuid()).max(10),existingInvoice:z.string().uuid().optional(),confirmed:z.literal(true)}).strict();
async function handler(path: string, method: string, input?: unknown) {
 const p=path.split("/").filter(Boolean), state=await readState(), org=state.workspace;
 const user={email:"Local operator"}, additions:StoredFile[]=[];
 async function storeFile(_org:string,wid:string,id:string,name:string,mime:string,bytes:Uint8Array){additions.push({id,workId:wid,name,mime,bytes})}
 async function save(_org:string,w:Work,_v:number){void _v;const i=state.work.findIndex(x=>x.id===w.id);need(i>=0,"Work item not found.");state.work[i]=w;await commit(state,additions)}
 async function removeFile(_org:string,id:string){const i=additions.findIndex(f=>f.id===id);if(i>=0)additions.splice(i,1)}
 const response=(value:unknown,_status=200)=>{void _status;return value};
 const bucket=()=>({get:async(key:string)=>{const f=await readFile(key.split("/").at(-1)!);return {arrayBuffer:async()=>f.bytes.slice().buffer}}});
 if(p[0]==="me"&&method==="GET")return {workspace:org,user:{name:"Local operator",email:""},integrations:{ai:true,email:false,inbound:false}};
 if(p[0]==="settings"&&method==="PUT"){
  const d=z.object({name:z.string().trim().min(1).max(200),billing:z.string().trim().max(1500),paused:z.boolean()}).strict().parse(input);
  state.workspace={...org,...d,paused:d.paused?1:0};await commit(state);return {ok:true};
 }
 need(p[0]==="work","Unknown local operation.");
 if(p.length===1&&method==="GET")return [...state.work].reverse().map(({id,title,customer,status})=>({id,title,customer,status}));
 if(p.length===1&&method==="POST"){
  const d=createInput.parse(input);need(d.authorized,"Verify the billing contact before continuing.");need(state.work.length<100,"Workspace work-item limit reached.");
  const w:Work={...d,id:uid(),status:"Add documents",revision:0,documents:[],requirements:[],packages:[],requests:[],activity:[],created:now(),calls:0,paused:false};
  event(w,user.email,"Work item created.");state.work.push(w);await commit(state);return w;
 }
 const w=state.work.find(x=>x.id===p[1]),v=state.version;need(w,"Work item not found. Reload the workspace.",404);
 if(p.length===2&&method==="GET")return w;
 if(p.length===2&&method==="DELETE"){
  state.work=state.work.filter(x=>x.id!==w.id);await commit(state,[],[...w.documents.map(d=>d.id),...w.packages.flatMap(p=>[p.id,...(p.pdfId?[p.pdfId]:[])])]);return {ok:true};
 }
if(p[2]==="pause"&&method==="POST"){const d=z.object({paused:z.boolean()}).strict().parse(input);w.paused=d.paused;event(w,user.email,d.paused?"Automation paused.":"Automation resumed.");await save(org.id,w,v);return response(w)}
if(p[2]==="document"&&method==="POST"){
 need(w.documents.length<10,"A work item may contain at most 10 documents.",409);need(input instanceof FormData,"Choose a document.");const form=input;const f=form.get("file");need(f instanceof File,"Choose a file.");need(f.size>0&&f.size<=4*1024*1024,"Use a PDF or TXT file up to 4 MB.",413);const name=f.name.replace(/[\\/\x00-\x1f]/g,"_").slice(0,150);const bytes=new Uint8Array(await f.arrayBuffer());const pages=await extract(bytes,name);need(w.documents.flatMap(x=>x.pages).join("").length+pages.join("").length<=200000,"This work item contains too much text.",413);
 const id=uid(),mime=/\.pdf$/i.test(name)?"application/pdf":"text/plain";await storeFile(org.id,w.id,id,name,mime,bytes);const d:DocumentRecord={id,name,mime,size:bytes.length,pages,approved:false};w.documents.push(d);invalidate(w);event(w,user.email,"Document uploaded: "+name+". Checklist and package approvals require review.");for(const r of w.requirements)r.status="received";try{await save(org.id,w,v)}catch(e){await removeFile(org.id,id).catch(()=>{});throw e}return response(w)
}
if(p[2]==="analyze"&&method==="POST"){
 need(!w.paused&&!org.paused,"Resume automation in Settings and on this work item first.",409);
 const data=z.object({revision:z.number().int(),requirements:z.unknown()}).strict().parse(input);
 need(data.revision===w.revision,"This work changed during analysis. Refresh and analyze the current documents.",409);
 const proposed=validateAnalysis(w,{requirements:data.requirements});
 w.requirements=proposed;invalidate(w);event(w,user.email,"Saved "+proposed.length+" source-linked browser proposals. Human review is required.");await save(org.id,w,v);return response(w);
}

if(p[2]==="requirement"&&method==="PUT"){
 const data=z.object({id:z.string().uuid().optional(),requirement:requirementInput}).strict().parse(input);const r=data.requirement;need(r.status==="waived"||r.evidence.length>0,"Attach source evidence or explicitly waive this requirement.");need(r.evidence.every(e=>validEvidence(w,e)),"Source quote must match the chosen document and page.");need(w.requirements.length<30||data.id,"Requirement limit reached.");const pos=w.requirements.findIndex(x=>x.id===data.id);need(!data.id||pos>=0,"Requirement not found.",404);const item={...r,id:data.id||uid(),reviewedBy:user.email};if(pos>=0)w.requirements[pos]=item;else w.requirements.push(item);invalidate(w);w.status=w.requirements.every(x=>["satisfied","waived"].includes(x.status))?"Ready to package":"Review required";event(w,user.email,r.title+": "+r.status+". "+r.reason);await save(org.id,w,v);return response(w)
}
if(p[2]==="request"&&method==="POST"){
 need(w.requests.length<10,"Request allowance reached.");
 const d=z.object({requirements:z.array(z.string().uuid()).min(1).max(20),body:z.string().trim().min(10).max(3000)}).strict().parse(input);
 need(d.requirements.every(id=>w.requirements.some(r=>r.id===id&&r.status==="missing")),"Select missing requirements.");
 w.requests.push({id:uid(),requirements:d.requirements,body:d.body,recipient:w.email,status:"draft_not_sent",created:now()});
 event(w,user.email,"Missing-document request saved as a draft. No email was sent.");await save(org.id,w,v);return w;
}
if(p[2]==="reply"&&method==="POST"){
 const d=z.object({requestId:z.string().uuid(),text:z.string().trim().min(10).max(20000),sender:z.string().email(),verified:z.literal(true)}).strict().parse(input);const req=w.requests.find(x=>x.id===d.requestId);need(req,"Request not found.",404);need(d.sender.toLowerCase()===req.recipient.toLowerCase(),"The sender must match the authorized contact.");need(w.documents.length<10,"Document limit reached.");const bytes=new TextEncoder().encode(d.text),id=uid();await storeFile(org.id,w.id,id,"Recorded reply.txt","text/plain",bytes);w.documents.push({id,name:("Recorded reply from "+d.sender).slice(0,150),mime:"text/plain",size:bytes.length,pages:[d.text],approved:false});req.status="reply_recorded";invalidate(w);for(const r of w.requirements)r.status="received";event(w,user.email,"Operator recorded a reply and verified its source. Review its evidence; it is not an automatically verified email.");try{await save(org.id,w,v)}catch(e){await removeFile(org.id,id).catch(()=>{});throw e}return response(w)
}
if(p[2]==="package"&&method==="POST"){
 need(w.requirements.length>0&&w.requirements.every(r=>["satisfied","waived"].includes(r.status)),"Resolve and review every requirement before packaging.",409);need(w.authorized,"Authorize the billing contact first.",409);need(w.packages.length<10,"Package version limit reached.",409);need(org.billing,"Save your business billing details in Settings first.",409);
 const d=packageInput.parse(input);const total=cents(d.total);need(total>0,"The invoice total must be positive.");need(d.due>=d.issue&&Number.isFinite(Date.parse(d.issue))&&Number.isFinite(Date.parse(d.due))&&new Date(d.issue).toISOString().slice(0,10)===d.issue&&new Date(d.due).toISOString().slice(0,10)===d.due,"Enter valid issue and due dates.");need(d.evidence.every(e=>validEvidence(w,e)),"The amount evidence must match its source.");const quoted=d.evidence.map(e=>e.quote).join(" ");const values=[...quoted.matchAll(/\d[\d,]*(?:\.\d{1,2})?/g)].map(x=>x[0].replace(/,/g,""));need(values.some(x=>{try{return cents(x)===total}catch{return false}}),"The total must appear in the selected source evidence.");need(new Set(d.documents).size===d.documents.length&&d.documents.every(id=>w.documents.some(x=>x.id===id)),"Choose existing, distinct supporting documents.");const existing=d.existingInvoice?w.documents.find(x=>x.id===d.existingInvoice&&x.mime==="application/pdf"):undefined;need(!d.existingInvoice||existing,"Choose a PDF for the existing invoice.");
 const id=uid(),number="DV-"+w.id.slice(0,8).toUpperCase()+"-"+(w.packages.length+1);const manifest={number,work:w.title,customer:w.customer,currency:w.currency,total:money(total),recipient:w.email,business:org.name,billing:org.billing,issue:d.issue,due:d.due,summary:d.summary,evidence:d.evidence,documents:d.documents,revision:w.revision};const all:Record<string,Uint8Array>={};
 if(existing){const f=await bucket().get(org.id+"/"+w.id+"/"+existing.id);need(f,"Invoice file unavailable.",503);all["invoice.pdf"]=new Uint8Array(await f.arrayBuffer())}
 else all["invoice.pdf"]=await invoice([org.name,org.billing,"INVOICE "+number,"Customer: "+w.customer,"To: "+w.email,"Issue: "+d.issue+"    Due: "+d.due,"Completed work: "+w.title,d.summary,"Confirmed total: "+w.currency+" "+money(total),"Source-supported total; tax treatment confirmed by the operator."]);
 let size=all["invoice.pdf"].length;
 for(const docId of d.documents){if(docId===d.existingInvoice)continue;const doc=w.documents.find(x=>x.id===docId)!;const object=await bucket().get(org.id+"/"+w.id+"/"+docId);need(object,"Supporting document unavailable.",503);size+=doc.size;need(size<12*1024*1024,"Keep the package under 12 MB.",413);all["supporting/"+docId.slice(0,8)+"-"+doc.name]=new Uint8Array(await object.arrayBuffer())}
 const bytes=archive(all,manifest,d.summary);const hash=await digest(bytes);await storeFile(org.id,w.id,id,number+".zip","application/zip",bytes);const pdfId=uid();try{await storeFile(org.id,w.id,pdfId,number+".pdf","application/pdf",all["invoice.pdf"])}catch(e){await removeFile(org.id,id).catch(()=>{});throw e}
 const packet:Packet={id,number,digest:hash,total:money(total),currency:w.currency,recipient:w.email,revision:w.revision,approved:false,created:now(),documents:d.documents,summary:d.summary,delivery:"not_sent"};w.packages.unshift({...packet,pdfId} as Packet);event(w,user.email,"Package "+number+" assembled. Review the exact PDF and attachments before approval.");try{await save(org.id,w,v)}catch(e){await removeFile(org.id,id).catch(()=>{});await removeFile(org.id,pdfId).catch(()=>{});throw e}return response(w)
}
if(p[2]==="approve"&&method==="POST"){const d=z.object({id:z.string().uuid(),digest:z.string(),authorize:z.literal(true)}).strict().parse(input);const packet=w.packages.find(x=>x.id===d.id);need(packet&&packet.digest===d.digest&&packet.revision===w.revision,"The package changed; assemble and review the current version.",409);need(w.requirements.every(r=>["satisfied","waived"].includes(r.status)),"Review all requirements.",409);packet.approved=true;packet.approvedBy=user.email;w.status="Approved";event(w,user.email,"Exact package "+packet.number+" approved, including amount, recipient and listed attachments.");await save(org.id,w,v);return response(w)}
throw new Problem("This operation is not available in the browser workspace.");
}
export async function localApi<T=unknown>(path:string,method="GET",data?:unknown):Promise<T>{
 try{return await handler(path,method,data) as T}catch(error){
  if(error instanceof z.ZodError)throw new Error("Check the fields and source references, then try again.");
  throw error;
 }
}
