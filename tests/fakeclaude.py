#!/usr/bin/env python3
import json, os, re, subprocess, sys, time
args = sys.argv[1:]
prompt = args[args.index("-p")+1]
mcp = json.loads(args[args.index("--mcp-config")+1])["mcpServers"]["company"]
settings = json.loads(args[args.index("--settings")+1])
assert settings["sandbox"]["enabled"] and not settings["sandbox"]["allowUnsandboxedCommands"]
assert args[args.index("--permission-mode")+1] == "auto"
def out(o): print(json.dumps(o), flush=True)
out({"type":"system","subtype":"init"})
p = subprocess.Popen([mcp["command"], *mcp["args"]], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env={**os.environ, **mcp["env"]})
n=[0]
def rpc(method, params=None, note=False):
    n[0]+=1; m={"jsonrpc":"2.0","method":method}
    if params is not None: m["params"]=params
    if not note: m["id"]=n[0]
    p.stdin.write(json.dumps(m)+"\n"); p.stdin.flush()
    if note: return
    while True:
        r=json.loads(p.stdout.readline())
        if r.get("id")==n[0]: return r
rpc("initialize",{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"fake","version":"1"}}); rpc("notifications/initialized",note=True)
def tool(name, **a):
    out({"type":"assistant","message":{"content":[{"type":"tool_use","name":"mcp__company__"+name,"input":a}]}})
    r = rpc("tools/call",{"name":name,"arguments":a}); t = r["result"]["content"][0]["text"]; out({"type":"user","message":{"content":[{"type":"tool_result","content":t}]}}); return t
aid = os.environ["AGENT_ID"]; time.sleep(0.5)
if "## Worker's submission" in prompt:
    tid = int(re.search(r"review_verdict\(task_id=(\d+)", prompt).group(1))
    flag = os.path.expanduser(f"~/genesis/var/fake-rejected-{tid}")
    if tid == 1 and not os.path.exists(flag):
        open(flag,"w").write("x"); tool("review_verdict", task_id=tid, approve=False, feedback="1. Add a newline.")
    else:
        tool("review_verdict", task_id=tid, approve=True, feedback="verified")
elif "judge_contest(contest_id=" in prompt:
    cid = int(re.search(r"judge_contest\(contest_id=(\d+)", prompt).group(1))
    win = int(re.findall(r"## Entry #(\d+)", prompt)[-1])
    tool("judge_contest", contest_id=cid, winner_task_id=win, rationale="entry is cleaner")
elif "## Task #" in prompt:
    tid = int(re.search(r"## Task #(\d+)", prompt).group(1))
    open(f"file-{tid}.txt","w").write(f"work by {aid}\n")
    subprocess.run(["git","add","-A"]); subprocess.run(["git","commit","-qm",f"work for {tid}"])
    tool("submit_work", summary=f"wrote file-{tid}.txt")
else:
    tool("read_inbox")
out({"type":"result","subtype":"success","is_error":False,"num_turns":2,"total_cost_usd":0.01,"result":"ok","usage":{"input_tokens":10,"output_tokens":5}})
p.kill()
