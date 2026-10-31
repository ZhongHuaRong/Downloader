import uuid

from PyQt5.QtCore import QObject, QTimer, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from Network.M3u8Playlist import PlaylistBuilder, master_playlist, request_headers, select_variant


class VideoExtractor(QObject):
    changed = pyqtSignal()

    def __init__(self, ffmpeg, parent=None):
        super().__init__(parent)
        self._ffmpeg = ffmpeg
        self._manager = QNetworkAccessManager(self)
        self._reply = None
        self._generation = 0
        self._resources = []
        self._title = ''
        self._date = ''
        self._status = ''
        self._error = ''
        self._busy = False

    @pyqtProperty('QVariantList', notify=changed)
    def resources(self):
        return self._resources

    @pyqtProperty(str, notify=changed)
    def title(self):
        return self._title

    @pyqtProperty(str, notify=changed)
    def publishedDate(self):
        return self._date

    @pyqtProperty(str, notify=changed)
    def status(self):
        return self._status

    @pyqtProperty(str, notify=changed)
    def error(self):
        return self._error

    @pyqtProperty(bool, notify=changed)
    def busy(self):
        return self._busy

    def setError(self, message):
        self._error = message
        self.changed.emit()

    @pyqtSlot()
    def cancel(self):
        self._generation += 1
        reply, self._reply = self._reply, None
        if reply:
            reply.abort()
            reply.deleteLater()
        self._busy = False
        self.changed.emit()

    def _get(self, url, callback, options=None):
        generation = self._generation
        request = QNetworkRequest(QUrl(url))
        request.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
        for name, value in request_headers(options or {}, url).items():
            request.setRawHeader(name.encode('ascii'), value.encode('utf-8'))
        reply = self._manager.get(request)
        self._reply = reply
        timer = QTimer(reply)
        timer.setSingleShot(True)
        timer.timeout.connect(reply.abort)
        timer.start(15000)
        buffer = bytearray()

        def ready():
            buffer.extend(bytes(reply.readAll()))
            if len(buffer) > 4 * 1024 * 1024:
                reply.abort()

        def finished():
            timer.stop()
            if reply is not self._reply or generation != self._generation:
                reply.deleteLater()
                return
            ready()
            self._reply = None
            status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) or 0
            final_url = reply.url().toString()
            failed = reply.error() != QNetworkReply.NoError or not 200 <= status < 300
            reply.deleteLater()
            if failed:
                self._busy = False
                self.setError('无法读取播放清单，HTTP ' + str(status))
                return
            try:
                callback(buffer.decode('utf-8-sig'), final_url)
            except (ValueError, OSError) as error:
                self._busy = False
                self.setError(str(error))

        reply.readyRead.connect(ready)
        reply.finished.connect(finished)

    @pyqtSlot(str)
    def inspectM3u8(self, url):
        self.cancel()
        self._resources = []
        self._title = ''
        self._date = ''
        self._error = ''
        self._status = '正在读取播放清单'
        self._busy = True
        self.changed.emit()

        def received(text, base):
            master = master_playlist(text, base)
            selected, audio = select_variant(master)
            variants = master['variants'] or [{'url': base, 'label': '默认清晰度', 'width': 0, 'height': 0}]
            self._resources = [{'id': str(uuid.uuid4()), 'kind': 'm3u8', 'url': base,
                                'variantUrl': selected['url'] if selected else base,
                                'variants': variants, 'duration': 0, 'preview': '', 'headers': {},
                                'sourceUrl': '', 'headerUrl': base, 'previewBusy': False}]
            self._busy = False
            self._status = '已读取播放清单'
            self.changed.emit()

        self._get(url, received)

    @pyqtSlot(str, str, result='QVariantMap')
    def taskOptions(self, resource_id, variant_url):
        resource = next((item for item in self._resources if item['id'] == resource_id), None)
        if not resource:
            return {}
        return {'kind': resource['kind'], 'url': resource['url'], 'variantUrl': variant_url,
                'sourceUrl': resource.get('sourceUrl', ''), 'headers': resource.get('headers', {}),
                'headerUrl': resource.get('headerUrl', resource['url']),
                'headerOrigins': resource.get('headerOrigins', {}),
                'title': self._title, 'publishedDate': self._date}
