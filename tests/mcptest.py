import json, subprocess, os, sys, time
sys.path.insert(0, "runtime")
os.environ["GENESIS_DB"] = os.path.abspath("var/test.db")
from genesis import db
c = db.connect()
for aid, role, kind in [("ceo","ceo","leader"),("cto","cto","leader"),("engineer-1","engineer","worker"),("reviewer-1","reviewer","worker")]:
    c.execute("INSERT OR IGNORE INTO agents(id, role, kind, model, status, created_at) VALUES (?,?,?,?,?,?)", (aid, role, kind, "sonnet", "idle", time.time()))

def session(agent, calls):
    env = {**os.environ, "PYTHONPATH":"runtime", "AGENT_ID":agent, "GENESIS_DB":os.path.abspath("var/test.db"), "GENESIS_NO_GITHUB":"1"}
    p = subprocess.Popen([".venv/bin/python","-m","genesis.mcp_server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    def send(o): p.stdin.write(json.dumps(o)+"\n"); p.stdin.flush()
    def recv():
        while True:
            l = p.stdout.readline()
            if not l: raise SystemExit("server died: "+p.stderr.read()[-2000:])
            m = json.loads(l)
            if "id" in m: return m
    send({"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"1"}}})
    recv(); send({"jsonrpc":"2.0","method":"notifications/initialized"})
    out=[]
    for i,(name,args) in enumerate(calls,1):
        if name=="__list":
            send({"jsonrpc":"2.0","id":i,"method":"tools/list"}); out.append([t["name"] for t in recv()["result"]["tools"]])
        else:
            send({"jsonrpc":"2.0","id":i,"method":"tools/call","params":{"name":name,"arguments":args}})
            r = recv(); out.append(r.get("result",{}).get("content",[{}])[0].get("text") if "result" in r else r)
    p.kill(); return out

r = session("ceo", [("__list",{}),
  ("rename_company",{"name":"Test Co","tagline":"testing"}),
  ("create_venture",{"name":"zz-test-venture","pitch":"A test venture.\nMore."}),
  ("create_task",{"title":"Build hello","description":"d","role":"engineer","acceptance_criteria":"a","venture":"zz-test-venture"}),
  ("create_task",{"title":"Hard thing","description":"d","role":"engineer","acceptance_criteria":"a","venture":"zz-test-venture","competitors":2}),
  ("create_task",{"title":"x","description":"d","role":"nope","acceptance_criteria":"a"}),
  ("define_role",{"name":"security-auditor","title":"Security Auditor","kind":"worker","model":"sonnet","description":"audits","charter":"You audit."}),
  ("send_message",{"to":"cto","subject":"hi","body":"hello"}),
  ("remember",{"topic":"zz test topic","content":"the sky is blue"}),
  ("recall",{"query":"sky blue"}),
  ("list_tasks",{}),
  ("company_status",{}),
])
print("TOOLS:", r[0]); 
for x in r[1:]: print("->", str(x)[:160].replace("\n"," | "))
print("CTO inbox:", session("cto", [("read_inbox",{})])[0])
print("engineer define_role:", session("engineer-1", [("define_role",{"name":"x-y","title":"t","kind":"worker","model":"sonnet","description":"d","charter":"c"})])[0])
