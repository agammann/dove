import { hydrateRoot } from "react-dom/client";
import Workspace from "../app/workspace/workspace";
import "../app/globals.css";
import "../app/workspace/workspace.css";

const root = document.getElementById("dove-root");
if (!root) throw new Error("Dove's page root is missing.");
hydrateRoot(root, <Workspace />);
