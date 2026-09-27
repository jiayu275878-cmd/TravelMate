"""后端 Key 自检脚本（排查工具，不是业务代码）。

作用：确认 backend/.env 里的「Web 服务 Key」能正常请求高德接口。
用法：在 backend 目录下执行

    .\.venv\Scripts\python.exe check_key.py

为什么先做这一步：Key 类型不对、Key 没启用、配额用完这三类问题，
如果留到业务代码里排查，报错会淹没在你自己的代码里。先用一个最小的请求把它们排除掉，
之后再出问题，就基本只可能是自己的代码写错了。
"""

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("AMAP_WEB_SERVICE_KEY", "").strip()

# 用广州做测试。天气接口只认行政区编码，不认经纬度，所以这里用城市编码 440100。
TEST_ADCODE = "440100"

# 高德的错误代码 → 人话。Day 1 最容易遇到的几种情况都在这里。
ERROR_HINTS = {
    "INVALID_USER_KEY": "Key 不正确或没启用。检查是否复制完整，以及控制台里这个 Key 是不是「Web服务」类型。",
    "USERKEY_PLAT_NOMATCH": "Key 的平台类型不对：这个接口要用「Web服务」Key，不是「Web端(JS API)」Key。",
    "SERVICE_NOT_AVAILABLE": "这个 Key 没有开通该服务，去控制台检查它是否勾选了对应服务。",
    "DAILY_QUERY_OVER_LIMIT": "今天的调用量已经用完，明天再试，或去控制台查看配额。",
    "INVALID_USER_SCODE": "这是安全密钥相关的错误，属于 JS API 才会遇到的提示；在这里看到它说明 Key 类型用错了。",
}


def main() -> int:
    if not KEY:
        print("没有读到 AMAP_WEB_SERVICE_KEY。")
        print("请打开 backend/.env，把那行改成 AMAP_WEB_SERVICE_KEY=你的Web服务Key，保存后重新运行本脚本。")
        return 1

    # 只打印头尾几位，既能确认填对了，又不会把完整密钥留在终端记录里。
    print(f"读到 Key：{KEY[:4]}...{KEY[-4:]}（长度 {len(KEY)}）")

    try:
        resp = requests.get(
            "https://restapi.amap.com/v3/weather/weatherInfo",
            params={"city": TEST_ADCODE, "key": KEY, "extensions": "base"},
            timeout=10,
        )
    except requests.RequestException as exc:
        print(f"请求发不出去：{exc}")
        print("先确认网络是否正常；如果开了代理，检查代理是否放行了对高德的访问。")
        return 1

    data = resp.json()
    info = str(data.get("info", ""))

    if data.get("status") != "1":
        print(f"高德拒绝了这次请求：{data.get('infocode')} {info}")
        print(ERROR_HINTS.get(info, "这个错误代码没有收录，把这行输出发给我，我们一起查。"))
        return 1

    live = data["lives"][0]
    print("Key 可用。高德返回的广州天气：")
    print(
        f"  {live['province']} {live['city']} | {live['weather']} | 气温 {live['temperature']}℃ | "
        f"{live['winddirection']}风 {live['windpower']} 级 | 湿度 {live['humidity']}% | 更新于 {live['reporttime']}"
    )
    print("后端这一类 Key 验证通过，接着去验证前端的地图 Key。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
