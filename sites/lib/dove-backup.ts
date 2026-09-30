import { z } from "zod";
import { zipSync, unzipSync, strToU8, strFromU8 } from "fflate";
import { createInput } from "./dove-local";
import { requirementInput, digest, need, validEvidence } from "./dove-core";
import { snapshot, readState, commit, download, MAX_BYTES } from "./dove-storage";
import type { StoredFile } from "./dove-storage";
import type { Work } from "./dove-types";

const id = z.string().uuid(), text = z.string().max(2000);
const documentSchema = z.object({ id, name:z.string().min(1).max(150), mime:z.enum(["application/pdf","text/plain"]), size:z.number().int().min(1).max(4*1024*1024), pages:z.array(z.string().max(100000)).min(1).max(40), approved:z.boolean() }).strict();
const packetSchema = z.object({id,pdfId:id.optional(),number:text,digest:z.string().regex(/^[a-f0-9]{64}$/),total:text,currency:z.enum(["USD","EUR","GBP","CAD","AUD"]),recipient:z.string().email(),revision:z.number().int().nonnegative(),approved:z.boolean(),approvedBy:text.optional(),created:z.string().datetime(),documents:z.array(id).max(10),summary:text,delivery:text,providerId:text.optional()}).strict();
const workSchema = createInput.extend({id,status:text,revision:z.number().int().nonnegative(),documents:z.array(documentSchema).max(10),requirements:z.array(requirementInput.extend({id,reviewedBy:text.optional()})).max(30),packages:z.array(packetSchema).max(10),requests:z.array(z.object({id,requirements:z.array(id).max(20),body:z.string().max(3000),recipient:z.string().email(),status:text,providerId:text.optional(),created:z.string().datetime()}).strict()).max(10),activity:z.array(z.object({at:z.string().datetime(),by:text,text:z.string().max(3000)}).strict()).max(150),created:z.string().datetime(),calls:z.number().int().nonnegative(),paused:z.boolean()}).strict();
const manifestSchema=z.object({format:z.literal("dove-browser-backup"),version:z.literal(1),workspace:z.object({id:z.literal("local"),name:z.string().min(1).max(200),billing:z.string().max(1500),paused:z.union([z.literal(0),z.literal(1)])}).strict(),work:z.array(workSchema).max(100),files:z.array(z.object({id,workId:id,name:z.string().min(1).max(200),mime:z.enum(["application/pdf","text/plain","application/zip"]),sha256:z.string().regex(/^[a-f0-9]{64}$/)}).strict()).max(100)}).strict();

export async function exportBackup() {
  const {state,files}=await snapshot(), entries:Record<string,Uint8Array>=Object.create(null);
  const index=[];
  for(const f of files){entries["files/"+f.id]=f.bytes;index.push({id:f.id,workId:f.workId,name:f.name,mime:f.mime,sha256:await digest(f.bytes)})}
  entries["workspace.json"]=strToU8(JSON.stringify({format:"dove-browser-backup",version:1,workspace:state.workspace,work:state.work,files:index}));
  download(zipSync(entries,{level:0}),"dove-backup-"+new Date().toISOString().slice(0,10)+".zip","application/zip");
}
export async function importBackup(file:File) {
  const current=await readState();
  need(file.size>0&&file.size<=90*1024*1024,"Choose a Dove backup ZIP up to 90 MB.");
  let total=0,count=0;
  const entries=unzipSync(new Uint8Array(await file.arrayBuffer()),{filter(entry){
    count++;total+=entry.originalSize;
    need(count<=101&&total<=85*1024*1024,"This backup exceeds workspace limits.");
    need(entry.name==="workspace.json"||/^files\/[0-9a-f-]{36}$/.test(entry.name),"Unexpected file in this backup.");
    need(entry.originalSize<=(entry.name==="workspace.json"?20*1024*1024:MAX_BYTES),"This backup entry is too large.");
    return true;
  }});
  need(entries["workspace.json"],"This is not a complete Dove browser backup.");
  const parsed=manifestSchema.safeParse(JSON.parse(strFromU8(entries["workspace.json"])));
  need(parsed.success,"The backup format or records are invalid. Your current workspace is unchanged.");
  const data=parsed.data, files:StoredFile[]=[], expected=new Map<string,{workId:string;mime:string;size?:number}>();
  need(new Set(data.work.map(w=>w.id)).size===data.work.length,"Duplicate work items in backup.");
  for(const w of data.work){
    need(w.documents.flatMap(d=>d.pages).join("").length<=200000,"A work item contains too much text.");
    need(new Set(w.requirements.map(r=>r.id)).size===w.requirements.length,"Duplicate requirements in backup.");
    for(const d of w.documents){need(!expected.has(d.id),"Duplicate document in backup.");expected.set(d.id,{workId:w.id,mime:d.mime,size:d.size})}
    for(const r of w.requirements)need(r.evidence.every(e=>validEvidence(w as Work,e)),"A restored quote does not match its source.");
    for(const p of w.packages){
      need(p.documents.every(id=>w.documents.some(d=>d.id===id)),"Package refers to a missing document.");
      need(!expected.has(p.id),"Duplicate package in backup.");expected.set(p.id,{workId:w.id,mime:"application/zip"});
      if(p.pdfId){need(!expected.has(p.pdfId),"Duplicate invoice in backup.");expected.set(p.pdfId,{workId:w.id,mime:"application/pdf"})}
      p.approved=false;delete p.approvedBy;
    }
    if(w.packages.length)w.status="Review restored packages";
  }
  need(data.files.length===expected.size&&new Set(data.files.map(f=>f.id)).size===data.files.length,"Backup is missing files or contains duplicates.");
  need(Object.keys(entries).length===data.files.length+1,"Backup file index does not match its contents.");
  for(const f of data.files){
    const bytes=entries["files/"+f.id], ref=expected.get(f.id);
    need(bytes&&ref&&ref.workId===f.workId&&ref.mime===f.mime&&(!ref.size||ref.size===bytes.length),"Backup document metadata is inconsistent.");
    need(await digest(bytes)===f.sha256,"A backup file failed its integrity check.");
    files.push({id:f.id,workId:f.workId,name:f.name.replace(/[\\/\x00-\x1f]/g,"_"),mime:f.mime,bytes});
  }
  for(const w of data.work)for(const p of w.packages)need(await digest(entries["files/"+p.id])===p.digest,"A package fingerprint does not match its saved bytes.");
  // The same atomic version check as normal saves also protects changes made
  // in another tab while the backup was being decoded and validated.
  await commit({version:current.version,workspace:data.workspace,work:data.work},files,[],true);
}
