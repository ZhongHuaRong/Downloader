import asyncio
import base64
from datetime import date
import html
import math
import re
import threading
import time
from urllib.parse import urldefrag, urljoin, urlsplit
import uuid

from PyQt5.QtCore import QThread, pyqtSignal

from Network.M3u8Playlist import attributes, master_playlist, request_headers


MAX_TEXT = 2 * 1024 * 1024
HEADERS = {'referer', 'origin', 'user-agent', 'cookie', 'authorization'}


def published_date(value):
    match = re.search(r'(\d{4})\s*[-/.年]\s*(\d{1,2})\s*[-/.月]\s*(\d{1,2})', value or '')
    if not match:
        return ''
    try:
        return date(*map(int, match.groups())).isoformat()
    except ValueError:
        return ''


def media_kind(url, mime=''):
    path = urlsplit(url).path.lower()
    mime = mime.split(';', 1)[0].strip().lower()
    if path.endswith('.m3u8') or mime in ('application/vnd.apple.mpegurl', 'application/x-mpegurl',
                                        'audio/mpegurl', 'audio/x-mpegurl'):
        return 'm3u8'
    if path.endswith('.mp4') or (mime == 'video/mp4' and not path.endswith(('.m4s', '.ts'))):
        return 'mp4'
    return ''


class VideoResources:
    def __init__(self, source):
        self.source = source
        self.items = {}
        self.links = {}
        self.children = {}
        self.referenced = set()
        self.renditions = set()
        self.origins = {}
        self.requests = {}
        self.agent = ''

    def add(self, url, base='', kind='', status=None, headers=None, frame=None):
        try:
            url = urldefrag(urljoin(base, url.strip()))[0]
            parsed = urlsplit(url)
            if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                return None
        except ValueError:
            return None
        kind = kind or media_kind(url)
        if kind not in ('m3u8', 'mp4'):
            return None
        item = self.items.setdefault(url, {'url':url, 'kind':kind, 'headers':{}, 'status':None,
                                          'frames':set(), 'duration':0, 'variants':[], 'parsed':False,
                                          'preview':'', 'score':0, 'references':set()})
        item['kind'] = kind
        if status is not None:
            item['status'] = status
        if headers:
            item['headers'].update({key.lower():str(value) for key, value in headers.items()
                                    if key.lower() in HEADERS})
        if frame is not None:
            item['frames'].add(frame)
        return item

    def scan(self, text, base):
        text = html.unescape(text)
        text = re.sub(r'\\(?:u([\da-fA-F]{4})|x([\da-fA-F]{2}))',
                      lambda match: chr(int(match[1] or match[2], 16)), text).replace(r'\/', '/')
        for value in re.findall(r'''["']([^"'<>\s]+)["']''', text):
            self.add(value, base)
        for match in re.finditer(r'''https?://[^\s"'<>\\]+''', text):
            self.add(match[0], base)

    def link(self, parent, child):
        self.links.setdefault(parent, set()).add(child)
        self.links.setdefault(child, set()).add(parent)
        self.children.setdefault(parent, set()).add(child)

    def playlist(self, url, text):
        item = self.items[url]
        master = master_playlist(text, url)
        item.update(parsed=True, variants=master['variants'])
        for variant in master['variants']:
            self.link(url, variant['url'])
            self.add(variant['url'], kind='m3u8')
        for audio in master['audio']:
            self.renditions.add(audio['url'])
            self.link(url, audio['url'])
        duration = 0
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('#EXTINF:'):
                try:
                    seconds = float(line.split(':', 1)[1].split(',', 1)[0])
                    if math.isfinite(seconds) and seconds > 0:
                        duration += seconds
                except ValueError:
                    pass
            elif line.startswith(('#EXT-X-MAP:', '#EXT-X-KEY:')):
                uri = attributes(line).get('URI')
                if uri:
                    self.referenced.add(urljoin(url, uri))
                    item['references'].add(urljoin(url, uri))
            elif line and not line.startswith('#') and not master['variants']:
                self.referenced.add(urljoin(url, line))
                item['references'].add(urljoin(url, line))
        if '#EXT-X-ENDLIST' in text:
            item['duration'] = duration

    def related(self, url):
        group, pending = set(), [url]
        while pending:
            current = pending.pop()
            if current not in group:
                group.add(current)
                pending.extend(self.links.get(current, ()))
        return group

    def match_player(self, frame, player, blob_count):
        source = urldefrag(player['src'])[0]
        if source in self.items and source not in self.referenced:
            return self.related(source)
        duration = player.get('duration')
        if not source.startswith('blob:') or blob_count != 1 or not duration:
            return set()
        matches = set()
        for url, item in self.items.items():
            if item['kind'] != 'm3u8' or frame not in item['frames'] or not item['parsed']:
                continue
            group = frozenset(self.related(url))
            if any(self.items.get(member, {}).get('duration') and
                   abs(self.items[member]['duration'] - duration) <= max(1, duration * 0.02)
                   for member in group):
                matches.add(group)
        return set(matches.pop()) if len(matches) == 1 else set()

    def groups(self):
        seen, result = set(), []
        for url, item in list(self.items.items()):
            if url in seen or url in self.referenced or url in self.renditions:
                continue
            group = self.related(url)
            seen.update(group)
            members = [self.items[key] for key in group if key in self.items]
            valid = [value for value in members if value['status'] is None or 200 <= value['status'] < 300]
            if not valid:
                continue
            masters = [value for value in valid if value['variants']]
            roots = [value for value in masters if not any(value['url'] in children
                     for parent, children in self.children.items() if parent in group)]
            root = (roots or masters or valid)[0]
            choices = sorted(root['variants'], key=lambda value:(value['height'],value['bandwidth']), reverse=True)
            if not choices:
                choices = [{'url':root['url'], 'label':'默认清晰度', 'width':0, 'height':0}]
            preview = max(members, key=lambda value:value['score'])
            headers = dict(root['headers'])
            headers.setdefault('user-agent', self.agent)
            headers.setdefault('referer', self.source)
            origin_headers = {}
            references = set().union(*(member['references'] for member in members))
            for address in group | references:
                origin = '{0.scheme}://{0.netloc}'.format(urlsplit(address)).lower()
                if origin in self.origins:
                    origin_headers[origin] = dict(self.origins[origin])
                if address in self.requests:
                    origin_headers.setdefault(origin,{}).update(self.requests[address])
            url_headers = {member['url']:member['headers'] for member in members if member['headers']}
            result.append({'id':str(uuid.uuid5(uuid.NAMESPACE_URL, root['url'])), 'kind':root['kind'],
                           'url':root['url'], 'variantUrl':choices[0]['url'], 'variants':choices,
                           'duration':max(value['duration'] for value in members),
                           'headers':headers, 'headerOrigins':origin_headers, 'headerUrl':root['url'],
                           'headerUrls':url_headers,
                           'sourceUrl':self.source, 'preview':preview['preview'], 'previewBusy':False})
        return result


class VideoBrowser(QThread):
    updated = pyqtSignal(object)
    status = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, url, proxy, visible=False, storage=None, parent=None):
        super().__init__(parent)
        self.url = url
        self.proxy = proxy
        self.visible = visible
        self.storage = storage
        self._finish = threading.Event()

    def finish(self):
        self._finish.set()

    def run(self):
        try:
            asyncio.run(self._run())
        except ImportError:
            self.failed.emit('网页识别需要 Playwright，请执行 python.exe -m pip install playwright')
        except Exception as error:
            self.failed.emit('网页识别失败：' + str(error)[:500])

    async def _run(self):
        from playwright.async_api import async_playwright
        async with async_playwright() as playwright:
            job = asyncio.create_task(self._browse(playwright))
            try:
                while not job.done():
                    if self.isInterruptionRequested():
                        job.cancel()
                        break
                    await asyncio.sleep(0.1)
                await job
            except asyncio.CancelledError:
                pass

    async def _browse(self, playwright):
        from playwright.async_api import Error
        browser = None
        for channel in ('msedge', 'chrome', None):
            try:
                options = {'headless':not self.visible, 'timeout':12000,
                           'args':['--autoplay-policy=no-user-gesture-required']}
                if channel:
                    options['channel'] = channel
                if self.proxy:
                    options['proxy'] = self.proxy
                else:
                    options['args'].append('--no-proxy-server')
                browser = await playwright.chromium.launch(**options)
                break
            except Error:
                continue
        if browser is None:
            raise RuntimeError('未找到 Edge / Chrome，请安装浏览器或执行 python.exe -m playwright install chromium')
        pending = set()
        try:
            context = await browser.new_context(viewport={'width':1200, 'height':800},
                                                accept_downloads=False, storage_state=self.storage)
            context.set_default_timeout(1500)
            collector = VideoResources(self.url)
            page = await context.new_page()
            collector.agent = await page.evaluate('navigator.userAgent')
            metadata = {'title':'', 'date':'', 'rawDate':''}

            async def response_received(response):
                try:
                    request = response.request
                    mime = response.headers.get('content-type', '')
                    headers = await request.all_headers()
                    try:
                        frame = request.frame
                    except Error:
                        frame = None
                    kind = media_kind(response.url, mime)
                    if kind:
                        collector.add(response.url, kind=kind, status=response.status, headers=headers, frame=frame)
                    if request.resource_type in ('media','xhr','fetch') or kind:
                        origin = '{0.scheme}://{0.netloc}'.format(urlsplit(response.url)).lower()
                        if len(collector.requests) < 2000:
                            collector.requests[response.url] = {key:value for key,value in headers.items() if key in HEADERS}
                    length = int(response.headers.get('content-length', '0') or '0')
                    small_text = any(value in mime for value in ('text/html','javascript','json','text/plain'))
                    if not 200 <= response.status < 300 or length > MAX_TEXT or not (kind == 'm3u8' or small_text):
                        return
                    body = await asyncio.wait_for(response.body(), 5)
                    if len(body) > MAX_TEXT:
                        return
                    text = body.decode('utf-8-sig', errors='replace')
                    if text.lstrip().startswith('#EXTM3U'):
                        collector.add(response.url, kind='m3u8', status=response.status, headers=headers, frame=frame)
                        collector.playlist(response.url, text)
                    else:
                        collector.scan(text, response.url)
                except (Error, ValueError, asyncio.TimeoutError):
                    pass

            def schedule(response):
                task = asyncio.create_task(response_received(response))
                pending.add(task)
                task.add_done_callback(pending.discard)
            context.on('response', schedule)
            self.status.emit('正在检查网页和播放器配置')
            try:
                response = await context.request.get(self.url, timeout=10000)
                if response.ok and int(response.headers.get('content-length', '0') or '0') <= MAX_TEXT:
                    body = await response.body()
                    if len(body) <= MAX_TEXT:
                        collector.scan(body.decode('utf-8', errors='replace'), response.url)
                await response.dispose()
            except (Error, ValueError):
                pass
            try:
                await page.goto(self.url, wait_until='domcontentloaded', timeout=20000)
            except Error:
                pass
            if self.visible:
                self.status.emit('浏览器已打开；播放视频后点击“完成识别”，也可以取消')
            else:
                self.status.emit('正在尝试播放并识别视频')
            started = time.monotonic()
            resolved = set()
            last_publish = 0
            while not self._finish.is_set() and time.monotonic() - started < (60 if self.visible else 12):
                if page.is_closed():
                    break
                elapsed = time.monotonic() - started
                if elapsed < 5:
                    await self._play(page, Error)
                metadata = await self._metadata(page, metadata, Error)
                await self._resolve(context, collector, resolved, Error,started + (60 if self.visible else 12))
                if time.monotonic() - last_publish > 1:
                    await self._capture(context, collector, Error)
                    await self._cookies(context, collector, Error)
                    self.updated.emit({'resources':collector.groups(), **metadata})
                    last_publish = time.monotonic()
                if not self.visible and elapsed > 5 and any(item['parsed'] for item in collector.items.values()):
                    break
                await asyncio.sleep(0.3)
            if pending:
                await asyncio.wait(pending, timeout=2)
            await self._capture(context, collector, Error)
            await self._cookies(context, collector, Error)
            try:
                storage = await context.storage_state()
            except Error:
                storage = self.storage
            self.updated.emit({'resources':collector.groups(), **metadata, 'storage':storage})
        finally:
            for task in list(pending):
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            await browser.close()

    async def _resolve(self, context, collector, resolved, error_type, deadline):
        inspected = 0
        for url, item in list(collector.items.items()):
            if self._finish.is_set() or time.monotonic() >= deadline or inspected >= 4:
                break
            if item['kind'] != 'm3u8' or item['parsed'] or url in resolved or len(resolved) >= 32:
                continue
            resolved.add(url)
            inspected += 1
            try:
                options = {'headers':item['headers'], 'headerUrl':url, 'sourceUrl':self.url}
                response = await context.request.get(url, headers=request_headers(options,url),timeout=max(100,int(min(5,deadline-time.monotonic())*1000)))
                collector.add(url,kind='m3u8',status=response.status)
                if response.ok and int(response.headers.get('content-length','0') or '0') <= MAX_TEXT:
                    body = await response.body()
                    if len(body) <= MAX_TEXT:
                        final = response.url
                        collector.add(final,kind='m3u8',status=response.status,headers=item['headers'])
                        if final != url:
                            collector.link(url,final)
                        collector.playlist(final,body.decode('utf-8-sig'))
                await response.dispose()
            except (error_type,ValueError):
                pass

    async def _cookies(self, context, collector, error_type):
        addresses = list(collector.items) + list(collector.referenced)
        origins = {}
        for address in addresses:
            origin = '{0.scheme}://{0.netloc}'.format(urlsplit(address)).lower()
            origins.setdefault(origin,address)
        for origin, address in origins.items():
            try:
                cookies = await context.cookies([address])
            except error_type:
                return
            headers = dict(collector.origins.get(origin,{}))
            headers.setdefault('user-agent',collector.agent)
            if cookies:
                headers['cookie'] = '; '.join(item['name']+'='+item['value'] for item in cookies)
            collector.origins[origin] = headers

    async def _metadata(self, page, previous, error_type):
        try:
            values = await page.evaluate('''() => {
                const text = selector => (document.querySelector(selector)?.textContent || '').trim().replace(/\\s+/g,' ');
                const meta = selector => document.querySelector(selector)?.content || '';
                let structured = {};
                const visit = value => {
                    if (!value || typeof value !== 'object') return;
                    if (Array.isArray(value)) {value.forEach(visit); return;}
                    if ([].concat(value['@type'] || []).includes('VideoObject') && !structured.name) structured=value;
                    if (value['@graph']) visit(value['@graph']);
                    for (const key of ['video','mainEntity','subjectOf']) if (value[key]) visit(value[key]);
                };
                document.querySelectorAll('script[type="application/ld+json"]').forEach(node => {try {visit(JSON.parse(node.textContent));} catch (error) {}});
                return {
                    title: text('#dle-content article.page .page__header h1') || structured.name || meta('meta[property="og:title"]') || text('article h1') || text('h1') || document.title,
                    rawDate: text('#dle-content article.page .page__meta-item--date') || structured.uploadDate || structured.datePublished || meta('meta[property="article:published_time"]') || document.querySelector('time[datetime]')?.dateTime || ''
                };
            }''')
            return {'title':re.sub(r'\s+', ' ', str(values['title'])).strip(),
                    'date':published_date(values['rawDate']), 'rawDate':str(values['rawDate'])}
        except error_type:
            return previous

    async def _play(self, page, error_type):
        allowed = {page.main_frame}
        for frame in page.frames:
            try:
                if frame != page.main_frame:
                    element = await frame.frame_element()
                    scoped = await element.evaluate('node => !!node.closest(".page__player, [class*=player], [id*=player]")')
                    if scoped or frame.parent_frame in allowed and frame.parent_frame != page.main_frame:
                        allowed.add(frame)
                    elif not await page.locator('.page__player, [class*=player], [id*=player], video').count():
                        allowed.add(frame)
                if frame not in allowed:
                    continue
                playing = await frame.evaluate('''() => {
                    const root = document.querySelector('#dle-content article.page .page__player') || document.querySelector('.page__player') || document;
                    root.querySelectorAll('video').forEach(video => {
                        video.muted=true; video.playsInline=true;
                        if (video.paused) video.play().catch(() => {});
                    });
                    return [...root.querySelectorAll('video')].some(video => !video.paused);
                }''')
                if playing:
                    continue
                root = frame.locator('#dle-content article.page .page__player, .page__player').first
                scope = root if await root.count() else frame
                buttons = scope.locator('button[aria-label="播放"], button[aria-label="Play"], .vjs-big-play-button, .jw-display-icon-container, [data-plyr="play"]')
                for index in range(min(await buttons.count(),2)):
                    button = buttons.nth(index)
                    if await button.is_visible():
                        await button.click(timeout=500, no_wait_after=True)
            except error_type:
                continue

    async def _capture(self, context, collector, error_type):
        for page in context.pages:
            for frame in page.frames:
                try:
                    videos = frame.locator('video')
                    players = await videos.evaluate_all('''videos => videos.map(video => ({
                        src:video.currentSrc || video.src || (video.querySelectorAll('source').length === 1 ? video.querySelector('source').src : ''),
                        poster:video.poster, duration:Number.isFinite(video.duration) ? video.duration : null,
                        ready:video.readyState, time:video.currentTime
                    }))''')
                    blob_count = sum(player['src'].startswith('blob:') for player in players)
                    for index, player in enumerate(players):
                        group = collector.match_player(frame,player,blob_count)
                        members = [collector.items[url] for url in group if url in collector.items]
                        if not members:
                            continue
                        score = 2 if player['ready'] >= 2 and player['time'] >= 0.1 else 1
                        if score == 1 and (not player['poster'] or player['ready'] >= 2):
                            continue
                        if all(item['score'] >= score for item in members):
                            continue
                        video = videos.nth(index)
                        content = await video.screenshot(type='jpeg', quality=65, timeout=1500)
                        if await video.evaluate('video => video.currentSrc || video.src || (video.querySelector("source") || {}).src || ""') != player['src']:
                            continue
                        preview = 'data:image/jpeg;base64,' + base64.b64encode(content).decode('ascii')
                        for item in members:
                            if score >= item['score']:
                                item.update(preview=preview,score=score,duration=item['duration'] or player['duration'] or 0)
                except error_type:
                    continue
