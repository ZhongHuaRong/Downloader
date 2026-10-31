"""网页媒体地址探测，网址在本机输入。

安装：python.exe -m pip install playwright
运行：python.exe probe_video.py
仅检查网页源码：python.exe probe_video.py --static-only
可选保存结果：python.exe probe_video.py --output C:\\Temp\\video_probe.json

默认打开独立浏览器窗口，手动点击播放后监听 60 秒。
结果是候选媒体地址，只输出地址，不保存视频分片或执行解密、合并。
"""

import argparse
import html
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.request import ProxyHandler, Request, build_opener


MAX_TEXT = 2 * 1024 * 1024
USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
              'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')


def media_kind(url, content_type=''):
    mime = content_type.split(';', 1)[0].strip().lower()
    if mime in ('application/vnd.apple.mpegurl', 'application/x-mpegurl',
                'audio/mpegurl', 'audio/x-mpegurl'):
        return 'M3U8'
    if mime == 'application/dash+xml':
        return 'DASH'
    path = urlsplit(url).path.lower()
    for suffix, kind in [('.m3u8', 'M3U8'), ('.mpd', 'DASH'), ('.mp4', 'MP4'),
                         ('.mkv', 'MKV'), ('.webm', 'WebM'), ('.m4v', 'M4V')]:
        if path.endswith(suffix):
            return kind
    if not path.endswith(('.ts', '.m4s', '.aac', '.vtt', '.key')) and mime.startswith('video/'):
        if mime not in ('video/mp2t', 'video/iso.segment'):
            return mime
    return ''


class MediaCollector:
    def __init__(self):
        self.items = {}

    def add(self, url, source, base='', kind='', status=None, headers=None):
        try:
            url = urldefrag(urljoin(base, url.strip()))[0]
            parsed = urlsplit(url)
        except ValueError:
            return
        if parsed.scheme.lower() not in ('http', 'https') or not parsed.netloc:
            return
        kind = kind or media_kind(url)
        if not kind:
            return
        first = url not in self.items
        item = self.items.setdefault(url, {
            'type': kind, 'url': url, 'sources': [], 'status': None, 'headers': {},
        })
        status_changed = status is not None and status != item['status']
        if source not in item['sources']:
            item['sources'].append(source)
        item['type'] = kind
        if status is not None:
            item['status'] = status
        if headers:
            item['headers'].update({name.lower(): value for name, value in headers.items()
                                    if name.lower() in ('referer', 'origin', 'user-agent',
                                                        'cookie', 'authorization')})
        if first or status_changed:
            state = f'，HTTP {status}' if status is not None else ''
            print(f'\n[{kind}] {source}{state}\n{url}', flush=True)

    def scan(self, text, base, source):
        text = re.sub(r'&(?:amp|quot|apos|lt|gt|#\d+|#x[\da-fA-F]+);',
                      lambda match: html.unescape(match.group()), text)
        text = re.sub(r'\\(?:u([\da-fA-F]{4})|x([\da-fA-F]{2}))',
                      lambda match: chr(int(match.group(1) or match.group(2), 16)), text)
        text = text.replace(r'\/', '/')
        # Separate passes keep complete, signed URLs intact, including their query strings.
        for value in re.findall(r'''["']([^"'<>\s]+)["']''', text):
            self.add(value, source, base)
        for match in re.finditer(r'''https?://[^\s"'<>\\]+''', text):
            self.add(match.group(), source, base)


def inspect_page(url, collector, proxy=''):
    print('先检查网页源码和播放器配置...', flush=True)
    opener = build_opener(ProxyHandler({'http': proxy, 'https': proxy})) if proxy else build_opener()
    try:
        with opener.open(Request(url, headers={'User-Agent': USER_AGENT}), timeout=15) as response:
            final_url = response.geturl()
            mime = response.headers.get('Content-Type', '')
            kind = media_kind(final_url, mime)
            if kind:
                collector.add(final_url, '直接响应', kind=kind, status=response.status)
            if mime.lower().startswith('video/') or (kind and kind not in ('M3U8', 'DASH')):
                return
            if mime.split(';', 1)[0].lower() == 'application/octet-stream':
                return
            raw = response.read(MAX_TEXT)
            text = raw.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')
            if text.lstrip('\ufeff \r\n\t').startswith('#EXTM3U'):
                collector.add(final_url, '播放列表内容', kind='M3U8', status=response.status)
            elif re.search(r'<(?:\w+:)?MPD(?:\s|>)', text):
                collector.add(final_url, '播放列表内容', kind='DASH', status=response.status)
            collector.scan(text, final_url, '网页候选')
    except (HTTPError, URLError, OSError, ValueError) as error:
        print(f'静态读取未成功：{error}；浏览器仍可继续尝试。', flush=True)


def watch_browser(args, collector):
    try:
        from playwright.sync_api import Error, TimeoutError, sync_playwright
    except ImportError:
        print('\n浏览器探测需要安装：python.exe -m pip install playwright')
        return False

    with sync_playwright() as playwright:
        browser = None
        channels = ['msedge', 'chrome', None] if os.name == 'nt' else [None, 'chrome']
        for channel in channels:
            options = {'headless': args.headless}
            if channel:
                options['channel'] = channel
            if args.proxy:
                options['proxy'] = {'server': args.proxy}
            try:
                browser = playwright.chromium.launch(**options)
                print(f'使用浏览器：{channel or "Chromium"}', flush=True)
                break
            except Error:
                continue
        if browser is None:
            print('没有可启动的浏览器，请执行：python.exe -m playwright install chromium')
            return False

        context = browser.new_context()

        def request_headers(request):
            try:
                return request.all_headers()
            except Error:
                return request.headers

        def on_request(request):
            if media_kind(request.url):
                collector.add(request.url, '浏览器请求', headers=request_headers(request))

        def on_response(response):
            kind = media_kind(response.url, response.headers.get('content-type', ''))
            if kind:
                collector.add(response.url, '浏览器响应', kind=kind, status=response.status,
                              headers=request_headers(response.request))

        def on_finished(request):
            if request.resource_type not in ('document', 'xhr', 'fetch'):
                return
            try:
                response = request.response()
                if response is None or response.status >= 400:
                    return
                mime = response.headers.get('content-type', '').lower()
                if not (mime.startswith('text/') or 'json' in mime or 'mpegurl' in mime
                        or 'dash+xml' in mime):
                    return
                if int(response.headers.get('content-length', '0')) > MAX_TEXT:
                    return
                body = response.body()
                if len(body) > MAX_TEXT:
                    return
                text = body.decode('utf-8', errors='replace')
                if text.lstrip('\ufeff \r\n\t').startswith('#EXTM3U'):
                    collector.add(response.url, '播放列表内容', kind='M3U8', status=response.status,
                                  headers=request_headers(request))
                elif re.search(r'<(?:\w+:)?MPD(?:\s|>)', text):
                    collector.add(response.url, '播放列表内容', kind='DASH', status=response.status,
                                  headers=request_headers(request))
                else:
                    collector.scan(text, response.url, '页面／接口候选')
            except (Error, ValueError):
                pass

        context.on('request', on_request)
        context.on('response', on_response)
        context.on('requestfinished', on_finished)
        page = context.new_page()
        print(f'请在打开的窗口中点击播放，监听 {args.wait:g} 秒；关闭窗口可提前结束。', flush=True)
        try:
            try:
                page.goto(args.url, wait_until='domcontentloaded', timeout=30000)
            except TimeoutError:
                print('页面加载超时，继续监听已打开的页面。', flush=True)
            except Error as error:
                print(f'导航提示：{error}', flush=True)
            deadline = time.monotonic() + args.wait
            while time.monotonic() < deadline and context.pages:
                # Playwright dispatches network callbacks while its event loop is running.
                context.pages[0].wait_for_timeout(250)
        except KeyboardInterrupt:
            print('\n停止监听。')
        except Error:
            print('浏览器已关闭，结束监听。')
        finally:
            try:
                browser.close()
            except Error:
                pass
    return True


def main():
    parser = argparse.ArgumentParser(description='在本机探测网页中的媒体地址，默认打开浏览器供手动播放。')
    parser.add_argument('url', nargs='?', help='网页或媒体链接；不填写时会询问')
    parser.add_argument('--static-only', action='store_true', help='只检查网页源码，无需 Playwright')
    parser.add_argument('--headless', action='store_true', help='隐藏浏览器，适用于自动播放页面')
    parser.add_argument('--wait', type=float, default=60, help='浏览器监听秒数，默认 60')
    parser.add_argument('--proxy', default='', help='代理地址，例如 http://127.0.0.1:7890')
    parser.add_argument('--output', type=Path, help='可选：保存候选地址和实际请求头到 JSON 文件')
    args = parser.parse_args()
    if not args.url:
        try:
            args.url = input('输入要测试的网址：').strip()
        except (EOFError, KeyboardInterrupt):
            return 1
    args.url = args.url.strip().strip('"')
    try:
        parsed = urlsplit(args.url)
    except ValueError:
        parser.error('网址格式不正确')
    if parsed.scheme.lower() not in ('http', 'https') or not parsed.netloc:
        parser.error('请输入完整的 http:// 或 https:// 地址')
    if args.wait <= 0:
        parser.error('--wait 必须大于 0')
    collector = MediaCollector()
    inspect_page(args.url, collector, args.proxy)
    browser_ok = True
    if not args.static_only:
        browser_ok = watch_browser(args, collector)
    print(f'\n共找到 {len(collector.items)} 个候选地址；有 HTTP 状态的记录表示收到了响应。')
    if not collector.items:
        print('未捕获到媒体地址。可增加 --wait 的时间，并确认浏览器中已开始播放。')
    if args.output:
        try:
            args.output.write_text(json.dumps(list(collector.items.values()), ensure_ascii=False, indent=2),
                                   encoding='utf-8')
            print(f'结果已保存：{args.output}')
        except OSError as error:
            print(f'保存失败：{error}', file=sys.stderr)
            return 1
    return 0 if collector.items and browser_ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
