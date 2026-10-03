import { renderToString } from "react-dom/server";
import Home from "../app/page";
import Workspace from "../app/workspace/workspace";

// Initial rendering only: effects, IndexedDB and model generation do not run.
export function renderPage(page: "home" | "workspace") {
  return renderToString(page === "home" ? <Home /> : <Workspace />);
}
