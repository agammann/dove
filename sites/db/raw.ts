import {env} from "cloudflare:workers";
export function database(): D1Database {if(!env.DB) throw new Error("Access request storage unavailable"); return env.DB;}
