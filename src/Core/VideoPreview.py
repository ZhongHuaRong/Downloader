import base64
from pathlib import Path
import shutil
import tempfile
import threading
from urllib.parse import urljoin

from PyQt5.QtCore import QObject, QProcess, QTimer, QUrl, pyqtSignal
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from Network.M3u8Playlist import PlaylistBuilder, master_playlist, request_headers, select_variant


class VideoPreview(QObject):
    """通过 Qt 下载少量样本，FFmpeg 只读取本地文件，不向其它来源转发凭据。"""
    finished = pyqtSignal(str, str)

    def __init__(self, resource, ffmpeg, parent=None):
        super().__init__(parent)
        self.resource = resource
        self.ffmpeg = ffmpeg
        self._manager = QNetworkAccessManager(self)
        self._reply = None
        self._process = None
        self._work = None
        self._active = True
        self._reported = False
        self._size = 0
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(lambda:self.cancel('预览获取超时，点击图片可重试'))

    def start(self):
        if not self._active:
            return
        try:
            if not self.ffmpeg.ready:
                raise ValueError('请先在设置中检测 FFmpeg，再点击图片获取预览')
            self._work = Path(tempfile.mkdtemp(prefix='downloader-preview-'))
            self._timer.start(35000)
            if self.resource['kind'] == 'm3u8':
                self._get(self.resource['url'],lambda data,url:self._playlist(data,url,0),limit=2*1024*1024)
            else:
                self._get(self.resource['url'],self._mp4,limit=12*1024*1024,partial=True)
        except (OSError, ValueError, RuntimeError) as error:
            self._finish('',str(error))

    def _get(self,url,callback,limit=8*1024*1024,partial=False,byte_range=None,redirects=0):
        if not self._active:
            return
        request = QNetworkRequest(QUrl(url))
        # 手动跳转以重新按目标来源选择 Cookie / Authorization。
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute,QNetworkRequest.ManualRedirectPolicy)
        for name, value in request_headers(self.resource,url).items():
            if '\r' in value or '\n' in value:
                self._finish('','请求头包含无效字符')
                return
            request.setRawHeader(name.encode('ascii'),value.encode('utf-8'))
        if partial:
            request.setRawHeader(b'Range',f'bytes=0-{limit-1}'.encode())
        if byte_range:
            start, length = byte_range
            request.setRawHeader(b'Range',f'bytes={start}-{start+length-1}'.encode())
        reply = self._manager.get(request)
        self._reply = reply
        buffer = bytearray()
        capped = [False]
        timer = QTimer(reply)
        timer.setSingleShot(True)
        timer.timeout.connect(reply.abort)
        timer.start(10000)

        def ready():
            if reply is not self._reply:
                return
            chunk = bytes(reply.readAll())
            remaining = limit - len(buffer)
            buffer.extend(chunk[:remaining])
            if len(chunk) > remaining:
                capped[0] = True
                reply.abort()

        def finished():
            timer.stop()
            if reply is not self._reply or not self._active:
                reply.deleteLater()
                return
            ready()
            self._reply = None
            status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) or 0
            destination = reply.attribute(QNetworkRequest.RedirectionTargetAttribute)
            error = reply.error()
            content_range = bytes(reply.rawHeader(b'Content-Range'))
            reply.deleteLater()
            if destination and 300 <= status < 400:
                if redirects >= 5:
                    self._finish('','预览资源重定向过多')
                    return
                self._get(urljoin(url,destination.toString()),callback,limit,partial,byte_range,redirects+1)
                return
            if not 200 <= status < 300 or (error != QNetworkReply.NoError and not (partial and capped[0])):
                self._finish('','预览下载失败，点击图片可重试')
                return
            if capped[0] and not partial:
                self._finish('','预览样本过大，点击图片可重试')
                return
            if byte_range:
                start,length = byte_range
                if status != 206 or not content_range.startswith(f'bytes {start}-{start+length-1}/'.encode()) or len(buffer) != length:
                    self._finish('','预览分片的字节范围不正确')
                    return
            try:
                self._size += len(buffer)
                if self._size > 24*1024*1024:
                    raise ValueError('预览样本过大')
                callback(bytes(buffer),url)
            except (OSError,ValueError,KeyError,RuntimeError) as problem:
                self._finish('',str(problem))

        reply.readyRead.connect(ready)
        reply.finished.connect(finished)

    def _mp4(self,data,url):
        source = self._work / 'source.mp4'
        source.write_bytes(data)
        self._extract(source)

    def _playlist(self,data,url,depth):
        text = data.decode('utf-8-sig')
        master = master_playlist(text,url)
        selected,_ = select_variant(master,self.resource.get('variantUrl',''))
        if selected:
            if depth >= 5:
                raise ValueError('播放清单嵌套层级过多')
            self._get(selected['url'],lambda body,base:self._playlist(body,base,depth+1),limit=2*1024*1024)
            return
        # 保留开头的序号、密钥、IV 和初始化信息，只取两个分片供抽帧。
        lines = []
        count = 0
        for line in text.splitlines():
            line = line.strip()
            if line == '#EXT-X-ENDLIST':
                continue
            lines.append(line)
            if line and not line.startswith('#'):
                count += 1
                if count >= 2:
                    break
        lines.append('#EXT-X-ENDLIST')
        builder = PlaylistBuilder()
        local = builder.media('\n'.join(lines),url)
        (self._work / 'local.m3u8').write_text(local['text'],encoding='utf-8')
        resources = iter(builder.resources)

        def next_resource():
            resource = next(resources,None)
            if resource is None:
                self._extract(self._work / 'local.m3u8')
                return
            def saved(body,base):
                if resource['role'] == 'key' and len(body) != 16:
                    raise ValueError('预览密钥长度无效')
                path = self._work / resource['name']
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(body)
                next_resource()
            self._get(resource['url'],saved,byte_range=resource.get('range'))
        next_resource()

    def _extract(self,source):
        if not self._active:
            return
        process = self.ffmpeg.createProcess(self)
        arguments = ['-hide_banner','-loglevel','error','-nostdin','-protocol_whitelist','file,crypto,data']
        if source.suffix == '.m3u8':
            arguments += ['-allowed_extensions','ALL']
        process.setArguments(arguments + ['-i',str(source),
                              '-an','-vf','thumbnail=10,scale=320:-2','-frames:v','1','-f','image2pipe',
                              '-c:v','mjpeg','pipe:1'])
        self._process = process
        output = bytearray()
        def read():
            output.extend(bytes(process.readAllStandardOutput()))
        def finished(code,status):
            read()
            if process is not self._process:
                process.deleteLater()
                return
            self._process = None
            process.deleteLater()
            if self._active and code == 0 and status == QProcess.NormalExit and output.startswith(b'\xff\xd8'):
                self._finish('data:image/jpeg;base64,'+base64.b64encode(output).decode('ascii'),'')
            else:
                self._finish('','暂无预览，点击图片可重试')
        def failed(error):
            if process is self._process and error == QProcess.FailedToStart:
                self._process = None
                process.deleteLater()
                self._finish('','无法启动 FFmpeg 预览')
        process.readyReadStandardOutput.connect(read)
        process.finished.connect(finished)
        process.errorOccurred.connect(failed)
        process.start()

    def cancel(self,message=''):
        if not self._active:
            return
        self._active = False
        self._timer.stop()
        reply,self._reply = self._reply,None
        if reply:
            reply.abort()
            reply.deleteLater()
        if self._process:
            # finished 回调收到进程退出后再清理，避免 Windows 文件占用。
            self._process.kill()
        else:
            self._finish('',message)

    def _finish(self,preview,message):
        if self._reported:
            return
        self._reported = True
        self._active = False
        self._timer.stop()
        if self._work:
            path,self._work = self._work,None
            threading.Thread(target=shutil.rmtree,args=(path,),kwargs={'ignore_errors':True},daemon=True).start()
        self.finished.emit(preview,message)
