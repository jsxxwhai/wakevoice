"""Built-in skill: launch applications and open websites."""
from __future__ import annotations

import os
import subprocess

from .base import Skill


def _launch_app(name, ctx):
    name_l = name.lower()
    sites = {
        '百度': 'https://www.baidu.com',
        '谷歌': 'https://www.google.com',
        '谷歌翻译': 'https://translate.google.com',
        '哔哩哔哩': 'https://www.bilibili.com',
        'b站': 'https://www.bilibili.com',
        'bilibili': 'https://www.bilibili.com',
        '淘宝': 'https://www.taobao.com',
        '京东': 'https://www.jd.com',
        '拼多多': 'https://www.pinduoduo.com',
        '知乎': 'https://www.zhihu.com',
        '微博': 'https://weibo.com',
        '抖音': 'https://www.douyin.com',
        '快手': 'https://www.kuaishou.com',
        '小红书': 'https://www.xiaohongshu.com',
        '豆瓣': 'https://www.douban.com',
        '腾讯视频': 'https://v.qq.com',
        '优酷': 'https://www.youku.com',
        '爱奇艺': 'https://www.iqiyi.com',
        '网易云音乐': 'https://music.163.com',
        '网易云': 'https://music.163.com',
        'qq音乐': 'https://y.qq.com',
        '百度地图': 'https://map.baidu.com',
        '高德地图': 'https://www.amap.com',
        '高德': 'https://www.amap.com',
        '百度百科': 'https://baike.baidu.com',
        '维基百科': 'https://www.wikipedia.org',
        'wikipedia': 'https://www.wikipedia.org',
        '百度翻译': 'https://fanyi.baidu.com',
        '有道翻译': 'https://fanyi.youdao.com',
        '有道': 'https://fanyi.youdao.com',
        '今日头条': 'https://www.toutiao.com',
        '头条': 'https://www.toutiao.com',
        '腾讯新闻': 'https://news.qq.com',
        'github': 'https://github.com',
        'stackoverflow': 'https://stackoverflow.com',
    }
    for key, url in sorted(sites.items(), key=lambda kv: len(kv[0]), reverse=True):
        if key.lower() in name_l:
            import webbrowser
            webbrowser.open(url)
            return '已打开 ' + key
    exes = {
        '记事本': ['notepad.exe'],
        '计算器': ['calc.exe'],
        '画图': ['mspaint.exe'],
        '资源管理器': ['explorer.exe'],
        '文件资源管理器': ['explorer.exe'],
        '控制面板': ['control.exe'],
        '浏览器': ['msedge.exe', 'chrome.exe', 'firefox.exe'],
        'edge': ['msedge.exe'],
        'chrome': ['chrome.exe'],
        '谷歌浏览器': ['chrome.exe'],
        '微信': ['WeChat.exe'],
        'qq': ['QQ.exe'],
        '命令提示符': ['cmd.exe'],
        'cmd': ['cmd.exe'],
        'powershell': ['powershell.exe'],
        'vscode': ['code'],
        '终端': ['wt.exe', 'cmd.exe'],
        'terminal': ['wt.exe', 'cmd.exe'],
    }
    for key, cmds in sorted(exes.items(), key=lambda kv: len(kv[0]), reverse=True):
        if key.lower() in name_l:
            for c in cmds:
                try:
                    if os.name == 'nt':
                        subprocess.Popen(c, shell=True)
                    else:
                        subprocess.Popen(c.split())
                    return '已启动 ' + key
                except Exception:
                    continue
            return '启动 ' + key + ' 失败'
    return '我不确定怎么打开 ' + name + '（可尝试说“打开 网址 或 应用名”）'

def open_app_skill():
    import re
    pat = re.compile(r'(?:打开|启动|运行|帮我开)\s*(?P<target>.+)')
    def handler(params, ctx):
        return _launch_app(params.get('target', params.get('text', '')), ctx)
    return Skill(
        name='open_app',
        description='打开软件、网站或系统工具（如记事本、计算器、百度）',
        patterns=[pat],
        keywords=['打开', '启动', '运行'],
        handler=handler,
    )
