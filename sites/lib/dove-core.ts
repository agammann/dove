import type { Work, Evidence, Requirement } from "./dove-types";
import { z } from "zod";
export class Problem extends Error { constructor(message:string,public status=400){super(message)} }
export function need(value:unknown,message:string,status=400):asserts value {if(!value)throw new Problem(message,status)}
export const uid=()=>crypto.randomUUID();
export const now=()=>new Date().toISOString();
export async function digest(value:string|Uint8Array){const b=typeof value==="string"?new TextEncoder().encode(value):value;return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",b as BufferSource))).map(n=>n.toString(16).padStart(2,"0")).join("")}
export function event(w:Work,by:string,text:string){w.activity.unshift({at:now(),by,text});w.activity=w.activity.slice(0,150)}
export function invalidate(w:Work){w.revision++;for(const p of w.packages)p.approved=false;w.status="Review required"}
export const normalize=(s:string)=>s.replace(/\s+/g," ").trim();
export function validEvidence(w:Work,e:Evidence){const d=w.documents.find(x=>x.id===e.documentId);return !!d&&e.page>=1&&e.page<=d.pages.length&&normalize(e.quote).length>=3&&normalize(d.pages[e.page-1]).includes(normalize(e.quote))}
export const evidenceInput=z.object({documentId:z.string().uuid(),page:z.number().int().min(1).max(40),quote:z.string().trim().min(3).max(1500)}).strict();
export const requirementInput=z.object({title:z.string().trim().min(1).max(200),category:z.enum(["purchase_order","acceptance","deliverable","amount","billing_recipient","custom"]),status:z.enum(["missing","received","conflict","satisfied","waived"]),evidence:z.array(evidenceInput).max(10),reason:z.string().trim().min(5).max(1000)}).strict();
export function validateAnalysis(w:Work,a:unknown){need(w.documents.length,"Upload a source document first.");const parsed=z.object({requirements:z.array(requirementInput.omit({status:true}).extend({status:z.enum(["missing","received","conflict"])})).max(20)}).strict().parse(a);for(const p of parsed.requirements)need(p.evidence.length>0&&p.evidence.every(e=>validEvidence(w,e)),"The analysis included an unverified quote. Review the source and try again.",400);return parsed.requirements.map(p=>({...p,id:uid()})) as Requirement[]}
