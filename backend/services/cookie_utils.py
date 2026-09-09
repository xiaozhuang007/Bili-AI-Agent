"""
Cookie 工具函数模块
从 bilibili-web-downloader 迁移

本模块是“工具箱层”：只提供纯函数，不依赖 LLM / Agent。
新增能力（2026-09-09）：
  - detect_cookie_format: 识别 4 种格式（netscape/browser_string/json/unknown）
  - parse_json_cookies / json_to_netscape: 支持 EditThisCookie 等扩展导出的 JSON 格式
  - convert_cookie_content: 任意可识别格式 → Netscape 的统一入口
  - verify_cookie_login: 实测登录态（请求 B站 nav API，纯内存零落盘）
"""

import json
import time
import urllib.request
from typing import Optional


def is_netscape_format(content: str) -> bool:
    """判断 Cookie 内容是否为 Netscape 格式"""
    return content.startswith('# Netscape') or ('\n' in content and '\t' in content.split('\n')[1])


def convert_to_netscape(cookie_str: str) -> str:
    """将浏览器格式 cookie 字符串转换为 yt-dlp 需要的 Netscape 格式"""
    lines = ['# Netscape HTTP Cookie File.']
    lines.append('# This is a generated file!  Do not edit.')
    lines.append('')

    pairs = {}
    expiration = 0

    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            k, v = item.split('=', 1)
            k = k.strip()
            v = v.strip()
            pairs[k] = v
            if k == 'bili_ticket_expires':
                try:
                    expiration = int(v)
                except ValueError:
                    pass

    if expiration == 0:
        expiration = int(time.time()) + 180 * 24 * 3600

    domain = '.bilibili.com'
    flag = 'TRUE'
    path = '/'
    secure = 'TRUE'

    for name, value in pairs.items():
        lines.append(f'{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}')

    return '\n'.join(lines) + '\n'


def analyze_cookie(content: str) -> dict:
    """分析 Netscape 格式 cookie 内容，返回详细信息"""
    key_fields = ['SESSDATA', 'bili_jct', 'DedeUserID', 'buvid3', 'buvid4']
    fields_status = {}
    cookie_count = 0
    expiration_str = None
    days_left = None

    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        cookie_count += 1
        parts = line.split('\t')
        if len(parts) >= 7:
            name = parts[5]
            if name in key_fields:
                fields_status[name] = True
            if name == 'bili_ticket_expires':
                try:
                    exp_ts = int(parts[4])
                    expiration_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(exp_ts))
                    now = time.time()
                    if exp_ts < now:
                        days_left = 0
                    else:
                        days_left = int((exp_ts - now) / 86400)
                except ValueError:
                    pass

    for field in key_fields:
        if field not in fields_status:
            fields_status[field] = False

    return {
        'cookie_count': cookie_count,
        'fields_status': fields_status,
        'expiration': expiration_str,
        'days_left': days_left,
    }


# ---------- 以下为 2026-09-09 新增：文件级检测/转换能力 ----------

def detect_cookie_format(content: str) -> str:
    """识别 cookie 内容属于哪种格式。

    Returns:
        "netscape" | "browser_string" | "json" | "unknown"
        - netscape: 7 列制表符格式（yt-dlp 直接可用）
        - browser_string: 'a=1; b=2' 分号连接（需 convert_to_netscape）
        - json: 扩展导出的 cookie 数组 [{"name":..., "value":...}]（需 json_to_netscape）
        - unknown: 无法识别的格式
    """
    # 1) 已有判断函数优先：文件头 # Netscape 或首行含制表符 → Netscape
    if is_netscape_format(content):
        return "netscape"

    stripped = content.lstrip()
    # 2) JSON 格式：以 [ 或 { 开头（扩展导出的 cookie 数组几乎都是 [）
    if stripped.startswith('[') or stripped.startswith('{'):
        try:
            data = json.loads(stripped)
            # 必须是数组且元素含 name/value 字段才算“cookie json”
            if isinstance(data, list) and data and all(isinstance(i, dict) for i in data):
                return "json"
        except json.JSONDecodeError:
            pass
        return "unknown"

    # 3) 浏览器字符串：分号分隔，且第一段形如 key=value
    first_seg = content.split(';')[0].strip()
    if '=' in first_seg and not first_seg.startswith('='):
        return "browser_string"

    return "unknown"


def parse_json_cookies(content: str) -> dict:
    """把 JSON cookie 数组解析成 {name: value} 字典。

    EditThisCookie / Cookie-Editor 导出的典型结构：
        [{"name": "SESSDATA", "value": "xxx", "domain": ".bilibili.com",
          "path": "/", "expires": 1750000000, "secure": true}, ...]
    注意：expires 可能是秒级时间戳，也可能缺失/为 0（会话级 cookie）。
    """
    data = json.loads(content)
    pairs = {}
    for item in data:
        name = item.get('name')
        value = item.get('value')
        if name:  # value 允许为空字符串，但 name 必须有
            pairs[name] = value
    return pairs


def json_to_netscape(content: str) -> str:
    """JSON cookie 数组 → Netscape 格式文本。

    与 convert_to_netscape（浏览器字符串版）不同：JSON 每条自带
    domain/expires/secure 等元信息，逐条保留更精确（而不是写死 .bilibili.com）。
    浏览器扩展导出的 domain 通常以 "." 开头（如 .bilibili.com），
    表示“适用于所有子域”，Netscape 第 2 列 flag 应为 TRUE。
    """
    lines = ['# Netscape HTTP Cookie File.']
    lines.append('# This is a generated file!  Do not edit.')
    lines.append('')

    data = json.loads(content)
    for item in data:
        name = item.get('name')
        value = item.get('value', '')
        if not name:
            continue
        # domain：缺省时兜底为 .bilibili.com（B站场景）
        domain = item.get('domain') or '.bilibili.com'
        # flag：域名以 . 开头 → 子域共享，TRUE；否则 FALSE
        flag = 'TRUE' if domain.startswith('.') else 'FALSE'
        path = item.get('path') or '/'
        secure = 'TRUE' if item.get('secure') else 'FALSE'
        # expires：0/缺失/过去时间 → 会话 cookie，Netscape 规范中过期列写 0
        expires = item.get('expires') or item.get('expirationDate') or 0
        try:
            expires = int(expires)
        except (TypeError, ValueError):
            expires = 0
        if expires < int(time.time()):
            expires = 0
        lines.append(f'{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}')

    return '\n'.join(lines) + '\n'


def convert_cookie_content(content: str) -> tuple:
    """任意可识别格式 → Netscape 格式的统一入口（供工具层调用）。

    Returns:
        (success, netscape_text_or_error, source_format)
        - success=True  时第二个元素是 Netscape 全文
        - success=False 时第二个元素是错误说明（内容本身就不是合法 cookie）
    为什么不直接抛异常：工具层要把它转成给 LLM 看的友好字符串，
    返回三元组比 try/except 更好拼报告。
    """
    fmt = detect_cookie_format(content)
    if fmt == "netscape":
        return True, content, fmt
    if fmt == "browser_string":
        return True, convert_to_netscape(content), fmt
    if fmt == "json":
        return True, json_to_netscape(content), fmt
    return False, "Unrecognized cookie format. Expected Netscape file, browser string (a=1; b=2), or JSON array.", fmt


def _extract_sessdata(netscape_text: str) -> Optional[str]:
    """从 Netscape 文本中提取 SESSDATA 的值（实测登录态时构造 Cookie 头用）。

    为什么单独提取而不是带全部 cookie：nav API 只要 SESSDATA 就能判定登录身份，
    头里带全量反而可能触发风控；且最小化泄露面。
    """
    for line in netscape_text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) >= 7 and parts[5] == 'SESSDATA':
            return parts[6]
    return None


def verify_cookie_login(content: str) -> dict:
    """实测登录态：用 cookie 请求 B站官方 nav API。

    为什么需要“实测”：字段齐全 + 未过期只能说明“格式规范”，
    但 B站可能提前注销 SESSDATA（用户实际遇到过），只有真实请求才能确认可用。
    纯内存 HTTP 请求，不写任何文件。

    Returns:
        {"ok": bool, "isLogin": bool, "uname": str|None, "mid": int|None,
         "detail": str}  detail 恒为给人看的描述文本
    """
    # 先统一转成 Netscape（无论用户给什么格式都能提取 SESSDATA）
    ok, netscape_text, _ = convert_cookie_content(content)
    if not ok:
        return {"ok": False, "isLogin": False, "uname": None, "mid": None,
                "detail": netscape_text}

    sessdata = _extract_sessdata(netscape_text)
    if not sessdata:
        return {"ok": False, "isLogin": False, "uname": None, "mid": None,
                "detail": "SESSDATA not found in cookie. Login verification skipped."}

    # nav API：登录后返回 isLogin=true + 用户信息；未登录返回 code=0, isLogin=false
    url = "https://api.bilibili.com/x/web-interface/nav"
    req = urllib.request.Request(url)
    req.add_header("Cookie", f"SESSDATA={sessdata}")
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        # 网络失败 ≠ cookie 失效，如实上报，不误判为“cookie 不可用”
        return {"ok": False, "isLogin": False, "uname": None, "mid": None,
                "detail": f"Network error while verifying: {e}"}

    d = data.get('data') or {}
    is_login = bool(d.get('isLogin'))
    if data.get('code') == 0 and is_login:
        return {"ok": True, "isLogin": True, "uname": d.get('uname'),
                "mid": d.get('mid'), "detail": "Login verified."}
    return {"ok": False, "isLogin": False, "uname": None, "mid": None,
            "detail": f"Not logged in (API message: {data.get('message', 'unknown')})."}

