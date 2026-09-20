import {readFileSync,mkdirSync,writeFileSync} from "node:fs";
import {resolve} from "node:path";
const options=Object.fromEntries(process.argv.slice(2).map(x=>x.replace(/^--/,"").split(/=(.*)/s).slice(0,2)));
const url=options.url||"https://dove-paperwork.alx21.chatgpt.site";
if(!options.name)throw Error('Usage: node scripts/create-workspace.mjs --name="Your business" --email="owner@example.com" [--url=http://localhost:5173]');
const vars=Object.fromEntries(readFileSync(".env.local","utf8").split(/\r?\n/).filter(x=>/^[A-Z_]+=/.test(x)).map(x=>x.split(/=(.*)/s).slice(0,2)));
if(!vars.DOVE_ADMIN_TOKEN)throw Error("Set DOVE_ADMIN_TOKEN in ignored .env.local and the matching Sites server secret.");
const u=new URL(url);if(u.protocol!=="https:"&&!["localhost","127.0.0.1"].includes(u.hostname))throw Error("Use HTTPS for a hosted workspace.");
const res=await fetch(u.origin+"/api/dove/admin",{method:"POST",headers:{Authorization:"Bearer "+vars.DOVE_ADMIN_TOKEN,"Content-Type":"application/json"},body:JSON.stringify({name:options.name,email:options.email||null})});
if(!res.ok)throw Error("Workspace creation failed: HTTP "+res.status);
const data=await res.json();
mkdirSync("outputs",{recursive:true});
const output=resolve("outputs","workspace-invitation-"+data.org+".txt");
writeFileSync(output,"Private Dove workspace invitation (single use; expires in 72 hours).\nShare only with the intended owner.\n\n"+u.origin+"/workspace#invite="+data.token+"\n\nInvitation code (if sign-in removes the URL fragment):\n"+data.token+"\n",{mode:0o600});
console.log("Workspace created. The private invitation was saved locally to "+output+". No email was sent.");

