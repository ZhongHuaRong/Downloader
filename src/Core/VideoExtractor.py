import uuid

from PyQt5.QtCore import QCoreApplication, QObject, QTimer, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkProxy, QNetworkReply, QNetworkRequest

from Core.VideoBrowser import VideoBrowser
from Core.VideoPreview import VideoPreview
from Network.M3u8Playlist import master_playlist, request_headers, select_variant


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
        self._manual = False
        self._source = ''
        self._raw_date = ''
        self._storage = None
        self._worker = None
        self._workers = set()
        self._preview_jobs = {}
        self._preview_queue = []
        self._preview_tried = set()
        QCoreApplication.instance().aboutToQuit.connect(self.shutdown)

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
    def rawPublishedDate(self):
        return self._raw_date

    @pyqtProperty(bool, notify=changed)
    def manual(self):
        return self._manual

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
        self._preview_queue.clear()
        self._preview_tried.clear()
        for job in list(self._preview_jobs):
            job.cancel()
        for resource in self._resources:
            resource['previewBusy'] = False
        if self._worker:
            self._worker.requestInterruption()
            self._worker = None
        reply, self._reply = self._reply, None
        if reply:
            reply.abort()
            reply.deleteLater()
        self._busy = False
        self._manual = False
        self.changed.emit()

    @pyqtSlot(str, bool)
    def preview(self, resource_id, force=False):
        resource = next((item for item in self._resources if item['id'] == resource_id),None)
        if not resource or resource.get('previewBusy'):
            return
        if not force and (resource.get('preview') or resource_id in self._preview_tried):
            return
        self._preview_tried.add(resource_id)
        resource['previewBusy'] = True
        resource['previewError'] = ''
        self._preview_queue.append(resource_id)
        self.changed.emit()
        self._startPreviews()

    def _startPreviews(self):
        while self._preview_queue and len(self._preview_jobs) < 2:
            resource_id = self._preview_queue.pop(0)
            resource = next((item for item in self._resources if item['id'] == resource_id),None)
            if not resource:
                continue
            generation = self._generation
            job = VideoPreview(dict(resource),self._ffmpeg,self)
            self._preview_jobs[job] = resource_id
            def finished(preview,message,job=job,resource_id=resource_id,generation=generation):
                self._preview_jobs.pop(job,None)
                if generation == self._generation:
                    item = next((item for item in self._resources if item['id'] == resource_id),None)
                    if item:
                        item.update(previewBusy=False,previewError=message)
                        if preview:
                            item['preview'] = preview
                        self.changed.emit()
                job.deleteLater()
                self._startPreviews()
            job.finished.connect(finished)
            QTimer.singleShot(0,job.start)

    @pyqtSlot()
    def reset(self):
        self.cancel()
        self._source = ''
        self._resources = []
        self._title = self._date = self._raw_date = self._status = self._error = ''
        self._storage = None
        self.changed.emit()

    @pyqtSlot()
    def finishRecognition(self):
        if self._worker:
            self._worker.finish()
            self._status = '正在完成识别'
            self.changed.emit()

    @pyqtSlot()
    def shutdown(self):
        self.cancel()
        for job in list(self._preview_jobs):
            if job._process:
                job._process.waitForFinished(2000)
        for worker in list(self._workers):
            worker.requestInterruption()
        for worker in list(self._workers):
            worker.wait(5000)

    @pyqtSlot(str)
    @pyqtSlot(str, bool)
    def recognize(self, url, manual=False):
        self.cancel()
        if url != self._source:
            self._resources = []
            self._title = self._date = self._raw_date = ''
            self._storage = None
        self._source = url
        self._busy = True
        self._manual = manual
        self._error = ''
        self._status = '正在启动网页识别'
        proxy = QNetworkProxy.applicationProxy()
        options = {}
        if proxy.type() != QNetworkProxy.NoProxy and proxy.hostName():
            options['server'] = ('socks5' if proxy.type() == QNetworkProxy.Socks5Proxy else 'http') + '://' + proxy.hostName() + ':' + str(proxy.port())
            if proxy.user():
                options.update(username=proxy.user(), password=proxy.password())
        worker = VideoBrowser(url,options,manual,self._storage,self)
        self._worker = worker
        self._workers.add(worker)
        generation = self._generation

        def updated(data):
            if generation != self._generation:
                return
            resources = data['resources']
            # 主清单晚于子清单出现时保留条目身份，避免覆盖已经填写的名称。
            for item in resources:
                addresses = {item['url']} | {value['url'] for value in item['variants']}
                previous = next((old for old in self._resources if addresses &
                                 ({old['url']} | {value['url'] for value in old['variants']})),None)
                if previous:
                    item['id'] = previous['id']
                    if previous.get('preview') and not item.get('preview'):
                        item['preview'] = previous['preview']
                item['previewBusy'] = previous.get('previewBusy',False) if previous else False
                item['previewError'] = previous.get('previewError','') if previous and not item.get('preview') else ''
            self._resources = resources
            self._title = data['title']
            self._date = data['date']
            self._raw_date = data['rawDate']
            if 'storage' in data:
                self._storage = data['storage']
            self.changed.emit()

        def status(message):
            if generation == self._generation:
                self._status = message
                self.changed.emit()

        def failed(message):
            if generation == self._generation:
                self.setError(message)

        def finished():
            self._workers.discard(worker)
            if worker is self._worker:
                self._worker = None
                self._busy = self._manual = False
                self._status = '识别完成' if self._resources else '未发现 MP4 或 m3u8，可以在浏览器中继续识别'
                self.changed.emit()
            worker.deleteLater()

        worker.updated.connect(updated)
        worker.status.connect(status)
        worker.failed.connect(failed)
        worker.finished.connect(finished)
        worker.start()
        self.changed.emit()

    def _get(self, url, callback, options=None, redirects=0):
        generation = self._generation
        request = QNetworkRequest(QUrl(url))
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.ManualRedirectPolicy)
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
            destination = reply.attribute(QNetworkRequest.RedirectionTargetAttribute)
            if destination and 300 <= status < 400:
                reply.deleteLater()
                target = QUrl(url).resolved(destination)
                if redirects >= 5 or target.scheme() not in ('http','https'):
                    self._busy = False
                    self.setError('播放清单重定向无效')
                    return
                self._get(target.toString(),callback,options,redirects+1)
                return
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
        self.reset()
        self._source = url
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
            variants = sorted(master['variants'], key=lambda item:(item['height'],item['bandwidth']),reverse=True) or [{'url': base, 'label': '默认清晰度', 'width': 0, 'height': 0}]
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
                'headerUrls': resource.get('headerUrls', {}),
                'title': self._title, 'publishedDate': self._date}
