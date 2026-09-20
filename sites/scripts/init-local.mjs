import {readFileSync,writeFileSync,existsSync} from "node:fs";
import {randomBytes} from "node:crypto";
const file=".env.local";
let current=existsSync(file)?readFileSync(file,"utf8"):"OPENAI_MODEL=gpt-4.1-mini\n";
if(!/^DOVE_ADMIN_TOKEN=/m.test(current))current+="\nDOVE_ADMIN_TOKEN="+randomBytes(32).toString("hex")+"\n";
writeFileSync(file,current,{mode:0o600});
console.log("Local administrator secret is ready in ignored .env.local. Add OPENAI_API_KEY there for live analysis; do not commit the file.");

