# -*- coding: utf-8 -*-
"""AI 二次推荐（重排引擎）集成测试"""
import io, sys, json, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = "http://127.0.0.1:8001"

ok = 0
def check(name, cond, extra=""):
    global ok
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name} {extra}")
    if not cond:
        sys.exit(1)
    ok += 1

def req(method, path, body=None):
    r = urllib.request.Request(BASE + path, method=method)
    r.add_header("Content-Type", "application/json")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    try:
        with urllib.request.urlopen(r, data, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")

# 1. 创建行程 + 种子
st, t = req("POST", "/api/trips", {
    "title": "重排测试", "depart_city": "北京", "dest_city": "大理",
    "depart_date": "2026-10-10", "arrive_time": "11:00",
    "return_date": "2026-10-12", "depart_time": "16:00",
})
tid = t["trip"]["id"]
req("POST", f"/api/trips/{tid}/seed")
st, tl = req("GET", f"/api/trips/{tid}/timeline")
nodes_before = [(d["day_no"], n["id"]) for d in tl["days"] for n in d["nodes"]]
check("种子生成", st == 200 and len(nodes_before) > 8, f"{len(nodes_before)} 节点")

# 2. 打乱 D2 顺序（把评分最高的挪到最后：reorder 反序中间段）
d2 = tl["days"][1]
ids = [n["id"] for n in d2["nodes"]]
if len(ids) > 4:
    head, tail = ids[0], ids[-1]
    mid = ids[1:-1]
    mid.reverse()
    st, _ = req("POST", f"/api/trips/{tid}/days/2/reorder", {"node_ids": [head] + mid + [tail]})
    check("手动打乱 D2", st == 200)

# 3. 重排
st, rp = req("POST", f"/api/trips/{tid}/replan")
check("重排接口", st == 200 and rp.get("applied") is True, f"summary={rp.get('summary')}")
print("notes:", rp.get("notes", [])[:6])

# 4. 节点集合不变
st, tl2 = req("GET", f"/api/trips/{tid}/timeline")
nodes_after = [(d["day_no"], n["id"]) for d in tl2["days"] for n in d["nodes"]]
check("节点集合不变", sorted(nodes_before) == sorted(nodes_after), f"{len(nodes_after)} 节点")

# 5. 每天首末锚点不变
for d_b, d_a in zip(tl["days"], tl2["days"]):
    b, a = [n["id"] for n in d_b["nodes"]], [n["id"] for n in d_a["nodes"]]
    if len(b) > 2:
        check(f"D{d_b['day_no']} 首末锚点", b[0] == a[0] and b[-1] == a[-1])

# 6. 评分降序（每天中间段：真实评分节点应基本按评分降序）
def rating_of(nid):
    for d in tl2["days"]:
        for n in d["nodes"]:
            if n["id"] == nid:
                return (n.get("poi") or {}).get("rating") or 0
    return 0

any_mid = False
for d in tl2["days"]:
    mid = d["nodes"][1:-1]
    if len(mid) >= 2:
        rs = [rating_of(n["id"]) for n in mid]
        nonzero = [r for r in rs if r > 0]
        if len(nonzero) >= 2:
            any_mid = True
            check(f"D{d['day_no']} 评分降序", nonzero == sorted(nonzero, reverse=True),
                  f"ratings={nonzero}")
check("存在可验证的评分排序", any_mid)

# 7. 边完整
for d in tl2["days"]:
    check(f"D{d['day_no']} 边完整", len(d["edges"]) == max(0, len(d["nodes"]) - 1),
          f"nodes={len(d['nodes'])} edges={len(d['edges'])}")

# 8. 幂等：再次重排顺序不变
st, rp2 = req("POST", f"/api/trips/{tid}/replan")
st, tl3 = req("GET", f"/api/trips/{tid}/timeline")
same = ([n["id"] for d in tl2["days"] for n in d["nodes"]] ==
        [n["id"] for d in tl3["days"] for n in d["nodes"]])
check("重排幂等", same)

# 9. 营业时间软约束：把 09:00 开门的节点（若有）挪到当天第二，重排后应被处理
d2f = tl2["days"][1]
late = [n for n in d2f["nodes"][1:-1] if n.get("poi") and n["poi"].get("open_hours") and "09:00" in n["poi"]["open_hours"]]
if late and len(d2f["nodes"]) > 4:
    ids2 = [n["id"] for n in d2f["nodes"]]
    head, tail = ids2[0], ids2[-1]
    mid = [n["id"] for n in d2f["nodes"][1:-1]]
    mid.remove(late[0]["id"])
    mid.insert(0, late[0]["id"])  # 放第二位（酒店后）
    req("POST", f"/api/trips/{tid}/days/2/reorder", {"node_ids": [head] + mid + [tail]})
    st, rp3 = req("POST", f"/api/trips/{tid}/replan")
    st, tl4 = req("GET", f"/api/trips/{tid}/timeline")
    d2g = tl4["days"][1]
    target = next((n for n in d2g["nodes"] if n["id"] == late[0]["id"]), None)
    moved_ok = target and (target["start_time"] >= "09:00" or d2g["nodes"][0]["id"] == target["id"])
    check("营业时间软约束（09:00 开门不早于开门）", moved_ok, f"start={target and target['start_time']}")
else:
    print("[SKIP] 无 09:00 开门节点，跳过营业时间用例")

print(f"\n=== {ok} passed ===")
