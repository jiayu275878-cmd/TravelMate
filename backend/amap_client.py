"""高德接口客户端。

这个文件只做一件事：把高德的 HTTP 接口包装成几个好用的 Python 函数。
它不关心前端要什么结构的 JSON，也不关心页面长什么样，那是 app.py 的事。

为什么要把两者分开：它们的改动原因不同。高德改了参数格式，只改这个文件；
前端改了展示需求，只改 app.py。混在一起写，迟早会变成一团理不清的代码。
"""

import os
import time
import math
from concurrent.futures import ThreadPoolExecutor

import requests
from dotenv import load_dotenv

# 让这个文件无论被谁 import 都自己保证配置已加载，不依赖调用顺序。
load_dotenv()

# 高德 Web 服务接口的公共前缀。所有接口都是 GET，参数走查询字符串。
BASE_URL = "https://restapi.amap.com/v3"

# 超时 5 秒：宁可快速失败并告诉用户"暂时查不到"，也不要让页面一直转圈。
TIMEOUT = 5

# 一次搜索最多补几次地理编码。输入提示的条目本来就大多带坐标，需要补的是少数，
# 设个上限是为了避免一次搜索打出十几个请求，把每天的配额白白消耗掉。
MAX_GEOCODE_FIX = 3

# 一次搜索最多返回几条候选。手机一屏看不完更多，多取只会多花配额。
MAX_RESULTS = 8


class AmapError(Exception):
    """高德请求失败的统一异常。

    把"网络不通"和"高德拒绝"这两种失败都包成同一个类型，
    上层只要接住它、把 message 显示给用户就够了，不用分别处理。
    """

    def __init__(self, message, code="AMAP_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


def _get(url, params):
    """所有高德请求的唯一出口：统一注入 Key、统一超时、统一判断错误。

    参数是完整地址而不是路径，因为路线规划要用到 v4 接口（骑行），
    它和 v3 不在同一个前缀下，报错格式也不一样。
    """
    key = os.getenv("AMAP_WEB_SERVICE_KEY", "").strip()
    if not key:
        raise AmapError("后端没有读到 AMAP_WEB_SERVICE_KEY，请检查 backend/.env", "NO_KEY")

    try:
        resp = requests.get(url, params={**params, "key": key}, timeout=TIMEOUT)
    except requests.RequestException as exc:
        # 重要：requests 的异常信息里带着完整的请求 URL，而 URL 里含 Key。
        # 所以异常原文只打到服务端终端，绝不交给前端，否则密钥会从错误信息里漏出去。
        print(f"[amap] 请求失败：{exc}")
        raise AmapError("连接高德失败，请检查网络后重试", "NETWORK_ERROR") from exc

    try:
        data = resp.json()
    except ValueError as exc:
        raise AmapError("高德返回的内容不是 JSON，接口地址可能变了", "BAD_RESPONSE") from exc

    # 高德两代接口的成败标志不同，两种都要认：
    #   v3 用 status（字符串 "1" 表示成功），错误信息在 info / infocode
    #   v4 用 errcode（数字 0 表示成功），错误信息在 errmsg
    # 用它而不是 HTTP 状态码判断，是因为高德出错时 HTTP 依然是 200。
    if "status" in data and data.get("status") != "1":
        info = str(data.get("info", "UNKNOWN"))
        raise AmapError(f"高德拒绝了请求：{info}", str(data.get("infocode", "AMAP_REJECTED")))

    if "errcode" in data and data.get("errcode") != 0:
        raise AmapError(f"高德拒绝了请求：{data.get('errmsg')}", str(data.get("errcode")))

    if "status" not in data and "errcode" not in data:
        raise AmapError("高德返回的结构无法识别，接口可能变了", "BAD_RESPONSE")

    return data


def _request(path, params):
    """v3 接口的快捷方式：内部拼接公共前缀。"""
    return _get(f"{BASE_URL}{path}", params)


def _split_location(location):
    """把高德的 "经度,纬度" 字符串拆成两个浮点数。

    注意顺序是经度在前、纬度在后。写成 [纬度, 经度] 的话地图上的点会跑到完全不对的地方，
    这是初学地图开发最容易犯的错。
    """
    if not isinstance(location, str) or "," not in location:
        return None, None

    lng, lat = location.split(",", 1)
    try:
        return float(lng), float(lat)
    except ValueError:
        return None, None


def _as_text(value):
    """把高德偶尔返回的数组字段统一成字符串。

    高德有些字段（例如 city）有时给字符串、有时给数组、有时给空数组 []。
    如果原样透给前端，前端就要为同一个字段处理两种类型。统一在这一层做完，
    前端拿到的永远是字符串。
    """
    if isinstance(value, list):
        return " ".join(str(item) for item in value if item)
    if value is None:
        return ""
    return str(value)


def input_tips(keywords):
    """输入提示：用户边打字边给的联想结果，相当于搜索引擎的补全。

    返回的每一条大致包含名称、所在区县、城市编码与坐标，是目的地搜索的主路径。
    """
    return _request("/assistant/inputtips", {"keywords": keywords}).get("tips", [])


def geocode(address, city=None):
    """地理编码：把一段文字地址变成确定的经纬度与行政区编码。

    输入提示给不出的信息用它来补。city 可以填城市名或城市编码，用来缩小范围。
    """
    params = {"address": address}
    if city:
        params["city"] = city

    geocodes = _request("/geocode/geo", params).get("geocodes", [])
    if not geocodes:
        return None

    first = geocodes[0]
    lng, lat = _split_location(first.get("location"))
    return {
        "adcode": _as_text(first.get("adcode")),
        "district": _as_text(first.get("province")) or _as_text(first.get("city")),
        "lng": lng,
        "lat": lat,
        "address": _as_text(first.get("formatted_address")),
        "source": "geocode",
    }


def _tip_to_item(tip):
    """把高德的一条提示，整理成前端要用的字段。

    只保留前端真正需要的字段，而不是把高德的原始结构原样透出去：
    这样前端结构稳定，将来高德改了字段名，只需要改这一个函数。
    """
    lng, lat = _split_location(tip.get("location"))
    return {
        "id": _as_text(tip.get("id")) or _as_text(tip.get("adcode")) or _as_text(tip.get("name")),
        "name": _as_text(tip.get("name")).strip(),
        "district": _as_text(tip.get("district")),
        "adcode": _as_text(tip.get("adcode")),
        "lng": lng,
        "lat": lat,
        "address": _as_text(tip.get("address")),
        "source": "tips",
    }


def _fill_missing(item, keywords, budget):
    """对缺坐标的候选，用地理编码补一次。budget 是还能补几次。

    这里故意吞掉异常：补一条候选失败，不应该让整次搜索失败。
    失败的条目会因为缺坐标在下一步被过滤掉，其他结果照常返回。
    """
    if budget <= 0:
        return

    try:
        filled = geocode(item["name"] or keywords)
    except AmapError as exc:
        print(f"[amap] 补齐坐标失败，跳过这一条：{exc.message}")
        return

    if not filled or filled["lng"] is None:
        return

    item["adcode"] = item["adcode"] or filled["adcode"]
    item["district"] = item["district"] or filled["district"]
    item["lng"] = filled["lng"]
    item["lat"] = filled["lat"]
    item["source"] = "tips+geocode"


def search_destinations(keywords):
    """目的地搜索：把用户输入的一串字，变成可以在地图上定位的候选地点。

    三步走：
    1. 先用输入提示拿联想结果，这是主路径；
    2. 对其中缺坐标的少数条目，用地理编码补齐；
    3. 如果一条都定位不了，就退一步，直接对输入本身做一次地理编码。
    """
    keywords = keywords.strip()
    items = [_tip_to_item(tip) for tip in input_tips(keywords)]

    budget = MAX_GEOCODE_FIX
    for item in items:
        if item["lng"] is None and item["name"]:
            _fill_missing(item, keywords, budget)
            budget -= 1

    # 目的地必须有坐标。没有坐标的候选，后面查天气、搜景点、规划路线全都做不了，
    # 所以这里直接丢掉，而不是把一个残缺的数据交给前端去判断。
    usable = [item for item in items if item["name"] and item["lng"] is not None]

    if not usable:
        # 兜底：联想结果一条都用不了（例如用户输入的是一个完整地址），直接地理编码。
        #
        # 关键区分：「查不到」是正常结果，返回空列表让前端提示"换个说法试试"；
        # 只有接口真的坏了（例如 Key 无效）才算错误。高德在查不到时返回的是
        # ENGINE_RESPONSE_DATA_ERROR，落到这里就该走空列表这条路，而不是让整个请求失败。
        try:
            one = geocode(keywords)
        except AmapError as exc:
            print(f"[amap] 兜底地理编码没有结果：{exc.message}")
            one = None

        if one and one["lng"] is not None:
            one["id"] = one["adcode"] or keywords
            one["name"] = keywords
            usable = [one]

    return usable[:MAX_RESULTS]


# 天气缓存：{adcode: (取回时刻, 结果)}
#
# 为什么要缓存：天气在十分钟内基本不会变，但用户会反复刷新页面、来回切换步骤。
# 每刷一次就打一次高德，既快不起来，也在白白消耗每天的配额。
#
# 为什么用内存字典而不是 Redis：后端只有一个进程、只在本机跑，字典就是最简单够用的方案。
# 代价要说清楚：进程重启缓存就没了；将来如果开多个进程，每个进程会各有一份缓存。
WEATHER_TTL = 600  # 秒，十分钟
_weather_cache = {}


def _normalize_forecast(cast):
    """把一天的预报整理成前端要用的字段。"""
    return {
        "date": _as_text(cast.get("date")),
        "week": _as_text(cast.get("week")),
        "dayweather": _as_text(cast.get("dayweather")),
        "nightweather": _as_text(cast.get("nightweather")),
        "daytemp": _as_text(cast.get("daytemp")),
        "nighttemp": _as_text(cast.get("nighttemp")),
        "daywind": _as_text(cast.get("daywind")),
        "daypower": _as_text(cast.get("daypower")),
    }


def _weather_casts(forecast_data):
    """从预报的返回里取出每天的预报。

    高德在 extensions=all 时返回的字段名是 forecasts（复数），每条里有 casts 数组。
    这里同时兼容 forecast 与 forecasts 两种写法：接口版本不同会看到不同的命名，
    多写一个 or 就能让页面不受影响，比上线后才发现少一个字母要好。
    """
    items = forecast_data.get("forecasts") or forecast_data.get("forecast") or []
    if not items:
        return [], {}
    first = items[0]
    return first.get("casts") or [], first


def get_weather(adcode):
    """查天气：按行政区编码取实时天气与未来三天预报。

    高德的天气接口只认行政区编码（adcode），不认经纬度 —— 这也是第 1 步必须把
    adcode 存下来的原因。
    """
    cached = _weather_cache.get(adcode)
    if cached and time.time() - cached[0] < WEATHER_TTL:
        return cached[1]

    # 高德把天气拆成两个扩展参数：extensions=base 给实时天气（lives），
    # extensions=all 给未来几天预报（forecasts）。想要两者就要请求两次 ——
    # 这也是这里值得加缓存的原因：同一个城市十分钟内只花两次配额。
    live_data = _request("/weather/weatherInfo", {"city": adcode, "extensions": "base"})
    forecast_data = _request("/weather/weatherInfo", {"city": adcode, "extensions": "all"})

    lives = live_data.get("lives") or []
    live_raw = lives[0] if lives else None
    casts, forecast_raw = _weather_casts(forecast_data)

    result = {
        "adcode": adcode,
        "city": _as_text((live_raw or {}).get("city")) or _as_text(forecast_raw.get("city")),
        "province": _as_text((live_raw or {}).get("province"))
        or _as_text(forecast_raw.get("province")),
        "live": None
        if live_raw is None
        else {
            "weather": _as_text(live_raw.get("weather")),
            "temperature": _as_text(live_raw.get("temperature")),
            "winddirection": _as_text(live_raw.get("winddirection")),
            "windpower": _as_text(live_raw.get("windpower")),
            "humidity": _as_text(live_raw.get("humidity")),
            "reporttime": _as_text(live_raw.get("reporttime")),
        },
        "forecast": [_normalize_forecast(cast) for cast in casts],
    }

    _weather_cache[adcode] = (time.time(), result)
    return result


# ---------------------------------------------------------------- 景点搜索

# 一次取多少条。20 条足够手机滚两三屏，再多也看不完。
PAGE_SIZE = 20

# 景点的兴趣点类型码：110000 是风景名胜大类，110100 是公园广场大类。
#
# 为什么要两个都给：实测只给 110000 时，高德返回的是"冼星海纪念馆、北帝古庙、钟落潭文化广场"
# 这类冷门条目；把 110100 一起给，返回的才是广州塔、长隆、白云山、沙面岛这种必去榜。
# 一个参数之差，结果质量完全不同 —— 这就是要用真实请求试出来的地方。
SCENIC_TYPES = "110000|110100"


# 有关键词时，只保留这两大类兴趣点：
#   11 风景名胜（含公园广场）
#   14 科教文化服务（博物馆、展览馆、文化宫都在这一类下）
#
# 第一版只留了 11，结果搜"博物馆"只返回两条 —— 南越王博物院的类型码是 140100，
# 被过滤规则误伤了。放宽到这两类，既留住了博物馆，又仍然挡掉停车场（15）、
# 购物中心（06）、地铁站（15）这些"名字里有景点名、但不是景点"的条目。
KEYWORD_KEEP_PREFIXES = ("11", "14")


def _looks_visitable(typecode):
    """判断一条兴趣点是不是"值得去的地方"。

    类型码可能是 "110204|110202" 这种多值形式，所以要拆开逐段判断：
    只要有一段属于上面那两大类，就留下。
    """
    parts = [part for part in _as_text(typecode).split("|") if part]
    return any(part.startswith(KEYWORD_KEEP_PREFIXES) for part in parts)


def _distance_meters(lng1, lat1, lng2, lat2):
    """两点间的距离，单位米。

    用半正矢公式配合地球平均半径，在城市范围内足够准，
    也不需要引入额外的地理计算库 —— 我们只是要排序和显示"大约几公里"。
    """
    radius = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def _poi_to_item(poi, origin):
    """把高德的一条兴趣点整理成前端要用的字段。"""
    lng, lat = _split_location(poi.get("location"))
    item = {
        "id": _as_text(poi.get("id")) or _as_text(poi.get("name")),
        "name": _as_text(poi.get("name")).strip(),
        "address": _as_text(poi.get("address")),
        "district": _as_text(poi.get("adname")),
        "lng": lng,
        "lat": lat,
        "typecode": _as_text(poi.get("typecode")),
        # 高德的 type 是 "风景名胜;风景名胜;国家级景点" 这种分层文字，取最后一级最直观
        "typeText": _as_text(poi.get("type")).split(";")[-1],
        "distanceMeters": None,
    }

    # 有出发地坐标就算一下直线距离，前端可以显示"距目的地约 2.3 公里"。
    if origin and origin[0] is not None and lng is not None:
        item["distanceMeters"] = round(_distance_meters(origin[0], origin[1], lng, lat))

    return item


def search_attractions(adcode, keywords="", page=1, origin=None):
    """景点搜索：在指定城市里找景点，可以带关键词细化。

    这里有一个刻意的分工，是实测之后才定下来的：

    - 不带关键词时，用类型码请求（types=110000|110100）：高德按自身权重给我们一份
      "该城市值得去的地方"的列表，正好是景点页打开时的默认内容。
    - 带关键词时，请求里**不带**类型码，拿到结果后再自己按类型码过滤。
      原因：实测同时给 keywords 与 types 时，类型会把排序压过去 ——
      搜"广州塔"第一条返回的却是越秀公园。想要关键词排序对，就得让类型过滤发生在返回之后。

    也就是说：接口能过滤的交给接口，接口过滤会把排序搞坏的，就自己来。
    """
    params = {
        "city": adcode,
        # citylimit 是关键：只在这个城市范围内找。
        # Day 2 搜"北京路"返回北京店铺的问题，就是靠这个参数解决的。
        "citylimit": "true",
        "offset": str(PAGE_SIZE),
        "page": str(page),
        "extensions": "base",
    }

    keywords = keywords.strip()
    if keywords:
        params["keywords"] = keywords
    else:
        params["types"] = SCENIC_TYPES

    data = _request("/place/text", params)
    items = [_poi_to_item(poi, origin) for poi in (data.get("pois") or [])]

    # 定位失败的条目留着也没用：后面的路线规划需要坐标
    items = [item for item in items if item["name"] and item["lng"] is not None]

    if keywords:
        items = [item for item in items if _looks_visitable(item["typecode"])]

    # 从近到远排序。没有出发地坐标时保留高德自己的排序。
    if origin and origin[0] is not None:
        items.sort(key=lambda item: item["distanceMeters"])

    try:
        total = int(data.get("count") or 0)
    except (TypeError, ValueError):
        total = 0

    return {
        "adcode": adcode,
        "keywords": keywords,
        "page": page,
        "pageSize": PAGE_SIZE,
        # 有关键词时我们自己过滤过，条数会比高德报的总数少，
        # 所以 hasMore 只作为"还有下一页"的参考，不用它算精确结果数。
        "hasMore": page * PAGE_SIZE < total,
        "list": items,
    }


# ---------------------------------------------------------------- 路线规划

# 三种交通方式对应的接口地址与报文版本。
#
# 注意骑行用的是 v4 接口，它和另外两个不在同一个前缀下，报错格式也不同
# （v3 看 status，v4 看 errcode）。这些差异全部收在这张表和一个 _get 里，
# 上层调用者不需要知道。
ROUTE_ENDPOINTS = {
    "walking": ("https://restapi.amap.com/v3/direction/walking", "v3"),
    "driving": ("https://restapi.amap.com/v3/direction/driving", "v3"),
    "bicycling": ("https://restapi.amap.com/v4/direction/bicycling", "v4"),
}

# 最多允许几个点。5 个景点是产品上的上限，留一个余量作为技术兜底，
# 防止有人直接调接口传进来几十个点，一次消耗掉一天的配额。
MAX_ROUTE_POINTS = 6


def _to_int(value, default=0):
    """把高德返回的数字统一成整数。

    v3 接口把距离写成字符串（"11030"），v4 接口写成数字（22822），
    所以两种都要能转。转不了就给默认值，不让页面因为一个脏字段整个崩掉。
    """
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _parse_polyline(text):
    """把 "经度,纬度;经度,纬度" 这样的字符串拆成坐标数组。

    这是前端画线真正需要的数据结构。放在后端做，是因为三种交通方式、
    每一段路、每一个 step 都要做同一件事 —— 前端只画，不转换。
    """
    points = []
    for pair in _as_text(text).split(";"):
        if "," not in pair:
            continue
        lng, lat = _split_location(pair)
        if lng is None:
            continue
        points.append([lng, lat])
    return points


def _route_paths(data, version):
    """取出路线数组：v3 在 data.route.paths，v4 在 data.data.paths。"""
    if version == "v3":
        return (data.get("route") or {}).get("paths") or []
    return (data.get("data") or {}).get("paths") or []


def plan_route(mode, points):
    """按给定顺序把多个点连成一条路线。

    为什么要逐段请求，而不是一次把途经点都传给高德：
    实测发现只有驾车接口支持 waypoints，步行与骑行会**静默忽略**这个参数 ——
    带不带途经点返回的距离完全一样，用户选的中间景点被跳过，而且不报任何错。
    与其为三种方式写两套逻辑，不如统一逐段请求：几个点就连几次，
    再把每段的距离、耗时和折线拼起来。三种交通方式因此走同一条代码路径，
    顺带还多出了每段的明细，可以显示"广州塔 → 陈家祠 3.2 公里"。

    代价要说清楚：一次规划会发出"点数减一"次请求（最多 5 个点就是 4 次）。
    规划是用户主动点一次才发生的动作，不是每次进页面都跑，这个代价可以接受。
    """
    if mode not in ROUTE_ENDPOINTS:
        raise AmapError("只支持步行、驾车、骑行三种交通方式", "BAD_MODE")
    if len(points) < 2:
        raise AmapError("至少需要两个景点才能规划路线", "TOO_FEW_POINTS")
    if len(points) > MAX_ROUTE_POINTS:
        raise AmapError(f"一次最多规划 {MAX_ROUTE_POINTS} 个点", "TOO_MANY_POINTS")

    url, version = ROUTE_ENDPOINTS[mode]
    legs = []
    path = []
    total_distance = 0
    total_duration = 0

    for start, end in zip(points, points[1:]):
        data = _get(
            url,
            {
                "origin": f"{start['lng']},{start['lat']}",
                "destination": f"{end['lng']},{end['lat']}",
            },
        )

        paths = _route_paths(data, version)
        if not paths:
            raise AmapError(
                f"高德没有给出「{start.get('name') or '起点'}」到「{end.get('name') or '终点'}」的路线",
                "NO_ROUTE",
            )

        first = paths[0]
        distance = _to_int(first.get("distance"))
        duration = _to_int(first.get("duration"))

        for step in first.get("steps") or []:
            for point in _parse_polyline(step.get("polyline")):
                # 相邻两段的接缝处会出现重复点，去掉，免得折线在接缝上多画一笔
                if not path or path[-1] != point:
                    path.append(point)

        legs.append(
            {
                "from": start.get("name") or "",
                "to": end.get("name") or "",
                "distance": distance,
                "duration": duration,
            }
        )
        total_distance += distance
        total_duration += duration

    return {
        "mode": mode,
        "distance": total_distance,
        "duration": total_duration,
        "legs": legs,
        # path 已经是坐标数组，前端可以直接交给地图的折线对象
        "path": path,
    }


# ---------------------------------------------------------------- 沿途美食

# 餐饮服务的兴趣点类型码。实测与用 keywords="美食" 的结果几乎一致，
# 但类型码更精确：它不会把名字里恰好带"美食"两个字的非餐饮店铺带进来。
FOOD_TYPES = "050000"

# 每个搜索中心的半径。两公里大约等于"开车路过时愿意绕一下"的范围。
FOOD_RADIUS_M = 2000

# 每个中心取多少条。取多了没意义，最后只会展示前面一小部分。
FOOD_PAGE_SIZE = 10

# 最多搜索几个中心。每多一个中心就多一次高德请求，这是覆盖度与配额之间的取舍。
MAX_FOOD_CENTERS = 10

# 最终最多返回多少家餐厅
FOOD_MAX_RESULTS = 24

# 两个中心相距小于这个距离时视为同一个点，只搜一次
CENTER_MERGE_M = 300

# 每个搜索点最多取几家。
#
# 为什么要限量：如果每个点都取十条，然后按"离路线由近到远"全局排序再截断，
# 结果会被最密集的那个点独占 —— 实测时 24 家餐厅全部在某个景点的 107 米以内，
# 后面的搜索点等于白搜了。先给每个点分一个名额，合并后路线上的结果才会铺开。
PER_CENTER_LIMIT = 4

# 同时向高德发出几个请求。
#
# 为什么值得并发：这一步最多要查 10 个位置，串行时实测每个约 1.6 秒，
# 一共要等 15 秒以上 —— 前端就超时了，用户也要盯着转圈。
#
# 为什么是 3 而不是 10：高德的个人 Key 有并发（QPS）限制，一次全发出去可能被限流。
# 实测 3 个并发时 6 个中心全部成功，耗时从 9.36 秒降到 3.64 秒；
# 按每个请求 1.6 秒算，3 个并发的实际速率约 2 次/秒，留了安全余量。
# 如果哪天看到 CUQPS_HAS_EXCEEDED_THE_LIMIT，把这个数字调小即可。
FOOD_WORKERS = 3


def _pick_centers(stops, path):
    """挑出用来搜索餐厅的中心点：景点本身 + 沿路线等距采样点。

    为什么要有采样这一步：高德只有"某个坐标周围的餐厅"，没有"这条线沿途的餐厅"。
    所以"沿途"必须由我们自己定义成一个具体动作 —— 沿着路线取若干个中心点，
    各自搜一圈，再去重合并。搜索中心选得好不好，直接决定结果像不像"沿途"。

    为什么景点也要各搜一遍：用户最可能吃饭的地方就是景点附近。

    采样个数按路线总长度决定：大约三公里取一个点，最少 3 个、最多 10 个。
    上限是硬约束，因为每个点都要发一次请求。
    """
    centers = []

    def add(lng, lat, name=""):
        # 已经有一个中心离得很近，就不重复搜了
        for exist in centers:
            if _distance_meters(exist[0], exist[1], lng, lat) < CENTER_MERGE_M:
                return
        centers.append((lng, lat, name))

    for stop in stops or []:
        add(float(stop["lng"]), float(stop["lat"]), stop.get("name") or "")

    if len(path) >= 2:
        total = 0.0
        for index in range(len(path) - 1):
            total += _distance_meters(
                path[index][0], path[index][1], path[index + 1][0], path[index + 1][1]
            )

        wanted = max(3, min(MAX_FOOD_CENTERS, int(total / 3000) + 1))
        step = max(1, len(path) // wanted)

        for index in range(0, len(path), step):
            add(path[index][0], path[index][1])

        # 终点一定要搜，那是最后一个景点所在的位置
        add(path[-1][0], path[-1][1])

    return centers[:MAX_FOOD_CENTERS]


def _food_item(poi):
    """把一条餐饮兴趣点整理成前端要用的字段。"""
    lng, lat = _split_location(poi.get("location"))
    return {
        "id": _as_text(poi.get("id")) or _as_text(poi.get("name")),
        "name": _as_text(poi.get("name")).strip(),
        "type": _as_text(poi.get("type")).split(";")[-1],
        "address": _as_text(poi.get("address")),
        "district": _as_text(poi.get("adname")),
        "lng": lng,
        "lat": lat,
        # 高德在周边搜索里会直接给出"离搜索中心多少米"，省得我们自己算
        "distanceMeters": _to_int(poi.get("distance")),
    }


def _search_one_center(center):
    """查一个中心点周围的餐厅，返回 (结果列表, 错误)。

    这个函数会被放进线程池并发执行，所以它只依赖入参、不修改任何共享状态 ——
    合并在主线程里做。这样就不需要锁，也不会出现两个线程抢着改同一个字典的问题。
    """
    lng, lat, _name = center
    try:
        data = _request(
            "/place/around",
            {
                "location": f"{lng},{lat}",
                "types": FOOD_TYPES,
                "radius": str(FOOD_RADIUS_M),
                "offset": str(FOOD_PAGE_SIZE),
                "page": "1",
            },
        )
    except AmapError as exc:
        return [], exc

    items = []
    # 高德返回的顺序本身就是按距离由近到远，直接取前几家即可
    for poi in (data.get("pois") or [])[:PER_CENTER_LIMIT]:
        item = _food_item(poi)
        if item["name"] and item["lng"] is not None:
            items.append(item)
    return items, None


def search_food(stops, path):
    """沿途美食：沿路线取若干中心点，各自搜一圈，再合并去重。

    要说清楚一件事：所谓"沿途"是我们定义出来的，不是高德提供的能力。
    做法是在路线上等距取点、每点搜一个半径，再把结果合并。路很长时
    （例如跨一整个地级市）采样点之间会有没覆盖到的路段，所以返回值里带上
    centerCount 与 radiusMeters，让前端如实告诉用户"沿路线搜索了 N 个位置、
    每个两公里范围"，而不是假装搜遍了全程。
    """
    centers = _pick_centers(stops, path)
    if not centers:
        raise AmapError("没有可用来搜索的路线点", "NO_CENTERS")

    merged = {}
    errors = []

    # 并发查所有中心；合并放在主线程做，所以不需要加锁
    with ThreadPoolExecutor(max_workers=FOOD_WORKERS) as pool:
        for items, error in pool.map(_search_one_center, centers):
            if error is not None:
                # 一个中心搜不到不该让整次搜索失败，记下来继续处理其他中心
                print(f"[amap] 沿途中点搜索失败：{error.message}")
                errors.append(error)
                continue

            for item in items:
                exist = merged.get(item["id"])
                # 同一家店可能同时落在两个搜索圆里，保留离路线更近的那次记录
                if exist is None or item["distanceMeters"] < exist["distanceMeters"]:
                    merged[item["id"]] = item

    if not merged and errors:
        # 所有中心都失败了，把第一个错误抛上去，让前端看到真正的原因
        raise errors[0]

    items = sorted(merged.values(), key=lambda item: item["distanceMeters"])

    return {
        "centerCount": len(centers),
        "radiusMeters": FOOD_RADIUS_M,
        "list": items[:FOOD_MAX_RESULTS],
    }
