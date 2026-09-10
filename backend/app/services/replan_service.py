# -*- coding: utf-8 -*-
"""AI 二次推荐：基于评分 / 类型分布 / 营业时间的确定性重排引擎。
保留用户手动增删的节点集合与时长设置，仅对每天中间节点智能重排并重建交通边。
将来接入 LLM 后可在此结果上做语言润色与个性化说明。"""
import re
import datetime as dt
from typing import Optional

from sqlalchemy.orm import Session

from ..models import Trip, TripDay, ItineraryNode, Poi
from . import seed_planner


def _rating(node: ItineraryNode) -> float:
    return float(node.poi.rating) if node.poi and node.poi.rating else 0.0


def _open_window(poi: Optional[dict]) -> Optional[tuple[dt.time, dt.time]]:
    """解析营业时间 '07:30-18:30'（兼容 '24小时/全天开放'，含闭馆备注）。poi 为 timeline 节点携带的 dict。"""
    if not poi or not poi.get("open_hours"):
        return None
    s = poi["open_hours"]
    m = re.search(r"(\d{1,2}:\d{2})\s*[-~]\s*(\d{1,2}:\d{2})", s)
    if not m:
        return None
    try:
        return dt.time.fromisoformat(m.group(1)), dt.time.fromisoformat(m.group(2))
    except ValueError:
        return None


def _interleave(items: list) -> list:
    """类型交替微调：连续 >=3 个同类型时，将后续与之后最近的不同类型交换（一遍贪心）。"""
    out = list(items)
    n = len(out)
    i = 0
    while i < n - 2:
        a, b, c = out[i], out[i + 1], out[i + 2]
        if a.node_type == b.node_type == c.node_type and a.node_type != "hotel":
            # 找之后第一个不同类型
            j = i + 3
            while j < n and out[j].node_type == a.node_type:
                j += 1
            if j < n:
                out[i + 2], out[j] = out[j], out[i + 2]
                i += 2  # 交换后从 i+2 继续检查
                continue
        i += 1
    return out


def _apply_order(db: Session, day: TripDay, ordered: list[ItineraryNode]) -> None:
    for idx, node in enumerate(ordered, start=1):
        node.sort_order = idx
    seed_planner._rebuild_day_edges(db, day.trip_id, day.id, ordered)
    db.flush()


def _rebuild_from_db(db: Session, day: TripDay) -> None:
    """按数据库当前 sort_order 顺序重建当天边（交换节点后使用）。"""
    ordered = (db.query(ItineraryNode)
               .filter(ItineraryNode.day_id == day.id)
               .order_by(ItineraryNode.sort_order)
               .all())
    seed_planner._rebuild_day_edges(db, day.trip_id, day.id, ordered)
    db.flush()


def _fmt_mm(t: Optional[dt.time]) -> int:
    return t.hour * 60 + t.minute if t else 0


def replan_trip(db: Session, trip: Trip) -> dict:
    """对行程内每一天执行智能重排，返回调整说明。"""
    notes: list[str] = []
    changed_days = 0

    days = (db.query(TripDay)
            .filter(TripDay.trip_id == trip.id)
            .order_by(TripDay.day_no)
            .all())

    for day in days:
        nodes = (db.query(ItineraryNode)
                 .filter(ItineraryNode.day_id == day.id)
                 .order_by(ItineraryNode.sort_order)
                 .all())
        # 预加载 POI（统一赋值，保证 _rating 安全）
        for n in nodes:
            n.poi = db.get(Poi, n.poi_id) if n.poi_id else None

        if len(nodes) <= 3:
            continue  # 过短无需重排

        head, tail = nodes[0], nodes[-1]  # 锚点：首末不动（通常为酒店）
        middle = nodes[1:-1]

        before = [n.id for n in middle]
        # 1) 评分降序（稳定排序，占位/无评分沉底）
        ranked = sorted(middle, key=lambda n: -_rating(n))
        # 2) 类型交替微调
        ranked = _interleave(ranked)
        after = [n.id for n in ranked]
        moved = [n for n in ranked if n.id not in before or before.index(n.id) != after.index(n.id)]

        _apply_order(db, day, [head] + ranked + [tail])
        day_notes = []

        # 3) 营业时间软约束：单次相邻交换
        tl = seed_planner.compute_day_timeline(db, day)
        tl_nodes = tl["nodes"]
        swapped = True
        guard = 0
        while swapped and guard < len(tl_nodes):
            swapped = False
            guard += 1
            tl = seed_planner.compute_day_timeline(db, day)
            tl_nodes = tl["nodes"]
            for i in range(len(tl_nodes) - 1):
                n = tl_nodes[i]
                w = _open_window(n.get("poi"))
                if not w:
                    continue
                open_t = _fmt_mm(w[0])
                start_t = _fmt_mm(dt.time.fromisoformat(n["start_time"]))
                if start_t < open_t:
                    # 与下一节点交换再试
                    cur = db.get(ItineraryNode, n["id"])
                    nxt = db.get(ItineraryNode, tl_nodes[i + 1]["id"])
                    cur.sort_order, nxt.sort_order = nxt.sort_order, cur.sort_order
                    _rebuild_from_db(db, day)
                    tl2 = seed_planner.compute_day_timeline(db, day)
                    n2 = next((x for x in tl2["nodes"] if x["id"] == n["id"]), None)
                    ok = n2 and _fmt_mm(dt.time.fromisoformat(n2["start_time"])) >= open_t
                    if ok:
                        day_notes.append(
                            f"D{day.day_no}：「{n['name']}」营业 {w[0].strftime('%H:%M')} 开门，"
                            f"已调整到开门后安排")
                        swapped = True
                        break
                    # 还原
                    cur.sort_order, nxt.sort_order = nxt.sort_order, cur.sort_order
                    _rebuild_from_db(db, day)
                    break  # 该节点尝试一次后退出

        # 记录移动说明
        for n in moved:
            if _rating(n) > 0:
                day_notes.append(f"D{day.day_no}：「{n.name}」评分 {_rating(n):.1f}，已优先安排")
            else:
                day_notes.append(f"D{day.day_no}：「{n.name}」为占位节点，已置于评分节点之后")

        if day_notes:
            changed_days += 1
            notes.extend(day_notes[:4])  # 每天最多 4 条说明

    db.commit()
    summary = f"已按评分、类型分布与营业时间重排 {changed_days} 天"
    return {"applied": True, "summary": summary, "notes": notes}
