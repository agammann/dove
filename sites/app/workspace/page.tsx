import { requireChatGPTUser } from "../chatgpt-auth";
import Workspace from "./workspace";
import "./workspace.css";
export const dynamic="force-dynamic";
export default async function Page(){const user=await requireChatGPTUser("/workspace");return <Workspace displayName={user.displayName}/>;}
