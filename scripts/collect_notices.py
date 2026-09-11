"""Copy dependency license notices from the installed locked environments."""
import importlib.metadata
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
out = root / "THIRD-PARTY-NOTICES"
out.mkdir(exist_ok=True)
index = []
for dist in importlib.metadata.distributions():
    name = dist.metadata.get("Name", "unknown")
    label = re.sub(r"[^a-zA-Z0-9_.]", "_", name + "_" + dist.version)
    copied = []
    for file in dist.files or []:
        if any(x.lower().startswith(("license", "notice", "copying", "copyright")) for x in Path(str(file)).parts):
            source = Path(dist.locate_file(file))
            if source.is_file() and source.stat().st_size < 3_000_000:
                target = out / (label + "__" + re.sub(r"[^a-zA-Z0-9_.]", "_", str(file)))
                target.write_bytes(source.read_bytes())
                copied.append(target.name)
    index.append({"ecosystem": "Python", "name": name, "version": dist.version, "license": dist.metadata.get("License-Expression") or dist.metadata.get("License"), "notices": copied})
for source in (root / "frontend" / "node_modules" / ".pnpm").rglob("package.json"):
    if source.parent.name == "node_modules":
        continue
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        continue
    if not data.get("name") or not data.get("version"):
        continue
    label = re.sub(r"[^a-zA-Z0-9_.]", "_", data["name"] + "_" + data["version"])
    copied = []
    for file in source.parent.iterdir():
        if file.is_file() and file.name.lower().startswith(("license", "notice", "copying", "copyright")):
            target = out / (label + "__" + file.name)
            target.write_bytes(file.read_bytes())
            copied.append(target.name)
    index.append({"ecosystem": "npm", "name": data["name"], "version": data["version"], "license": data.get("license"), "notices": copied})
(out / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
(out / "README.md").write_text("# Dependency notices\n\nCopies of license and notice files supplied by installed locked Python and npm dependencies. The index includes runtime and development packages. Docker base images retain their distribution notices within the images. These licenses do not assign a license to Dove's original source. Regenerate using the locked environments and scripts/collect_notices.py.\n", encoding="utf-8")
print(f"Collected notices for {len(index)} installed package entries")
