"""TravelMate 后端入口。

这一层只做三件事：接收前端的请求、校验参数、把 amap_client 取回的数据整理成前端好用的 JSON。
它不负责界面，也不负责地图渲染，那两件事都在浏览器里完成。
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from amap_client import (
    MAX_ROUTE_POINTS,
    AmapError,
    get_weather,
    plan_route,
    search_attractions,
    search_destinations,
    search_food,
)

# 把同目录下 .env 里的配置读进环境变量。
# 这样做是为了让 Key 只存在于本机配置文件里：既不写死在代码里，也不会被提交到 GitHub。
load_dotenv()

app = Flask(__name__)


def fail(code, message, status=400):
    """统一的失败返回。

    前端只需要认识一种错误形状，所以这里把"参数不对"这类失败集中成一个函数，
    免得每个接口各写一遍字典、久而久之写出四种不一样的错误格式。
    """
    return jsonify({"error": {"code": code, "message": message}}), status


@app.errorhandler(AmapError)
def handle_amap_error(error):
    """高德那边的失败也整理成同样的结构。

    状态码用 502，表示"我这边没问题，是上游服务出了问题"。
    """
    return fail(error.code, error.message, status=502)


@app.get("/api/health")
def health():
    """自检接口：前端用它确认后端是否活着，也能看出 Key 是否已经读到。"""
    return jsonify(
        {
            "ok": True,
            "hasKey": bool(os.getenv("AMAP_WEB_SERVICE_KEY")),
        }
    )


@app.get("/api/destination/search")
def destination_search():
    """目的地搜索：把用户输入的一串字，变成可以在地图上定位的候选地点。

    请求参数：
        keywords  必填，用户输入的城市或地点名，例如「广州」「广州塔」

    返回：
        {"keywords": "...", "list": [{id, name, district, adcode, lng, lat, address, source}, ...]}

    为什么把 keywords 原样返回：前端的输入框会做防抖，同一个输入可能连着发几次请求，
    响应回来的顺序不保证和发出的顺序一致。带上 keywords，前端就能判断这个结果是不是当前输入对应的。
    """
    keywords = (request.args.get("keywords") or "").strip()

    if not keywords:
        return fail("MISSING_KEYWORDS", "请给出 keywords 参数，例如 /api/destination/search?keywords=广州")

    if len(keywords) > 30:
        return fail("KEYWORDS_TOO_LONG", "关键词太长了，城市或地点名不会超过 30 个字")

    return jsonify({"keywords": keywords, "list": search_destinations(keywords)})


@app.get("/api/weather")
def weather():
    """天气查询：按行政区编码取实时天气与未来几天预报。

    请求参数：
        adcode  必填，6 位行政区编码，例如 440105

    返回：
        {"adcode", "city", "province", "live": {...} 或 null, "forecast": [{...}]}

    为什么先校验 adcode：天气接口只认行政区编码，传一个明显不对的值过去，
    高德只会回一句笼统的错误。提前拦住，前端就能收到一句能看懂的中文提示。
    """
    adcode = (request.args.get("adcode") or "").strip()

    if not adcode.isdigit() or len(adcode) != 6:
        return fail("BAD_ADCODE", "adcode 必须是 6 位数字的行政区编码，例如 440105")

    return jsonify(get_weather(adcode))


@app.get("/api/attractions")
def attractions():
    """景点搜索：在某个城市里找景点，可以带关键词细化。

    请求参数：
        adcode    必填，6 位行政区编码，决定在哪个城市里找
        keywords  可选，细化用的关键词，例如「博物馆」「塔」
        page      可选，页码，从 1 开始
        lng / lat 可选，出发地坐标；给了就按距离从近到远排序并返回距离

    返回：
        {"adcode", "keywords", "page", "pageSize", "hasMore", "list": [{...}]}
    """
    adcode = (request.args.get("adcode") or "").strip()
    if not adcode.isdigit() or len(adcode) != 6:
        return fail("BAD_ADCODE", "adcode 必须是 6 位数字的行政区编码，例如 440105")

    keywords = (request.args.get("keywords") or "").strip()
    if len(keywords) > 30:
        return fail("KEYWORDS_TOO_LONG", "关键词太长了，景点名不会超过 30 个字")

    try:
        page = int(request.args.get("page") or 1)
    except ValueError:
        page = 1
    page = max(1, page)

    # 出发地坐标是可选的：前端有就用，没有就保留高德自己的排序。
    origin = None
    raw_lng = request.args.get("lng")
    raw_lat = request.args.get("lat")
    if raw_lng and raw_lat:
        try:
            origin = (float(raw_lng), float(raw_lat))
        except ValueError:
            return fail("BAD_COORDINATE", "lng 与 lat 必须是数字，例如 lng=113.324521&lat=23.106428")

    return jsonify(search_attractions(adcode, keywords=keywords, page=page, origin=origin))


@app.post("/api/route")
def route():
    """路线规划：按顺序把多个景点连成一条路线。

    请求体（JSON）：
        {
          "mode": "driving" | "walking" | "bicycling",
          "points": [{"name": "广州塔", "lng": 113.324521, "lat": 23.106428}, ...]
        }

    返回：
        {"mode", "distance", "duration", "legs": [{from, to, distance, duration}], "path": [[lng, lat], ...]}

    为什么用 POST 而不是 GET：要传的是一串点（每个点有名字和两个坐标），
    塞进查询字符串会又长又难读，而且中文名字还得编码。POST 的请求体天生就适合放结构化的数据。
    """
    payload = request.get_json(silent=True) or {}
    mode = str(payload.get("mode") or "").strip()
    raw_points = payload.get("points")

    if mode not in ("walking", "driving", "bicycling"):
        return fail("BAD_MODE", "mode 只能是 walking、driving 或 bicycling")

    if not isinstance(raw_points, list) or len(raw_points) < 2:
        return fail("TOO_FEW_POINTS", "至少需要两个景点才能规划路线")

    if len(raw_points) > MAX_ROUTE_POINTS:
        return fail("TOO_MANY_POINTS", f"一次最多规划 {MAX_ROUTE_POINTS} 个点")

    points = []
    for item in raw_points:
        if not isinstance(item, dict):
            return fail("BAD_POINTS", "points 里的每一项都必须是包含 name、lng、lat 的对象")
        try:
            points.append(
                {
                    "name": str(item.get("name") or ""),
                    "lng": float(item["lng"]),
                    "lat": float(item["lat"]),
                }
            )
        except (KeyError, TypeError, ValueError):
            return fail("BAD_POINTS", "每个点都需要数字型的 lng 与 lat")

    return jsonify(plan_route(mode, points))

@app.post("/api/food")
def food():
    """沿途美食：沿着已经规划好的路线找餐厅。

    请求体（JSON）：
        {
          "stops": [{"name": "广州塔", "lng": 113.32, "lat": 23.10}, ...],   # 可选
          "path": [[113.32, 23.10], [113.33, 23.11], ...]                    # 路线折线，必填
        }

    返回：
        {"centerCount": 9, "radiusMeters": 2000, "list": [{id, name, type, address, distanceMeters}, ...]}

    为什么要前端把 path 再发回来：后端是无状态的，它不保存上一次请求的路线。
    让前端把折线带回来，比后端重新规划一遍路线便宜 —— 重新规划一次要多发好几次请求。
    """
    payload = request.get_json(silent=True) or {}
    raw_path = payload.get("path")
    raw_stops = payload.get("stops") or []

    if not isinstance(raw_path, list) or len(raw_path) < 2:
        return fail("BAD_PATH", "path 至少要有两个坐标点")

    # 折线点很多（长途路线可能上千个），但也不能让一个异常大的数组拖垮后端
    if len(raw_path) > 20000:
        return fail("PATH_TOO_LONG", "path 的点太多了")

    path = []
    for point in raw_path:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            return fail("BAD_PATH", "path 里每个点都要是 [经度, 纬度] 的形式")
        try:
            path.append([float(point[0]), float(point[1])])
        except (TypeError, ValueError):
            return fail("BAD_PATH", "path 里的经纬度必须是数字")

    stops = []
    if isinstance(raw_stops, list):
        for item in raw_stops:
            if not isinstance(item, dict):
                continue
            try:
                stops.append(
                    {
                        "name": str(item.get("name") or ""),
                        "lng": float(item["lng"]),
                        "lat": float(item["lat"]),
                    }
                )
            except (KeyError, TypeError, ValueError):
                continue

    return jsonify(search_food(stops, path))


if __name__ == "__main__":
    # 只监听本机，端口 5000。
    # 前端开发服务器会把 /api 开头的请求转发到这里，所以浏览器不会直接碰到这个端口。
    app.run(host="127.0.0.1", port=5000, debug=True)
