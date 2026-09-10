# -*- coding: utf-8 -*-
"""POI 服务：内置示例 POI 库（source=seed）+ 检索。
将来接入高德 Web API 时新增 GaodeAdapter，替换/合并 search_pois 的数据来源即可。
"""
from sqlalchemy.orm import Session

from ..models import Poi

# 内置示例 POI（真实存在的知名地点，坐标与票价为示例值，source=seed）
SEED_POIS: list[dict] = [
    # ---------- 大理 ----------
    {"city": "大理", "poi_type": "hotel", "name": "大理云顶度假酒店", "address": "大理市海东镇环海东路",
     "open_hours": "24 小时", "ticket_price": "约 ¥1200/晚", "rating": 4.7, "tags": "海景,度假,亲子"},
    {"city": "大理", "poi_type": "hotel", "name": "大理古城漫步客栈", "address": "大理古城人民路",
     "open_hours": "24 小时", "ticket_price": "约 ¥380/晚", "rating": 4.5, "tags": "古城,民宿,文艺"},
    {"city": "大理", "poi_type": "hotel", "name": "大理海湾国际酒店", "address": "大理市滨海大道",
     "open_hours": "24 小时", "ticket_price": "约 ¥680/晚", "rating": 4.6, "tags": "海景,商务"},
    {"city": "大理", "poi_type": "attraction", "name": "洱海", "address": "大理市洱海环湖",
     "open_hours": "全天开放", "ticket_price": "免费", "rating": 4.8, "tags": "湖泊,骑行,网红"},
    {"city": "大理", "poi_type": "attraction", "name": "大理古城", "address": "大理市大理古城",
     "open_hours": "全天开放", "ticket_price": "免费", "rating": 4.6, "tags": "古城,历史文化,美食"},
    {"city": "大理", "poi_type": "attraction", "name": "崇圣寺三塔", "address": "大理市三塔路",
     "open_hours": "07:30-18:30", "ticket_price": "¥75", "rating": 4.7, "tags": "寺庙,地标"},
    {"city": "大理", "poi_type": "attraction", "name": "苍山", "address": "大理市苍山景区",
     "open_hours": "08:30-16:30", "ticket_price": "¥40 起", "rating": 4.6, "tags": "山岳,索道"},
    {"city": "大理", "poi_type": "restaurant", "name": "段公子·大理白族菜", "address": "大理古城人民路",
     "open_hours": "11:00-22:00", "ticket_price": "人均 ¥90", "rating": 4.6, "tags": "白族菜,网红"},
    {"city": "大理", "poi_type": "restaurant", "name": "再回首鸡丝凉米线", "address": "大理古城复兴路",
     "open_hours": "08:00-21:00", "ticket_price": "人均 ¥30", "rating": 4.5, "tags": "小吃,米线"},
    {"city": "大理", "poi_type": "restaurant", "name": "洱月小厨", "address": "大理古城博爱路",
     "open_hours": "11:00-22:00", "ticket_price": "人均 ¥110", "rating": 4.7, "tags": "云南菜,私房"},
    # ---------- 北京 ----------
    {"city": "北京", "poi_type": "hotel", "name": "北京饭店", "address": "东城区东长安街 33 号",
     "open_hours": "24 小时", "ticket_price": "约 ¥1500/晚", "rating": 4.6, "tags": "地标,商务"},
    {"city": "北京", "poi_type": "hotel", "name": "全季酒店（王府井店）", "address": "东城区王府井大街",
     "open_hours": "24 小时", "ticket_price": "约 ¥550/晚", "rating": 4.5, "tags": "连锁,干净"},
    {"city": "北京", "poi_type": "attraction", "name": "故宫博物院", "address": "东城区景山前街 4 号",
     "open_hours": "08:30-17:00（周一闭馆）", "ticket_price": "¥60", "rating": 4.9, "tags": "博物馆,历史文化"},
    {"city": "北京", "poi_type": "attraction", "name": "天安门广场", "address": "东城区长安街",
     "open_hours": "全天开放", "ticket_price": "免费", "rating": 4.7, "tags": "地标,升旗"},
    {"city": "北京", "poi_type": "attraction", "name": "颐和园", "address": "海淀区新建宫门路 19 号",
     "open_hours": "06:30-18:00", "ticket_price": "¥30", "rating": 4.8, "tags": "皇家园林,湖景"},
    {"city": "北京", "poi_type": "attraction", "name": "八达岭长城", "address": "延庆区 G6 京藏高速",
     "open_hours": "06:30-19:00", "ticket_price": "¥40", "rating": 4.8, "tags": "长城,世界遗产"},
    {"city": "北京", "poi_type": "restaurant", "name": "全聚德烤鸭店（前门店）", "address": "东城区前门大街 30 号",
     "open_hours": "11:00-21:30", "ticket_price": "人均 ¥200", "rating": 4.5, "tags": "烤鸭,老字号"},
    {"city": "北京", "poi_type": "restaurant", "name": "四季民福烤鸭店（故宫店）", "address": "东城区南池子大街",
     "open_hours": "10:30-22:00", "ticket_price": "人均 ¥150", "rating": 4.7, "tags": "烤鸭,景观位"},
    {"city": "北京", "poi_type": "restaurant", "name": "东来顺（王府井店）", "address": "东城区王府井大街 198 号",
     "open_hours": "11:00-21:30", "ticket_price": "人均 ¥140", "rating": 4.4, "tags": "涮羊肉,老字号"},
    # ---------- 成都 ----------
    {"city": "成都", "poi_type": "hotel", "name": "成都博舍酒店", "address": "锦江区笔帖式街 81 号",
     "open_hours": "24 小时", "ticket_price": "约 ¥1800/晚", "rating": 4.8, "tags": "太古里,设计酒店"},
    {"city": "成都", "poi_type": "hotel", "name": "锦江宾馆", "address": "锦江区人民南路二段 80 号",
     "open_hours": "24 小时", "ticket_price": "约 ¥700/晚", "rating": 4.5, "tags": "老牌,园林"},
    {"city": "成都", "poi_type": "attraction", "name": "成都大熊猫繁育研究基地", "address": "成华区熊猫大道 1375 号",
     "open_hours": "07:30-18:00", "ticket_price": "¥55", "rating": 4.8, "tags": "熊猫,亲子"},
    {"city": "成都", "poi_type": "attraction", "name": "宽窄巷子", "address": "青羊区长顺上街",
     "open_hours": "全天开放", "ticket_price": "免费", "rating": 4.5, "tags": "老街,美食,市井"},
    {"city": "成都", "poi_type": "attraction", "name": "武侯祠", "address": "武侯区武侯祠大街 231 号",
     "open_hours": "09:00-18:00", "ticket_price": "¥50", "rating": 4.6, "tags": "三国,博物馆"},
    {"city": "成都", "poi_type": "attraction", "name": "锦里古街", "address": "武侯区武侯祠大街 231 号",
     "open_hours": "全天开放", "ticket_price": "免费", "rating": 4.4, "tags": "古街,夜市"},
    {"city": "成都", "poi_type": "restaurant", "name": "陈麻婆豆腐（骡马市店）", "address": "青羊区西玉龙街 197 号",
     "open_hours": "11:00-21:00", "ticket_price": "人均 ¥80", "rating": 4.5, "tags": "川菜,老字号"},
    {"city": "成都", "poi_type": "restaurant", "name": "蜀大侠火锅（春熙路店）", "address": "锦江区春熙路",
     "open_hours": "11:00-02:00", "ticket_price": "人均 ¥120", "rating": 4.6, "tags": "火锅,网红"},
    {"city": "成都", "poi_type": "restaurant", "name": "钟水饺（总府路店）", "address": "锦江区总府路 12 号",
     "open_hours": "10:00-21:00", "ticket_price": "人均 ¥50", "rating": 4.4, "tags": "小吃,老字号"},
]


def seed_pois(db: Session) -> int:
    """幂等写入内置 POI 库，返回新增数量。"""
    added = 0
    for item in SEED_POIS:
        exists = (db.query(Poi)
                  .filter(Poi.city == item["city"], Poi.name == item["name"])
                  .first())
        if not exists:
            db.add(Poi(**item, source="seed"))
            added += 1
    db.commit()
    return added


def search_pois(db: Session, city: str | None = None, keyword: str | None = None,
                poi_type: str | None = None, limit: int = 30) -> list[Poi]:
    """检索 POI 池（内置数据；高德接入后在此合并外部来源）。"""
    q = db.query(Poi)
    if city:
        q = q.filter(Poi.city.like(f"%{city}%"))
    if poi_type:
        q = q.filter(Poi.poi_type == poi_type)
    if keyword:
        q = q.filter(Poi.name.like(f"%{keyword}%"))
    return q.order_by(Poi.rating.desc()).limit(limit).all()
