import os, sys, threading, time
os.environ.update(GENESIS_DB=os.path.abspath("var/test.db"), GENESIS_CLAUDE_BIN=os.path.abspath("var/fakeclaude.py"), GENESIS_NO_GITHUB="1")
sys.path.insert(0,"runtime")
from genesis import scheduler, db, config, gitops
config.TICK_SECONDS = 1; scheduler.TICK_SECONDS = 1
s = scheduler.Scheduler(); s.last_publish = time.time()+1e9; s.last_export = time.time()+1e9
th = threading.Thread(target=s.loop, daemon=True); th.start()
c = db.connect()
for i in range(90):
    time.sleep(1)
    st = {r[0]:r[1] for r in c.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")}
    if i % 5 == 0: print(i, st, "running:", list(s.running))
    if st.get("done",0) >= 3 and not s.running and set(st) <= {"done","cancelled"}: break
s.stopping = True; time.sleep(2)
for t in c.execute("SELECT id, title, status, attempts, assignee, reviewer, substr(feedback,1,60) FROM tasks"): print(tuple(t))
print("main log:\n" + gitops.git(["log","--oneline"], "ventures/zz-test-venture").stdout)
print("files on main:", sorted(os.listdir("ventures/zz-test-venture")))
print("worktrees left:", os.listdir("var/worktrees"))
print("events:", [r[0] for r in c.execute("SELECT kind||':'||summary FROM events WHERE kind IN ('shipped','rejected','contest_judged','spawned','no_submit','error','integration_failed') ORDER BY id")])
print("agents:", c.execute("SELECT COUNT(*) FROM agents").fetchone()[0], "runs:", [tuple(r) for r in c.execute("SELECT status, COUNT(*) FROM runs GROUP BY status")])
