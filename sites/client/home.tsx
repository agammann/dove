import { hydrateRoot } from "react-dom/client";
import Home from "../app/page";
import "../app/globals.css";

const root = document.getElementById("dove-root");
if (!root) throw new Error("Dove's page root is missing.");
hydrateRoot(root, <Home />);
