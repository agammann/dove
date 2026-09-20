import { z } from "zod";
import { database } from "../../../db/raw";
const schema=z.object({request_id:z.string().uuid(),name:z.string().trim().min(2).max(100),email:z.string().trim().email().max(254),business:z.string().trim().min(1).max(200),problem:z.string().trim().min(10).max(2000),consent:z.literal("yes"),website:z.string().max(500).optional().default("")}).strict();
const headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"};
function reply(body:unknown,status=200){return Response.json(body,{status,headers});}
export async function POST(request:Request){
 const origin=request.headers.get("origin"); const url=new URL(request.url);
 if(!origin||origin!==url.origin)return reply({error:"Please submit your request from the Dove website."},403);
 if(!request.headers.get("content-type")?.startsWith("application/json"))return reply({error:"Use the access request form."},415);
 if(Number(request.headers.get("content-length")||0)>16384)return reply({error:"Please shorten your request."},413);
 let value:unknown;
 try{const reader=request.body?.getReader();if(!reader)return reply({error:"Your request is empty."},400);let size=0;const chunks:Uint8Array[]=[];while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>16384){await reader.cancel();return reply({error:"Please shorten your request."},413);}chunks.push(value);}const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}value=JSON.parse(new TextDecoder().decode(bytes));}catch{return reply({error:"Please check your request and try again."},400);}
 const parsed=schema.safeParse(value);if(!parsed.success)return reply({error:"Please complete all fields, use a valid email, and accept the data notice."},400);
 const data=parsed.data;if(data.website)return reply({ok:true});
 try{
  const db=database();const now=Date.now(),day=86400000;
  const existing=await db.prepare("SELECT id FROM access_requests WHERE id = ?").bind(data.request_id).first();if(existing)return reply({ok:true});
  const source=request.headers.get("cf-connecting-ip")||"local-shared";
  const hash=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(`${Math.floor(now/day)}:${source}`));
  const sourceHash=Array.from(new Uint8Array(hash)).map(n=>n.toString(16).padStart(2,"0")).join("");
  const results=await db.batch([
   db.prepare("DELETE FROM access_requests WHERE created_at < ?").bind(now-90*day),
   db.prepare(`INSERT INTO access_requests (id,name,email,business,problem,consent,created_at,source_hash) SELECT ?,?,?,?,?,1,?,? WHERE (SELECT COUNT(*) FROM access_requests WHERE source_hash = ? AND created_at > ?) < 5 AND (SELECT COUNT(*) FROM access_requests WHERE created_at > ?) < 300 ON CONFLICT(id) DO NOTHING`).bind(data.request_id,data.name,data.email.toLowerCase(),data.business,data.problem,now,sourceHash,sourceHash,now-day,now-day)
  ]);
  if(!results[1].meta.changes){const saved=await db.prepare("SELECT id FROM access_requests WHERE id = ?").bind(data.request_id).first();if(saved)return reply({ok:true});return reply({error:"We have received several requests recently. Please try again tomorrow."},429);}
  return reply({ok:true},201);
 }catch{console.error("Dove access request storage operation failed");return reply({error:"Your request could not be saved right now. Your details are still in the form. Please try again shortly."},503);}
}
export function GET(){return reply({error:"Access requests are private. Use the form to submit your own."},405);}
