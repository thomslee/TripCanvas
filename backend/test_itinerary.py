# -*- coding: utf-8 -*-
"""M2 轨迹图 API 集成测试：seed / timeline / 节点 CRUD / 顺序 / 交通切换 / 重排。"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import urllib.request

BASE = "http://127.0.0.1:8001/api"


def req(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


ok = 0
def check(name, cond, extra=""):
    global ok
    mark = "PASS" if cond else "FAIL"
    if cond:
        ok += 1
    print(f"[{mark}] {name} {extra}")


# 1. 创建测试行程
st, trip = req("POST", "/trips", {
    "depart_city": "北京", "dest_city": "成都",
    "depart_date": "2026-11-01", "arrive_time": "13:30",
    "return_date": "2026-11-04", "depart_time": "17:00",
    "preferences": {"pace": "balanced", "budget": "mid", "travelers": 2},
})
check("创建行程", st == 201 and trip["trip"]["total_days"] == 4, f"trip_id={trip['trip']['id']}")
tid = trip["trip"]["id"]

# 2. seed 骨架
st, r = req("POST", f"/trips/{tid}/seed")
check("seed 生成骨架", st == 200 and r["seeded"] is True)

# 3. timeline
st, tl = req("GET", f"/trips/{tid}/timeline")
check("timeline 200", st == 200 and len(tl["days"]) == 4, f"days={len(tl['days'])}")
d1 = tl["days"][0]
d2 = tl["days"][1]
d4 = tl["days"][3]
check("D1 窗口与节点", d1["window_start"] == "14:30" and len(d1["nodes"]) >= 3,
      f"D1 {d1['window_start']}-{d1['window_end']} nodes={len(d1['nodes'])} edges={len(d1['edges'])}")
check("中间日节点", len(d2["nodes"]) >= 4, f"D2 nodes={len(d2['nodes'])}")
check("末日窗口", d4["window_end"] == "14:00", f"D4 {d4['window_start']}-{d4['window_end']}")
check("节点含起止时间", bool(d1["nodes"][0]["start_time"]) and bool(d1["nodes"][0]["end_time"]),
      f"{d1['nodes'][0]['name']} {d1['nodes'][0]['start_time']}-{d1['nodes'][0]['end_time']}")
check("无冲突(中间日)", d2["conflict"] is False, f"used={d2['total_used_min']} overflow={d2['overflow_min']}")

# 4. 新增节点
st, node = req("POST", f"/trips/{tid}/days/2/nodes",
               {"node_type": "restaurant", "name": "川菜馆", "duration_minutes": 90})
check("新增节点", st == 201 and node["node_type"] == "restaurant", f"node_id={node['id']}")
nid = node["id"]
st, tl2 = req("GET", f"/trips/{tid}/timeline")
d2b = tl2["days"][1]
check("新增后边重建", len(d2b["edges"]) == len(d2b["nodes"]) - 1,
      f"nodes={len(d2b['nodes'])} edges={len(d2b['edges'])}")
check("跨天隔离(D1 边数不变)", len(tl2["days"][0]["edges"]) == len(d1["edges"]),
      f"D1 edges {len(d1['edges'])} -> {len(tl2['days'][0]['edges'])}")

# 5. 修改节点时长
st, n2 = req("PATCH", f"/nodes/{nid}", {"duration_minutes": 120, "name": "宽窄巷子"})
check("修改节点", st == 200 and n2["duration_minutes"] == 120 and n2["name"] == "宽窄巷子")

# 6. 移动节点（先上移两次测试边界）
st, _ = req("POST", f"/nodes/{nid}/move", {"direction": "up"})
check("上移", st == 200)
st, tl3 = req("GET", f"/trips/{tid}/timeline")
d2c = tl3["days"][1]
names = [n["name"] for n in d2c["nodes"]]
check("上移生效", names.index("宽窄巷子") == 0 or names.index("宽窄巷子") < len(names) - 1,
      f"order={names}")

# 7. 交通切换
edge0 = d2c["edges"][0]
st, e = req("PATCH", f"/edges/{edge0['id']}", {"transport": "taxi"})
check("切换交通", st == 200 and e["transport"] == "taxi" and e["duration_minutes"] == 25,
      f"{e['transport']} {e['duration_minutes']}min")

# 8. 批量重排（反转当天顺序）
st, tl4 = req("GET", f"/trips/{tid}/timeline")
ids = [n["id"] for n in tl4["days"][1]["nodes"]][::-1]
st, r4 = req("POST", f"/trips/{tid}/days/2/reorder", {"node_ids": ids})
check("批量重排", st == 200 and r4["ok"] is True)
st, tl5 = req("GET", f"/trips/{tid}/timeline")
rev_names = [n["name"] for n in tl5["days"][1]["nodes"]]
check("重排后顺序反转", rev_names == names[::-1], f"order={rev_names}")

# 9. 删除节点
st, _ = req("DELETE", f"/nodes/{nid}")
check("删除节点", st == 204)
st, tl6 = req("GET", f"/trips/{tid}/timeline")
d2d = tl6["days"][1]
check("删除后边重建", len(d2d["edges"]) == len(d2d["nodes"]) - 1,
      f"nodes={len(d2d['nodes'])} edges={len(d2d['edges'])}")

# 10. seed 幂等
st, r7 = req("POST", f"/trips/{tid}/seed")
check("seed 幂等跳过", st == 200 and r7["seeded"] is False)

# 11. 非法方向
st, r8 = req("POST", f"/nodes/{d2d['nodes'][0]['id']}/move", {"direction": "sideways"})
check("非法方向 400", st == 400)

print(f"\n=== {ok}/17 passed ===")
