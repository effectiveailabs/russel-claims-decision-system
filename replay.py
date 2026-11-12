"""Replay 1,000 synthetic wildfire total losses through claim.rsl, under the policy's 180-day
rebuild clause and under a proposed 12-month clause, and compare the two.

Usage: python replay.py [N]      (pip install rslc)
"""
import json, os, random, shutil, subprocess, sys, tempfile, time, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
RSLC = os.environ.get("RSLC", "rslc")

def claims(n):
    random.seed(7); loss = dt.date(2026, 1, 8); out = []
    for i in range(1, n + 1):
        a = random.choice([800000, 1200000, 1500000, 2000000, 2500000, 3500000, 5000000])
        ded = random.choice([2500, 5000, 10000, 25000])
        rebuild = int(a * random.uniform(0.9, 2.3) / 1000) * 1000
        days = random.randint(20, 540)
        started = days >= 60 and random.random() < 0.55
        rep = loss + dt.timedelta(days=random.randint(1, 10))
        out.append({"reported": str(rep), "notice_sent": True, "claim": {
            "loss_date": str(loss), "as_of": str(loss + dt.timedelta(days=days)), "rebuild_started": started,
            "house_limit": a, "ops_limit": a // 10, "deductible": ded, "contents_limit": a // 2, "monthly_living": 14000,
            "rebuild_cost": rebuild, "debris_cost": int(a * 0.08), "code_cost": int(a * 0.12)}})
    return out

def box(switch, alert):
    d = tempfile.mkdtemp(prefix="wf-")
    for f, a, b in [("settlement.rsl", "switch_day [cite: form:p3] = 180", f"switch_day [cite: form:p3] = {switch}"),
                    ("claim.rsl", "alert_day [cite: guide:p18] = 150", f"alert_day [cite: guide:p18] = {alert}")]:
        t = open(os.path.join(HERE, f)).read(); assert a in t
        open(os.path.join(d, f), "w").write(t.replace(a, b))
    return d

def run(d, cs):
    esc = 0; paid = [0, 0]; files = [0, 0]
    for i, c in enumerate(cs):
        log = os.path.join(d, f"c{i}.jsonl"); facts = os.path.join(d, "facts.json")
        json.dump(c, open(facts, "w"))
        subprocess.run([RSLC, "submission", "open", log, "--program", os.path.join(d, "claim.rsl"), "--as", "supervisor:replay"], capture_output=True, check=True)
        s = json.loads(subprocess.run([RSLC, "--json", "submission", "answer", log, "--file", facts, "--as", "supervisor:replay"], capture_output=True, text=True, check=True).stdout)
        st = s["status"]
        e = any(r["state"] == "Open" for r in st["referrals"])
        out = dict(st.get("outcomes") or {})
        # house paid = position less debris and code
        house = out["position"] - min(c["claim"]["code_cost"], c["claim"]["house_limit"]) - _debris(c, d)
        esc += e; paid[e] += house; files[e] += 1
    return dict(n=len(cs), escalated=esc, house_no_esc=paid[0], files_no_esc=files[0], house_esc=paid[1])

def _debris(c, d):  # recompute debris the same way the rule does, to subtract it
    k = c["claim"]; sw = int(open(os.path.join(d, "settlement.rsl")).read().split("switch_day [cite: form:p3] = ")[1].split()[0])
    days = (dt.date.fromisoformat(k["as_of"]) - dt.date.fromisoformat(k["loss_date"])).days
    vb = days >= sw and not k["rebuild_started"]
    base = k["house_limit"] if vb else max(min(k["rebuild_cost"], k["house_limit"] * 2), k["house_limit"])
    return round(min(k["debris_cost"], base * 0.30))

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    cs = claims(n)
    for label, sw, al in [("policy today: 180 days", 180, 150), ("proposed: 12 months", 365, 335)]:
        d = box(sw, al); t = time.time(); r = run(d, cs); r["seconds"] = round(time.time() - t, 1)
        print(label, json.dumps(r)); shutil.rmtree(d)
