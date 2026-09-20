import {readFileSync,writeFileSync,mkdirSync,copyFileSync} from "node:fs";
import {resolve} from "node:path";
import {spawn} from "node:child_process";
import "./sites-env.mjs";
// Test only on loopback. Sites supplies trusted identity headers in production;
// a standalone local Worker does not implement the hosting authentication layer.
const root=resolve("."),directory=resolve(".sites-runtime","built-preview");
mkdirSync(directory,{recursive:true});
const config=JSON.parse(readFileSync("dist/server/wrangler.json","utf8"));
config.main=resolve("dist/server/index.js");
config.assets.directory=resolve("dist/client");
writeFileSync(resolve(directory,"wrangler.json"),JSON.stringify(config));
copyFileSync(".env.local",resolve(directory,".dev.vars"));
const child=spawn(process.execPath,["node_modules/wrangler/bin/wrangler.js","dev","--config",resolve(directory,"wrangler.json"),"--local","--persist-to",resolve(".wrangler/state"),"--ip","127.0.0.1","--port","5174","--inspector-port","0"],{cwd:root,stdio:"inherit"});
child.on("exit",code=>{process.exitCode=code??1});

