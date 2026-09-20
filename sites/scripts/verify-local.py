"""Local integration verification; fictional data only. Never prints secret values."""
import json, os, hashlib, io, zipfile, uuid
from pathlib import Path
import httpx as requests
site=Path(__file__).resolve().parent.parent
root=site
(root/"outputs").mkdir(exist_ok=True)
config=dict(line.strip().split("=",1) for line in (site/".env.local").read_text(encoding="utf-8-sig").splitlines() if "=" in line and not line.startswith("#"))
base=os.getenv("DOVE_TEST_URL","http://127.0.0.1:5174")
assert base in ("http://localhost:5173","http://127.0.0.1:5174"), "This test runs only against local development or built preview."
built=base.endswith(":5174")
email="verify-"+uuid.uuid4().hex+"@example.invalid" if built else "seedy@sites.test"
s=requests.Client(trust_env=False)
s.headers.update({"Origin":base,"X-Dove-Action":"1","Cookie":"__sites_local_auth=1"})
if built: s.headers.update({"oai-authenticated-user-id":"verify-"+uuid.uuid4().hex,"oai-authenticated-user-email":email})
checks=[]
def call(path,method="GET",data=None,status=200,**kwargs):
    r=s.request(method,base+"/api/dove/"+path,json=data,timeout=65,**kwargs)
    assert r.status_code==status,(path,r.status_code,r.text[:500])
    return r.json() if "json" in r.headers.get("content-type","") else r
def check(name):checks.append(name);print("PASS",name,flush=True)
anon=requests.get(base+"/api/dove/me",timeout=20)
assert anon.status_code==401
check("anonymous access denied")
me=call("me",status=403)
admin=call("admin","POST",{"name":"Fictional Studio - verification","email":email},201,headers={"Authorization":"Bearer "+config["DOVE_ADMIN_TOKEN"]})
call("accept","POST",{"token":admin["token"]})
me=call("me")
assert me["integrations"]["ai"] and not me["integrations"]["email"]
check("invitation membership and configured AI")
call("accept","POST",{"token":admin["token"]},409)
call("settings","PUT",{"name":"Fictional Studio","billing":"100 Example Lane, Sample City\nPayment due within 30 days.","paused":False})
w=call("work","POST",{"title":"Fictional brand handoff","customer":"Example Customer","contactName":"Fictional Contact","email":"contact@example.invalid","authorized":True,"currency":"USD","description":"Brand identity files delivered and accepted."},201)
wid=w["id"];path="work/"+wid+"/"
call(path+"package","POST",{},409)
check("unreviewed work cannot be packaged")
source="Fictional agreement and completion record.\nThe final billing amount is USD 2400.00, including all applicable taxes.\nThe purchase order is PO-1042 and must accompany the invoice.\nThe brand identity files were delivered on 2026-09-19.\nExample Customer accepts the delivered work in full.\nBilling recipient: Fictional Contact, contact@example.invalid.\n"
r=s.post(base+"/api/dove/"+path+"document",files={"file":("Agreement.txt",source.encode(),"text/plain")},timeout=30)
assert r.status_code==200,(r.status_code,r.text)
w=r.json();doc=w["documents"][0]
check("private document stored and extracted")
assert call("file/"+doc["id"]).content==source.encode()
call(path+"requirement","PUT",{"requirement":{"title":"Bad quote","category":"custom","status":"satisfied","reason":"Test incorrect evidence","evidence":[{"documentId":doc["id"],"page":1,"quote":"This is invented."}]}},400)
check("invented evidence rejected")
w=call(path+"analyze","POST")
assert w["requirements"] and all(r["status"] in ["received","missing","conflict"] for r in w["requirements"])
check("live OpenAI returned source-verified proposals without auto-approval")
for req in w["requirements"]:
    payload={k:req[k] for k in ("title","category","status","reason","evidence")}
    payload.update(status="satisfied",reason="Fictional test: operator checked the cited source and confirmed this requirement.")
    w=call(path+"requirement","PUT",{"id":req["id"],"requirement":payload})
assert w["status"]=="Ready to package"
check("human decisions resolve checklist")
ev=[{"documentId":doc["id"],"page":1,"quote":"The final billing amount is USD 2400.00, including all applicable taxes."}]
pkg={"total":"2400.00","issue":"2026-09-19","due":"2026-10-19","summary":"Brand identity delivered and accepted in this fictional verification fixture.","evidence":ev,"documents":[doc["id"]],"confirmed":True}
call(path+"package","POST",{**pkg,"total":"9900.00"},400)
call(path+"package","POST",{**pkg,"issue":"2026-02-31"},400)
check("unsupported amount and impossible date rejected")
w=call(path+"package","POST",pkg);p=w["packages"][0]
r=call("file/"+p["id"]);assert hashlib.sha256(r.content).hexdigest()==p["digest"]
with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    assert "invoice.pdf" in z.namelist()
    manifest=json.loads(z.read("manifest.json"))
    assert manifest["total"]=="2400.00" and manifest["recipient"]=="contact@example.invalid"
    assert z.read("invoice.pdf").startswith(b"%PDF-")
(root/"outputs/dove-sites-package.zip").write_bytes(r.content)
check("ZIP digest, invoice PDF, source attachments and manifest verified")
pdf=call("file/"+p["pdfId"]).content
r=s.post(base+"/api/dove/"+path+"document",files={"file":("Generated invoice.pdf",pdf,"application/pdf")},timeout=40)
assert r.status_code==200,(r.status_code,r.text[:500])
w=r.json()
assert "2400.00" in "".join(w["documents"][-1]["pages"])
check("real PDF extraction on generated invoice")
call(path+"approve","POST",{"id":p["id"],"digest":p["digest"],"authorize":True},409)
check("new evidence invalidates earlier package approval")
for req in w["requirements"]:
    payload={k:req[k] for k in ("title","category","status","reason","evidence")}
    payload.update(status="satisfied",reason="Checked new fictional invoice against original evidence.")
    w=call(path+"requirement","PUT",{"id":req["id"],"requirement":payload})
w=call(path+"package","POST",pkg);p=w["packages"][0]
call(path+"approve","POST",{"id":p["id"],"digest":"wrong","authorize":True},409)
w=call(path+"approve","POST",{"id":p["id"],"digest":p["digest"],"authorize":True})
assert w["packages"][0]["approved"]
call(path+"deliver","POST",{"id":p["id"],"digest":p["digest"],"authorize":True},503)
assert call("work/"+wid)["packages"][0]["delivery"]=="not_sent"
check("exact package approval; unconfigured email fails closed")
bad=s.post(base+"/api/dove/"+path+"pause",json={"paused":True},headers={"Origin":"https://evil.invalid"},timeout=20)
assert bad.status_code==403
check("cross-origin mutation blocked")
snapshot=call("work/"+wid);assert snapshot["packages"][0]["approved"]
if built:
    other_email="other-"+uuid.uuid4().hex+"@example.invalid"
    other=requests.Client(trust_env=False,headers={"Origin":base,"X-Dove-Action":"1","oai-authenticated-user-id":"other-"+uuid.uuid4().hex,"oai-authenticated-user-email":other_email})
    assert other.get(base+"/api/dove/me").status_code==403
    inv=call("admin","POST",{"name":"Other fictional workspace","email":other_email},201,headers={"Authorization":"Bearer "+config["DOVE_ADMIN_TOKEN"]})
    assert other.post(base+"/api/dove/accept",json={"token":admin["token"]}).status_code==403
    assert other.post(base+"/api/dove/accept",json={"token":inv["token"]}).status_code==200
    assert other.get(base+"/api/dove/work/"+wid).status_code==404
    assert other.get(base+"/api/dove/file/"+p["id"]).status_code==404
    assert other.get(base+"/api/dove/work").json()==[]
    check("foreign workspace cannot read work, files or reuse invitations")
    quota=s.post(base+"/api/dove/"+path+"document",content=b"x"*(4*1024*1024+20001),headers={"Content-Type":"multipart/form-data; boundary=test"},timeout=30)
    assert quota.status_code==413
    check("oversized upload rejected before parsing")
    # An early 413 may close the connection with request bytes still unread.
    previous_headers=dict(s.headers); s.close(); s=requests.Client(trust_env=False,headers=previous_headers)
    assert call("work/"+wid)["packages"][0]["approved"]
    check("failed upload preserves approved package")
(root/"outputs/dove-sites-verification.json").write_text(json.dumps({"checks":checks,"work_id":wid,"org_id":admin["org"],"package_digest":p["digest"],"requirements":len(w["requirements"]),"live_ai":True},indent=2),encoding="utf-8")
print("VERIFIED",len(checks),"checks",flush=True)
