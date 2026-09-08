"""
Cookie 工具函数模块
从 bilibili-web-downloader 迁移
"""

import time


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
