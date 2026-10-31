import json
from pathlib import Path
import shutil
import threading
import time
import uuid

from PyQt5.QtCore import QObject, QProcess, QTimer, QUrl
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from Network.DownloaderAttributes import DownloaderAttributes
from Network.M3u8Playlist import PlaylistBuilder, PlaylistError, master_playlist, remote_url, request_headers, select_variant


def cleanup_workdir(parent, name, task_id=''):
    parent = Path(parent).resolve()
    work = parent / (name + '.tmp')
    if not work.is_dir() or work.resolve().parent != parent or work.resolve().name != name + '.tmp':
        return
    config = work / (name + '.tmp.cfg')
    try:
        data = json.loads(config.read_text(encoding='utf-8'))
        if data.get('kind') != 'm3u8' or data.get('name') != name:
            return
        if task_id and data.get('options', {}).get('id') != task_id:
            return
        shutil.rmtree(work)
    except (OSError, ValueError):
        return


class M3u8Downloader(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.attributes = DownloaderAttributes(DownloaderAttributes.UrlType.M3u8, self)
        self.ffmpeg = None
        self._manager = QNetworkAccessManager(self)
        self._reply = None
        self._file = None
        self._process = None
        self._generation = 0
        self._data = None
        self._work = None
        self._config = None
        self._paused = True
        self._done_bytes = 0
        self._builder = None
        self._playlists = {}
        self._audio = None

    def _state(self, state, message=''):
        self.attributes.message = message
        self.attributes.setState(state)

    def _local(self, name):
        path = (self._work / name).resolve()
        path.relative_to(self._work.resolve())
        return path

    def _save(self):
        if self._data is None or self._config is None:
            return
        pending = self._config.with_suffix('.writing')
        pending.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding='utf-8')
        pending.replace(self._config)

    def startDownload(self, isPause=False):
        self.deleteFile()
        self._paused = bool(isPause)
        self.attributes.taskName = self.attributes.fileName
        self.attributes.startTime = int(time.time())
        self.attributes.curTime = int(time.time())
        self._data = None
        self._config = None
        self._work = None
        generation = self._generation
        QTimer.singleShot(0, lambda: self._begin(generation))

    def _begin(self, generation):
        if generation != self._generation:
            return
        try:
            name = self.attributes.fileName
            if not name or Path(name).name != name or '/' in name or '\\' in name:
                raise ValueError('视频文件名无效')
            if Path(name).suffix.lower() not in ('.mkv', '.mp4'):
                raise ValueError('合并输出文件名应使用 .mkv 或 .mp4')
            parent = Path(self.attributes.path).resolve()
            parent.mkdir(parents=True, exist_ok=True)
            self._work = parent / (name + '.tmp')
            if self._work.exists() and self._work.resolve().parent != parent:
                raise ValueError('临时目录位置无效')
            self._config = self._work / (name + '.tmp.cfg')
            options = dict(self.attributes.taskOptions)
            options.setdefault('id', str(uuid.uuid4()))
            options['kind'] = 'm3u8'
            self.attributes.taskOptions = options
            if self._config.is_file():
                data = json.loads(self._config.read_text(encoding='utf-8'))
                if (data.get('kind') != 'm3u8' or data.get('name') != name
                        or data.get('url') != self.attributes.url
                        or data.get('options', {}).get('id') != options['id']):
                    raise ValueError('临时目录属于其它任务，请修改视频文件名')
                self._data = data
                self.attributes.taskOptions = data['options']
                for resource in data.get('resources', []):
                    path = self._local(resource['name'])
                    resource['done'] = bool(resource.get('done') and path.is_file()
                                            and path.stat().st_size == resource.get('size', 0)
                                            and path.stat().st_size > 0)
                self._sync_progress()
            else:
                if self._work.exists() and any(self._work.iterdir()):
                    raise ValueError('临时目录已有文件，请修改视频文件名')
                self._work.mkdir(exist_ok=True)
                self._data = {'version': 1, 'kind': 'm3u8', 'name': name, 'url': self.attributes.url,
                              'options': options, 'stage': 'resolving', 'resources': [], 'playlists': {}}
                self._save()
            if self._paused:
                self._state(DownloaderAttributes.States.pause, '任务已暂停')
                return
            self._continue()
        except (OSError, ValueError, KeyError) as error:
            self._fail(str(error))

    def _continue(self):
        if not self.ffmpeg or not self.ffmpeg.ready:
            self._fail('请先在设置中检测 FFmpeg')
            return
        self._paused = False
        if self._data.get('resources') and self._data.get('playlists'):
            for name, text in self._data['playlists'].items():
                self._local(name).write_text(text, encoding='utf-8')
            self._next_resource()
        else:
            self._builder = PlaylistBuilder()
            self._playlists = {}
            self._audio = None
            self._state(DownloaderAttributes.States.resolving, '正在读取播放清单')
            self._request(self.attributes.url, lambda text, url: self._video_playlist(text, url, 0))

    def _request(self, url, callback, resource=None, attempt=0, redirects=0):
        if self._paused:
            return
        generation = self._generation
        request = QNetworkRequest(QUrl(url))
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.ManualRedirectPolicy)
        for name, value in request_headers(self.attributes.taskOptions, url).items():
            if '\r' in value or '\n' in value:
                self._fail('请求头包含无效字符')
                return
            request.setRawHeader(name.encode('ascii'), value.encode('utf-8'))
        if resource and resource.get('range'):
            start, length = resource['range']
            request.setRawHeader(b'Range', f'bytes={start}-{start + length - 1}'.encode())
        try:
            if resource:
                destination = self._local(resource['name'] + '.tmp')
                destination.parent.mkdir(parents=True, exist_ok=True)
                self._file = destination.open('wb')
        except OSError as error:
            self._fail('无法写入分片：' + str(error))
            return
        reply = self._manager.get(request)
        self._reply = reply
        reply.setReadBufferSize(256 * 1024)
        data = bytearray()
        problem = []
        timer = QTimer(reply)
        timer.setSingleShot(True)

        def expire():
            problem.append('网络请求超时')
            reply.abort()

        def ready():
            if reply is not self._reply or generation != self._generation:
                return
            timer.start(20000)
            chunk = bytes(reply.readAll())
            try:
                status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) or 0
                if 300 <= status < 400:
                    return
                if resource and resource.get('range') and status != 206:
                    raise ValueError('服务器不支持该分片的字节范围请求')
                if status >= 400:
                    return
                if resource:
                    self._file.write(chunk)
                    self.attributes.curProgress = self._done_bytes + self._file.tell()
                    self.attributes.curTime = int(time.time())
                else:
                    data.extend(chunk)
                    if len(data) > 4 * 1024 * 1024:
                        raise ValueError('播放清单过大')
            except (OSError, ValueError) as error:
                problem.append(str(error))
                reply.abort()

        def progress(received, total):
            if reply is self._reply and generation == self._generation and resource:
                self.attributes.total = self._done_bytes + max(0, total)

        def finished():
            timer.stop()
            if reply is not self._reply or generation != self._generation:
                reply.deleteLater()
                return
            ready()
            self._reply = None
            if self._file:
                self._file.close()
                self._file = None
            status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) or 0
            destination = reply.attribute(QNetworkRequest.RedirectionTargetAttribute)
            if destination and 300 <= status < 400:
                reply.deleteLater()
                try:
                    if redirects >= 5:
                        raise ValueError('资源重定向过多')
                    self._request(remote_url(url,destination.toString()),callback,resource,attempt,redirects+1)
                except ValueError as error:
                    self._fail(str(error))
                return
            if resource and resource.get('range') and status == 206:
                start, length = resource['range']
                expected = f'bytes {start}-{start + length - 1}/'.encode()
                if not bytes(reply.rawHeader(b'Content-Range')).startswith(expected):
                    problem.append('服务器返回的分片字节范围不正确')
            failed = bool(problem or reply.error() != QNetworkReply.NoError or not 200 <= status < 300)
            final_url = reply.url().toString()
            reply.deleteLater()
            if failed:
                if attempt < 2 and not self._paused:
                    QTimer.singleShot(500 * (attempt + 1), lambda: self._request(url, callback, resource, attempt + 1)
                                      if generation == self._generation and not self._paused else None)
                else:
                    self._fail(problem[-1] if problem else '下载失败，HTTP ' + str(status))
                return
            try:
                if resource:
                    path = self._local(resource['name'] + '.tmp')
                    size = path.stat().st_size
                    if size <= 0 or (resource.get('range') and size != resource['range'][1]):
                        raise ValueError('分片内容不完整')
                    if resource['role'] == 'key' and size != 16:
                        raise ValueError('AES-128 密钥长度无效')
                    path.replace(self._local(resource['name']))
                    resource.update(done=True, size=size)
                    self._save()
                    self._sync_progress()
                    callback()
                else:
                    callback(data.decode('utf-8-sig'), final_url)
            except (OSError, ValueError, KeyError) as error:
                self._fail(str(error))

        timer.timeout.connect(expire)
        reply.readyRead.connect(ready)
        reply.downloadProgress.connect(progress)
        reply.finished.connect(finished)
        timer.start(20000)

    def _video_playlist(self, text, url, depth):
        master = master_playlist(text, url)
        selected, audio = select_variant(master, self.attributes.taskOptions.get('variantUrl', ''))
        if selected:
            if depth >= 5:
                raise PlaylistError('播放清单嵌套层级过多')
            if audio:
                self._audio = audio['url']
            self._request(selected['url'], lambda body, base: self._video_playlist(body, base, depth + 1))
            return
        self._playlists['video.m3u8'] = self._builder.media(text, url)['text']
        self._playlists['original.m3u8'] = text
        if self._audio:
            self._request(self._audio, self._audio_playlist)
        else:
            self._playlists['local.m3u8'] = self._playlists['video.m3u8']
            self._resolved()

    def _audio_playlist(self, text, url):
        self._playlists['audio.m3u8'] = self._builder.media(text, url)['text']
        self._playlists['local.m3u8'] = (
            '#EXTM3U\n#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="audio",DEFAULT=YES,'
            'AUTOSELECT=YES,URI="audio.m3u8"\n#EXT-X-STREAM-INF:BANDWIDTH=1000000,AUDIO="audio"\nvideo.m3u8\n')
        self._resolved()

    def _resolved(self):
        self._data.update(resources=self._builder.resources, playlists=self._playlists, stage='downloading')
        for name, text in self._playlists.items():
            self._local(name).write_text(text, encoding='utf-8')
        self._save()
        self._sync_progress()
        self._next_resource()

    def _sync_progress(self):
        resources = self._data.get('resources', [])
        segments = [item for item in resources if item['role'] == 'segment']
        self.attributes.setTotalFile(len(segments))
        self.attributes.setFinishFile(sum(bool(item.get('done')) for item in segments))
        self._done_bytes = sum(item.get('size', 0) for item in resources if item.get('done'))
        self.attributes.curProgress = self._done_bytes
        self.attributes.preProgress = self._done_bytes
        self.attributes.total = self._done_bytes
        self.attributes.curTime = int(time.time())

    def _next_resource(self):
        if self._paused:
            return
        pending = next((item for item in self._data['resources'] if not item['done']), None)
        if pending is None:
            self._merge()
            return
        self._state(DownloaderAttributes.States.downloading, '正在下载视频分片')
        self._request(pending['url'], self._next_resource, pending)

    def _merge(self):
        try:
            process = self.ffmpeg.createProcess(self)
            output = self._local('merge.part' + Path(self.attributes.fileName).suffix)
            args = ['-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-protocol_whitelist',
                    'file,crypto,data', '-allowed_extensions', 'ALL', '-i', str(self._local('local.m3u8')),
                    '-map', '0:v:0?', '-map', '0:a:0?', '-c', 'copy', str(output)]
            process.setArguments(args)
            process.setProcessChannelMode(QProcess.MergedChannels)
            self._process = process
            generation = self._generation
            messages = bytearray()

            def read():
                messages.extend(bytes(process.readAllStandardOutput()))
                if len(messages) > 16384:
                    del messages[:-16384]

            def finished(code, status):
                read()
                if process is not self._process or generation != self._generation:
                    process.deleteLater()
                    return
                self._process = None
                process.deleteLater()
                if code != 0 or status != QProcess.NormalExit or not output.is_file() or output.stat().st_size == 0:
                    self._fail('合并失败：' + messages.decode('utf-8', errors='replace')[-2000:])
                    return
                try:
                    parent = Path(self.attributes.path)
                    name = self.attributes.fileName
                    if (parent / name).exists():
                        name = self.attributes.checkFileNameAndTemp(name, str(parent))
                    output.rename(parent / name)
                    self._data['stage'] = 'complete'
                    self._save()
                    original_name = self._data['name']
                    options = dict(self.attributes.taskOptions)
                    threading.Thread(target=cleanup_workdir,
                                     args=(str(parent), original_name, options.get('id', '')),
                                     daemon=True).start()
                    self.attributes.fileName = name
                    self.attributes.taskName = name
                    self._paused = True
                    self._state(DownloaderAttributes.States.finish, '下载完成')
                except (OSError, ValueError) as error:
                    self._fail('无法保存合并结果：' + str(error))

            def failed(error):
                if process is self._process and generation == self._generation:
                    self._process = None
                    process.deleteLater()
                    self._fail('无法启动 FFmpeg')

            process.readyReadStandardOutput.connect(read)
            process.finished.connect(finished)
            process.errorOccurred.connect(failed)
            self._data['stage'] = 'merging'
            self._save()
            self._state(DownloaderAttributes.States.merging, '正在合并视频')
            if process is self._process and generation == self._generation and not self._paused:
                process.start()
        except (OSError, ValueError, RuntimeError) as error:
            self._fail(str(error))

    def _fail(self, message):
        self._paused = True
        self._state(DownloaderAttributes.States.downloadError, message)

    def pauseDown(self):
        if not self._paused:
            self.deleteFile()
            self._state(DownloaderAttributes.States.pause, '任务已暂停')
        elif self._data is None:
            self.startDownload(False)
        else:
            self._continue()

    def deleteFile(self):
        self._paused = True
        self._generation += 1
        reply, self._reply = self._reply, None
        if reply is not None:
            reply.abort()
            reply.deleteLater()
        if self._file:
            self._file.close()
            self._file = None
        process, self._process = self._process, None
        if process is not None:
            process.kill()
            process.waitForFinished(1000)
            process.deleteLater()
        if self._data is not None:
            try:
                self._save()
            except OSError:
                pass
