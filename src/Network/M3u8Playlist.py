import re
from urllib.parse import urljoin, urlsplit


class PlaylistError(ValueError):
    pass


def attributes(line):
    return {match[1]: match[2].strip('"') for match in re.finditer(
        r'([A-Z0-9-]+)=((?:"[^"]*")|[^,]*)', line.split(':', 1)[-1])}


def remote_url(base, value):
    result = urljoin(base, value)
    if urlsplit(result).scheme.lower() not in ('http', 'https'):
        raise PlaylistError('播放清单包含不支持的资源地址')
    return result


def request_headers(options, url):
    origin = '{0.scheme}://{0.netloc}'.format(urlsplit(url)).lower()
    source = options.get('headers', {})
    scoped = options.get('headerOrigins', {}).get(origin, {})
    scoped = dict(scoped, **options.get('headerUrls', {}).get(url, {}))
    original = urlsplit(options.get('headerUrl') or options.get('url', ''))
    same_origin = origin == '{0.scheme}://{0.netloc}'.format(original).lower()
    result = {}
    for name, value in source.items():
        lower = name.lower()
        if lower in ('user-agent', 'referer', 'origin') or (
                same_origin and lower in ('cookie', 'authorization')):
            result[name] = str(value)
    result.update({name: str(value) for name, value in scoped.items()
                   if name.lower() in ('user-agent', 'referer', 'origin', 'cookie', 'authorization')})
    if not any(name.lower() == 'referer' for name in result) and options.get('sourceUrl'):
        result['Referer'] = options['sourceUrl']
    return result


def master_playlist(text, url):
    lines = [line.strip() for line in text.lstrip('\ufeff').splitlines() if line.strip()]
    if not lines or lines[0] != '#EXTM3U':
        raise PlaylistError('返回内容不是有效的 m3u8 播放清单')
    variants, audio = [], []
    pending = None
    for line in lines:
        if line.startswith('#EXT-X-STREAM-INF:'):
            pending = attributes(line)
        elif line.startswith('#EXT-X-MEDIA:'):
            item = attributes(line)
            if item.get('TYPE') == 'AUDIO' and item.get('URI'):
                audio.append(dict(item, url=remote_url(url, item['URI'])))
        elif not line.startswith('#') and pending is not None:
            size = pending.get('RESOLUTION', '').split('x')
            width, height = (int(size[0]), int(size[1])) if len(size) == 2 else (0, 0)
            bandwidth = int(pending.get('BANDWIDTH', '0'))
            variants.append({'url': remote_url(url, line), 'width': width, 'height': height,
                             'bandwidth': bandwidth, 'audio': pending.get('AUDIO', ''),
                             'label': str(height) + 'p' if height else str(bandwidth // 1000) + ' kbps'})
            pending = None
    if pending is not None:
        raise PlaylistError('主播放清单缺少清晰度地址')
    return {'variants': variants, 'audio': audio}


def select_variant(master, preferred=''):
    variants = master['variants']
    if not variants:
        return None, None
    selected = next((item for item in variants if item['url'] == preferred), None)
    if selected is None:
        selected = max(variants, key=lambda item: (item['height'], item['bandwidth']))
    audio = [item for item in master['audio'] if item.get('GROUP-ID') == selected['audio']]
    audio.sort(key=lambda item: (item.get('DEFAULT') != 'YES', item.get('AUTOSELECT') != 'YES'))
    return selected, audio[0] if audio else None


class PlaylistBuilder:
    """将远程播放清单转换为只引用工作目录文件的本地清单。"""

    def __init__(self):
        self.resources = []
        self._known = {}

    def resource(self, url, role, byte_range=None):
        key = (url, role, tuple(byte_range) if byte_range else None)
        if key in self._known:
            return self._known[key]
        suffix = '.key' if role == 'key' else urlsplit(url).path.rsplit('/', 1)[-1]
        suffix = '.' + suffix.rsplit('.', 1)[-1].lower() if '.' in suffix else '.bin'
        if suffix not in ('.ts', '.m4s', '.mp4', '.aac', '.key', '.bin', '.vtt'):
            suffix = '.bin'
        index = len(self.resources)
        folder = 'keys' if role == 'key' else 'segments'
        name = folder + '/' + str(index).zfill(6) + suffix
        self.resources.append({'url': url, 'name': name, 'role': role, 'range': byte_range,
                               'done': False, 'size': 0})
        self._known[key] = name
        return name

    def media(self, text, url):
        master = master_playlist(text, url)
        if master['variants']:
            raise PlaylistError('仍然指向主清单，请选择具体清晰度')
        lines = [line.strip() for line in text.lstrip('\ufeff').splitlines() if line.strip()]
        if '#EXT-X-ENDLIST' not in lines:
            raise PlaylistError('暂不支持直播或尚未结束的播放清单')
        output = []
        byte_range = None
        previous_end = {}
        encrypted = False
        duration = 0
        count = 0
        for line in lines:
            if line.startswith(('#EXT-X-PART:', '#EXT-X-PRELOAD-HINT:', '#EXT-X-DEFINE:')):
                raise PlaylistError('播放清单包含暂不支持的 HLS 特性')
            if line.startswith('#EXT-X-KEY:'):
                item = attributes(line)
                method = item.get('METHOD', '')
                if method == 'NONE':
                    encrypted = False
                    output.append(line)
                    continue
                if method != 'AES-128' or item.get('KEYFORMAT', 'identity') != 'identity':
                    raise PlaylistError('暂不支持这种视频加密方式：' + method)
                if not item.get('URI'):
                    raise PlaylistError('加密清单缺少密钥地址')
                key = self.resource(remote_url(url, item['URI']), 'key')
                output.append(re.sub(r'URI="[^"]*"', 'URI="' + key + '"', line))
                encrypted = True
            elif line.startswith('#EXT-X-MAP:'):
                item = attributes(line)
                if not item.get('URI'):
                    raise PlaylistError('初始化片段缺少地址')
                resource_url = remote_url(url, item['URI'])
                byte_spec = self._range(item.get('BYTERANGE'), resource_url, previous_end)
                if encrypted and byte_spec:
                    raise PlaylistError('暂不支持加密的字节范围分片')
                name = self.resource(resource_url, 'init', byte_spec)
                rewritten = re.sub(r'URI="[^"]*"', 'URI="' + name + '"', line)
                output.append(re.sub(r',?BYTERANGE="[^"]*"', '', rewritten))
            elif line.startswith('#EXT-X-BYTERANGE:'):
                byte_range = line.split(':', 1)[1]
            elif line.startswith('#EXTINF:'):
                try:
                    duration += float(line.split(':', 1)[1].split(',', 1)[0])
                except ValueError:
                    raise PlaylistError('分片时长无效')
                output.append(line)
            elif not line.startswith('#'):
                resource_url = remote_url(url, line)
                byte_spec = self._range(byte_range, resource_url, previous_end)
                if encrypted and byte_spec:
                    raise PlaylistError('暂不支持加密的字节范围分片')
                output.append(self.resource(resource_url, 'segment', byte_spec))
                byte_range = None
                count += 1
            else:
                output.append(line)
        if not count:
            raise PlaylistError('播放清单没有视频分片')
        return {'text': '\n'.join(output) + '\n', 'duration': duration, 'count': count}

    @staticmethod
    def _range(value, url, previous_end):
        if not value:
            return None
        try:
            parts = value.split('@')
            length = int(parts[0])
            start = int(parts[1]) if len(parts) == 2 else previous_end[url]
            if length <= 0 or start < 0:
                raise ValueError()
        except (ValueError, KeyError):
            raise PlaylistError('字节范围分片缺少有效偏移或长度')
        previous_end[url] = start + length
        return [start, length]
