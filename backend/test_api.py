# -*- coding: utf-8 -*-
import io, sys, json, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = "http://127.0.0.1:8001"

def req(method, path, body=None):
    url = BASE + path
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    r = urllib.request.Request(url, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw.decode("utf-8")) if raw else None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")

# 1) 创建行程
body = {
    "depart_city": "北京", "dest_city": "大理",
    "depart_date": "2026-10-01", "arrive_time": "14:30",
    "return_date": "2026-10-05", "depart_time": "18:00",
    "preferences": {"pace": "relaxed", "interest": ["nature", "food"], "budget": "mid", "travelers": 2},
}
s, out = req("POST", "/api/trips", body)
print("POST /api/trips ->", s)
if s == 201:
    t = out["trip"]
    print("  title:", t["title"], "| days:", t["total_days"], "| status:", t["status"])
    print("  windows:")
    for w in out["windows"]:
        print(f"    D{w['day_no']} {w['date']} {w['start']}-{w['end']} ({w['note']})")
    print("  messages:", out["messages"])
    trip_id = t["id"]
else:
    print("  ERR:", out)
    trip_id = None

# 2) 列表
s, lst = req("GET", "/api/trips")
print("GET /api/trips ->", s, "| count:", len(lst) if isinstance(lst, list) else lst)

# 3) 详情
if trip_id:
    s, d = req("GET", f"/api/trips/{trip_id}")
    print("GET /api/trips/{id} ->", s, "| days:", len(d.get("days", [])), "| first day:", d["days"][0] if d.get("days") else None)

# 4) 非法日期
bad = {"depart_city": "北京", "dest_city": "大理",
       "depart_date": "2026-10-05", "return_date": "2026-10-01"}
s, out = req("POST", "/api/trips", bad)
print("POST invalid dates ->", s, out if s != 201 else "UNEXPECTED")
