"""网页媒体地址探测，网址在本机输入。

安装：python.exe -m pip install playwright
运行：python.exe tools/probe_video.py
仅检查网页源码：python.exe tools/probe_video.py --static-only
可选保存结果：python.exe tools/probe_video.py --output C:\\Temp\\video_probe.json
指定预览页：python.exe tools/probe_video.py --report C:\\Temp\\video_preview.html

默认打开独立浏览器窗口，手动点击播放后监听 60 秒。
结束后打开本地预览页，显示播放器截图、时长、清晰度及候选地址。
结果用于测试资源识别，不执行视频下载、解密或合并。
"""

import argparse
import base64
import html
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import webbrowser
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
        self.frames = {}
        self.links = {}
        self.variants = {}

    def add(self, url, source, base='', kind='', status=None, headers=None, frame=None):
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
            'title': '', 'duration': None, 'width': 0, 'height': 0,
            'preview': '', 'preview_source': '', 'preview_score': 0,
            'playlist_kind': '',
        })
        if frame is not None:
            self.frames.setdefault(url, set()).add(frame)
        if url in self.variants:
            item.update(self.variants[url])
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

    def parse_playlist(self, url, text):
        item = self.items.get(url)
        if item is None:
            return
        lines = [line.strip() for line in text.lstrip('\ufeff').splitlines() if line.strip()]
        pending = None
        duration = 0
        master = False
        for line in lines:
            if line.startswith('#EXT-X-STREAM-INF:'):
                master = True
                size = re.search(r'RESOLUTION=(\d+)x(\d+)', line, re.IGNORECASE)
                pending = {'width': int(size[1]), 'height': int(size[2])} if size else {}
            elif line.startswith('#EXT-X-MEDIA:'):
                uri = re.search(r'URI="([^"]+)"', line)
                if uri:
                    child = urldefrag(urljoin(url, uri[1]))[0]
                    self.links.setdefault(url, set()).add(child)
                    self.links.setdefault(child, set()).add(url)
            elif not line.startswith('#') and pending is not None:
                child = urldefrag(urljoin(url, line))[0]
                self.links.setdefault(url, set()).add(child)
                self.links.setdefault(child, set()).add(url)
                self.variants[child] = pending
                if child in self.items:
                    self.items[child].update(pending)
                pending = None
            elif line.startswith('#EXTINF:'):
                try:
                    seconds = float(line.split(':', 1)[1].split(',', 1)[0])
                    if math.isfinite(seconds) and seconds > 0:
                        duration += seconds
                except ValueError:
                    pass
        item['playlist_kind'] = 'master' if master else 'media'
        if not master and '#EXT-X-ENDLIST' in lines and duration:
            item['duration'] = duration

    def related(self, url):
        result = set()
        pending = [url]
        while pending:
            current = pending.pop()
            if current not in result:
                result.add(current)
                pending.extend(self.links.get(current, ()))
        return result

    def match_player(self, frame, player, blob_count):
        src = urldefrag(player['src'])[0]
        if src in self.items:
            return self.related(src), '媒体地址匹配'
        # MSE 的 blob 地址只在同一页面的清单组和播放器时长能唯一匹配时关联。
        duration = player.get('duration')
        if not src.startswith('blob:') or blob_count != 1 or not duration:
            return set(), ''
        groups = set()
        for url, item in self.items.items():
            if item['type'] != 'M3U8' or frame not in self.frames.get(url, ()):
                continue
            if item['status'] is None or not 200 <= item['status'] < 300:
                continue
            group = frozenset(self.related(url))
            durations = [self.items[member]['duration'] for member in group if member in self.items]
            if any(value and abs(value - duration) <= max(1, duration * 0.02) for value in durations):
                groups.add(group)
        if len(groups) == 1:
            return set(groups.pop()), '同页唯一 HLS 清单与播放器时长匹配'
        return set(), ''


def capture_previews(context, collector, error_type):
    for page in context.pages:
        for frame in page.frames:
            try:
                videos = frame.locator('video')
                players = videos.evaluate_all('''videos => videos.map(video => ({
                    src: video.currentSrc || video.src ||
                         (video.querySelectorAll('source').length === 1 ? video.querySelector('source').src : ''),
                    poster: video.poster,
                    title: video.title || document.title,
                    duration: Number.isFinite(video.duration) ? video.duration : null,
                    width: video.videoWidth, height: video.videoHeight,
                    ready: video.readyState, time: video.currentTime
                }))''')
                blob_count = sum(player['src'].startswith('blob:') for player in players)
                for index, player in enumerate(players):
                    urls, match = collector.match_player(frame, player, blob_count)
                    members = [collector.items[url] for url in urls if url in collector.items]
                    if not members:
                        continue
                    for item in members:
                        item['title'] = player['title'] or item['title']
                        item['duration'] = item['duration'] or player['duration']
                        item['width'] = item['width'] or player['width']
                        item['height'] = item['height'] or player['height']
                    score = 2 if player['ready'] >= 2 and player['time'] >= 0.1 else 1
                    if score == 1 and (not player['poster'] or player['ready'] >= 2):
                        continue
                    if all(item['preview_score'] >= score for item in members):
                        continue
                    video = videos.nth(index)
                    box = video.bounding_box(timeout=500)
                    viewport = page.viewport_size
                    if not box or not viewport or box['width'] <= 1 or box['height'] <= 1:
                        continue
                    if (box['x'] < 0 or box['y'] < 0 or box['x'] + box['width'] > viewport['width']
                            or box['y'] + box['height'] > viewport['height']):
                        continue
                    image = page.screenshot(clip=box, type='jpeg', quality=70, timeout=1500)
                    after = video.evaluate('video => video.currentSrc || video.src || '
                                           "(video.querySelector('source') || {}).src || ''")
                    if after != player['src']:
                        continue
                    preview = 'data:image/jpeg;base64,' + base64.b64encode(image).decode('ascii')
                    source = ('播放画面' if score == 2 else '播放器封面') + ' · ' + match
                    for item in members:
                        if score >= item['preview_score']:
                            item.update(preview=preview, preview_source=source, preview_score=score)
            except error_type:
                continue


def duration_label(seconds):
    if seconds is None or not math.isfinite(seconds) or seconds < 0:
        return '时长未知'
    seconds = round(seconds)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f'{hours}:{minutes:02}:{seconds:02}' if hours else f'{minutes:02}:{seconds:02}'


def write_report(collector, path):
    cards = []
    seen = set()
    for url, item in collector.items.items():
        if url in seen:
            continue
        group = collector.related(url)
        seen.update(group)
        members = [value for key, value in collector.items.items() if key in group]
        preferred = sorted(members, key=lambda value: (
            value['playlist_kind'] != 'media', value['status'] not in (200, 206),
            -value['preview_score']))[0]
        preview = max(members, key=lambda value: value['preview_score'])
        title = (preview['title'] or preferred['title']
                 or Path(urlsplit(preferred['url']).path).name or urlsplit(url).netloc)
        escaped = html.escape
        image = ('<img src="' + escaped(preview['preview'], quote=True) + '" alt="播放器预览">'
                 if preview['preview'] else '<span>暂无预览</span>')
        source = preview['preview_source'] or '尚未匹配到对应播放器'
        choices = {}
        for value in [preferred] + members:
            label = f"{value['height']}p" if value['height'] else value['type']
            if value['playlist_kind'] == 'master':
                label = '主清单'
            elif value['playlist_kind'] == 'media' and not value['height']:
                label = '分片清单'
            state = f"HTTP {value['status']}" if value['status'] is not None else '候选地址'
            choices[value['url']] = f'{label} · {state}'
        for child, info in collector.variants.items():
            if child in group and child not in choices:
                label = f"{info['height']}p" if info.get('height') else '清晰度清单'
                choices[child] = label + ' · 尚未请求'
        options = ''.join('<option value="' + escaped(address, quote=True) + '">' + escaped(label)
                          + '</option>' for address, label in choices.items())
        urls = ''.join('<li><strong>' + escaped(label) + '</strong><code>' + escaped(address)
                       + '</code></li>' for address, label in choices.items())
        cards.append('<article><div class="preview">' + image + '<b>'
                     + duration_label(preferred['duration']) + '</b></div><div class="info"><h2>'
                     + escaped(title) + '</h2><p class="source">' + escaped(source)
                     + '</p><div class="actions"><span class="tag">' + escaped(preferred['type'])
                     + '</span><select aria-label="选择媒体地址">' + options
                     + '</select><button type="button">复制地址</button><span class="copied"></span></div>'
                     + '<details><summary>查看全部地址</summary><ul>' + urls + '</ul></details></div></article>')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'">
<title>媒体探测结果</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f5f7;color:#20242b;font:14px system-ui,sans-serif}
main{max-width:1040px;margin:30px auto;padding:0 20px}h1{font-size:24px}header p,.source{color:#626d7a}
article{display:flex;gap:18px;margin:16px 0;padding:16px;background:white;border:1px solid #e2e5e9;border-radius:12px}
.preview{width:180px;height:104px;flex-shrink:0;position:relative;background:#e9ecf0;border-radius:7px;overflow:hidden;display:grid;place-items:center;color:#65717e}
.preview img{width:100%;height:100%;object-fit:contain;background:#111}.preview b{position:absolute;right:5px;bottom:5px;background:#000b;color:white;padding:2px 5px;border-radius:4px;font-size:12px}
.info{min-width:0;flex:1}h2{margin:0 0 7px;font-size:16px;overflow-wrap:anywhere}.source{font-size:12px;margin:5px 0 12px}
.actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.tag{padding:3px 6px;background:#e6f3fc;color:#126398;border-radius:4px}
select,button{font:inherit;padding:7px 10px;border:1px solid #d0d7df;border-radius:6px}select{max-width:100%;background:white}button{background:#087fb9;color:white;border-color:#087fb9;cursor:pointer}
.copied{font-size:12px;color:#176638}details{margin-top:12px}summary{cursor:pointer;color:#526172}ul{padding-left:18px}li{margin:10px 0}code{display:block;white-space:normal;overflow-wrap:anywhere;color:#44505f;margin-top:4px}
@media(max-width:600px){article{flex-direction:column}.preview{width:100%;height:180px}main{padding:0 12px}}
</style><main><header><h1>媒体探测结果</h1><p>共 CARD_COUNT 组资源。同一主清单下的清晰度归为一组，可选择地址后复制到下载脚本。</p></header>CARDS</main>
<script>document.querySelectorAll('button').forEach(button=>button.addEventListener('click',async()=>{
const card=button.closest('article'),url=card.querySelector('select').value,label=card.querySelector('.copied');
try{await navigator.clipboard.writeText(url);label.textContent='已复制'}catch(error){
const input=document.createElement('textarea');input.value=url;document.body.append(input);input.select();
const ok=document.execCommand('copy');input.remove();label.textContent=ok?'已复制':'请展开地址手动复制'}
}));</script></html>'''
    content = ''.join(cards) or '<p>未捕获到媒体地址。请确认播放已开始，或增加监听时间。</p>'
    path.write_text(page.replace('CARD_COUNT', str(len(cards))).replace('CARDS', content), encoding='utf-8')


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
                collector.parse_playlist(final_url, text)
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

        def request_frame(request):
            try:
                return request.frame
            except Error:
                return None

        def on_request(request):
            if media_kind(request.url):
                collector.add(request.url, '浏览器请求', headers=request_headers(request),
                              frame=request_frame(request))

        def on_response(response):
            kind = media_kind(response.url, response.headers.get('content-type', ''))
            if kind:
                collector.add(response.url, '浏览器响应', kind=kind, status=response.status,
                              headers=request_headers(response.request), frame=request_frame(response.request))

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
                                  headers=request_headers(request), frame=request_frame(request))
                    collector.parse_playlist(response.url, text)
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
            next_preview = 0
            while time.monotonic() < deadline and context.pages:
                if time.monotonic() >= next_preview:
                    capture_previews(context, collector, Error)
                    next_preview = time.monotonic() + 1
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
    parser.add_argument('--report', type=Path, help='预览 HTML 保存位置，默认保存到本机临时目录')
    parser.add_argument('--no-open', action='store_true', help='生成预览页后不自动打开')
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
    report = args.report or Path(tempfile.mkdtemp(prefix='downloader-media-')) / 'index.html'
    try:
        write_report(collector, report)
        print(f'预览页已保存：{report.resolve()}')
        if not args.no_open and not args.headless:
            webbrowser.open(report.resolve().as_uri())
    except OSError as error:
        print(f'预览页保存失败：{error}', file=sys.stderr)
        return 1
    return 0 if collector.items and browser_ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
