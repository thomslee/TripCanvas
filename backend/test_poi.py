# -*- coding: utf-8 -*-
"""POI 关联功能集成测试：搜索 / 种子关联 / 清单 / 插入指定位置 / 替换 / 删除联动。"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import urllib.request, urllib.error

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


# 0. POI 库初始化
st, r = req("POST", "/pois/seed")
check("POI 库初始化", st == 200, f"新增 {r['seeded']} 条")

# 1. 搜索（按城市+类型+关键字）
st, pois = req("GET", "/pois/search?city=%E5%A4%A7%E7%90%86&type=attraction")
check("搜索大理景点", st == 200 and len(pois) >= 4 and pois[0]["name"], f"{len(pois)} 条，如 {pois[0]['name']}")
st, h = req("GET", "/pois/search?q=%E5%85%A8%E8%81%9A%E5%BE%B7")
check("关键字搜索全聚德", st == 200 and len(h) >= 1 and h[0]["name"].startswith("全聚德"),
      h[0]["name"] if h else "")
check("POI 含特有数据", bool(pois[0].get("open_hours")) and bool(pois[0].get("ticket_price")),
      f"{pois[0]['name']} {pois[0]['open_hours']} {pois[0]['ticket_price']}")

# 2. 创建成都行程并 seed（应关联真实 POI）
st, trip = req("POST", "/trips", {
    "depart_city": "北京", "dest_city": "成都",
    "depart_date": "2026-11-01", "arrive_time": "13:30",
    "return_date": "2026-11-04", "depart_time": "17:00",
})
check("创建行程", st == 201, f"trip_id={trip['trip']['id']}")
tid = trip["trip"]["id"]
req("POST", f"/trips/{tid}/seed")
st, tl = req("GET", f"/trips/{tid}/timeline")
all_nodes = [n for d in tl["days"] for n in d["nodes"]]
poi_nodes = [n for n in all_nodes if n["poi_id"]]
check("种子关联真实 POI", len(poi_nodes) > 0, f"{len(poi_nodes)}/{len(all_nodes)} 个节点关联")
check("POI 节点带营业/票价", bool(poi_nodes[0]["poi"]) and bool(poi_nodes[0]["poi"]["open_hours"]),
      f"{poi_nodes[0]['name']} | {poi_nodes[0]['poi']['ticket_price']}")
keep_placeholder = [n for n in all_nodes if not n["poi_id"]]
check("保留占位节点(统称)", len(keep_placeholder) > 0, f"{len(keep_placeholder)} 个占位")

# 3. 行程 POI 清单
st, tpois = req("GET", f"/trips/{tid}/pois")
check("行程 POI 清单", st == 200 and len(tpois) == len({n["poi_id"] for n in poi_nodes}),
      f"{len(tpois)} 个真实地点")

# 4. 插入指定位置（真实 POI 到 D2 第一节点之后）
poi_d2 = req("GET", "/pois/search?city=%E6%88%90%E9%83%BD&type=attraction")[1][0]
d2 = tl["days"][1]
anchor = d2["nodes"][0]
st, nn = req("POST", f"/trips/{tid}/days/2/nodes", {
    "node_type": "attraction", "name": "x",
    "duration_minutes": 120, "poi_id": poi_d2["id"],
    "after_node_id": anchor["id"],
})
check("插入真实 POI 到指定位置", st == 201 and nn["poi_id"] == poi_d2["id"] and nn["name"] == poi_d2["name"],
      f"{nn['name']} 在 {anchor['name']} 之后")
st, tl2 = req("GET", f"/trips/{tid}/timeline")
d2b = tl2["days"][1]
names = [n["name"] for n in d2b["nodes"]]
check("插入位置正确", names.index(poi_d2["name"]) == names.index(anchor["name"]) + 1,
      f"order={names}")

# 4b. 插入最前面（after_node_id=-1）
st, nn1 = req("POST", f"/trips/{tid}/days/2/nodes", {
    "node_type": "attraction", "name": "x",
    "duration_minutes": 120, "poi_id": poi_d2["id"],
    "after_node_id": -1,
})
st2, tl2b = req("GET", f"/trips/{tid}/timeline")
first = tl2b["days"][1]["nodes"][0]["name"]
check("插入最前面", st == 201 and first == poi_d2["name"], f"first={first}")

# 5. 替换占位节点为真实 POI（占位可能在任意天，取整行程首个占位）
all_nodes2 = [n for d in tl2["days"] for n in d["nodes"]]
placeholder = next((n for n in all_nodes2 if not n["poi_id"]), None)
check("仍有占位节点可替换", placeholder is not None, f"占位={placeholder['name'] if placeholder else '无'}")
if placeholder is None:
    sys.exit(1)
poi_r = req("GET", "/pois/search?city=%E6%88%90%E9%83%BD&type=restaurant")[1][0]
st, rep = req("PATCH", f"/nodes/{placeholder['id']}", {"poi_id": poi_r["id"]})
check("替换占位为真实 POI", st == 200 and rep["name"] == poi_r["name"] and rep["poi_id"] == poi_r["id"],
      f"{placeholder['name']} -> {rep['name']}")

# 6. 清除 POI 关联（恢复占位）
st, clr = req("PATCH", f"/nodes/{placeholder['id']}", {"poi_id": 0})
check("清除关联恢复占位", st == 200 and clr["poi_id"] is None and "占位" in clr["name"],
      clr["name"])

# 7. 从清单删除真实 POI → 节点联动删除
st, tpois2 = req("GET", f"/trips/{tid}/pois")
target = tpois2[0]
before_cnt = len([n for d in tl2["days"] for n in d["nodes"] if n["poi_id"] == target["poi"]["id"]])
st, _ = req("DELETE", f"/trips/{tid}/pois/{target['poi']['id']}")
check("删除清单 POI", st == 204)
st, tl3 = req("GET", f"/trips/{tid}/timeline")
after_cnt = len([n for d in tl3["days"] for n in d["nodes"] if n["poi_id"] == target["poi"]["id"]])
check("轨迹图联动删除", before_cnt >= 1 and after_cnt == 0, f"{before_cnt} -> {after_cnt} 节点")
for d in tl3["days"]:
    check(f"D{d['day_no']} 边完整", len(d["edges"]) == len(d["nodes"]) - 1,
          f"nodes={len(d['nodes'])} edges={len(d['edges'])}")

# 8. 删除不在行程的 POI → 404
st, r404 = req("DELETE", f"/trips/{tid}/pois/999999")
check("删除不存在 POI 404", st == 404)

print(f"\n=== {ok} passed ===")
