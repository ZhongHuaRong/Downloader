import logging
import time

from PyQt5.QtCore import QCoreApplication, QObject, QTimer, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkProxy, QNetworkReply, QNetworkRequest

from Core.VideoBrowser import VideoBrowser, VideoResources, error_summary, log_url
from Core.VideoPreview import VideoPreview
from Network.M3u8Playlist import master_playlist, request_headers, select_variant


class VideoExtractor(QObject):
    changed = pyqtSignal()

    def __init__(self, ffmpeg, parent=None):
        super().__init__(parent)
        self._ffmpeg = ffmpeg
        self._manager = QNetworkAccessManager(self)
        self._replies = set()
        self._inspections = set()
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
        if message and message != self._error:
            logging.warning('[视频识别] %s',error_summary(message))
        self._error = message
        self.changed.emit()

    @pyqtSlot()
    def cancel(self):
        if self._busy:
            logging.info('[视频识别] 已取消%s','浏览器中识别' if self._manual else '识别')
        self._generation += 1
        self._preview_queue.clear()
        self._preview_tried.clear()
        for job in list(self._preview_jobs):
            job.cancel()
        for resource in self._resources:
            resource['previewBusy'] = False
            for variant in resource['variants']:
                variant['counting'] = False
        if self._worker:
            self._worker.requestInterruption()
            self._worker = None
        replies, self._replies = self._replies, set()
        self._inspections.clear()
        for reply in replies:
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
                        if message:
                            logging.warning('[视频预览] 获取失败：%s；%s',log_url(item['url']),error_summary(message))
                        else:
                            logging.info('[视频预览] 已生成预览：%s',log_url(item['url']))
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
            logging.info('[视频识别] 用户完成浏览器中识别，正在整理结果')
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
        started = time.monotonic()
        logging.info('[视频识别] 开始%s：%s','浏览器中识别' if manual else '自动识别',log_url(url))
        proxy = QNetworkProxy.applicationProxy()
        options = {}
        if proxy.type() != QNetworkProxy.NoProxy and proxy.hostName():
            options['server'] = ('socks5' if proxy.type() == QNetworkProxy.Socks5Proxy else 'http') + '://' + proxy.hostName() + ':' + str(proxy.port())
            if proxy.user():
                options.update(username=proxy.user(), password=proxy.password())
        logging.info('[视频识别] 网络：%s',options.get('server','直连'))
        worker = VideoBrowser(url,options,manual,self._storage,self)
        self._worker = worker
        self._workers.add(worker)
        generation = self._generation
        summary = None

        def updated(data):
            nonlocal summary
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
                    old_variants = {value['url']:value for value in previous['variants']}
                    for variant in item['variants']:
                        old = old_variants.get(variant['url'],{})
                        if variant.get('segmentCount',-1) < 0 and old.get('segmentCount',-1) >= 0:
                            variant.update(segmentCount=old['segmentCount'],duration=old.get('duration',0))
                        variant['counting'] = (item['id'],variant['url']) in self._inspections
                item['previewBusy'] = previous.get('previewBusy',False) if previous else False
                item['previewError'] = previous.get('previewError','') if previous and not item.get('preview') else ''
            self._resources = resources
            self._title = data['title']
            self._date = data['date']
            self._raw_date = data['rawDate']
            if 'storage' in data:
                self._storage = data['storage']
            current = tuple((item['kind'],item['url'],len(item['variants'])) for item in resources)
            if current != summary:
                summary = current
                logging.info('[视频识别] 已发现 %d 组资源（m3u8：%d，MP4：%d）',len(resources),
                             sum(item['kind']=='m3u8' for item in resources),sum(item['kind']=='mp4' for item in resources))
            self.changed.emit()

        def status(message):
            if generation == self._generation:
                self._status = message
                logging.info('[视频识别] %s',message)
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
                logging.info('[视频识别] 识别结束：%d 组资源，耗时 %.1f 秒，标题%s，发布日期%s',
                             len(self._resources),time.monotonic()-started,
                             '已获取' if self._title else '未获取',self._date or '未获取')
                self.changed.emit()
            worker.deleteLater()

        worker.updated.connect(updated)
        worker.status.connect(status)
        worker.failed.connect(failed)
        worker.finished.connect(finished)
        worker.start()
        self.changed.emit()

    def _get(self, url, callback, options=None, redirects=0, on_error=None):
        generation = self._generation
        request = QNetworkRequest(QUrl(url))
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.ManualRedirectPolicy)
        for name, value in request_headers(options or {}, url).items():
            request.setRawHeader(name.encode('ascii'), value.encode('utf-8'))
        reply = self._manager.get(request)
        self._replies.add(reply)
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
            if reply not in self._replies or generation != self._generation:
                reply.deleteLater()
                return
            ready()
            self._replies.discard(reply)
            status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) or 0
            final_url = reply.url().toString()
            destination = reply.attribute(QNetworkRequest.RedirectionTargetAttribute)
            if destination and 300 <= status < 400:
                reply.deleteLater()
                target = QUrl(url).resolved(destination)
                if redirects >= 5 or target.scheme() not in ('http','https'):
                    report_error('播放清单重定向无效')
                    return
                self._get(target.toString(),callback,options,redirects+1,on_error)
                return
            failed = reply.error() != QNetworkReply.NoError or not 200 <= status < 300
            reason = reply.errorString()
            reply.deleteLater()
            if failed:
                report_error('无法读取播放清单，HTTP ' + str(status) + '：' + reason)
                return
            try:
                callback(buffer.decode('utf-8-sig'), final_url)
            except (ValueError, OSError) as error:
                report_error(str(error))

        def report_error(message):
            if on_error:
                on_error(message)
            else:
                self._busy = False
                self.setError(message)

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
        logging.info('[m3u8] 读取播放清单：%s',log_url(url))
        self.changed.emit()

        def received(text, base):
            collector = VideoResources('')
            collector.add(base,kind='m3u8',status=200)
            collector.playlist(base,text)
            self._resources = collector.groups()
            if not self._resources:
                raise ValueError('清单没有可识别的视频')
            self._busy = False
            self._status = '已读取播放清单'
            logging.info('[m3u8] 已读取播放清单，%d 个清晰度',len(self._resources[0]['variants']))
            self.changed.emit()
            resource = self._resources[0]
            self.inspectVariant(resource['id'],resource['variantUrl'])

        self._get(url, received)

    @pyqtSlot(str, str)
    def inspectVariant(self, resource_id, variant_url):
        resource = next((item for item in self._resources if item['id']==resource_id),None)
        if not resource or resource['kind'] != 'm3u8':
            return
        variant = next((item for item in resource['variants'] if item['url']==variant_url),None)
        key = (resource_id,variant_url)
        if not variant or variant.get('segmentCount',-1) >= 0 or key in self._inspections:
            return
        self._inspections.add(key)
        variant.update(counting=True,countError='')
        logging.info('[m3u8] 统计视频分片：%s',log_url(variant_url))
        self.changed.emit()

        def apply(stats, error=''):
            self._inspections.discard(key)
            current = next((item for item in self._resources if item['id']==resource_id),None)
            if not current:
                return
            for value in current['variants']:
                if value['url']==variant_url:
                    value.update(stats,counting=False,countError=error)
            if error:
                logging.warning('[m3u8] 分片数量未获取：%s；%s',log_url(variant_url),error_summary(error))
            else:
                logging.info('[m3u8] 视频分片：%s；数量：%s',log_url(variant_url),stats['segmentCount'])
            self.changed.emit()

        def received(text, base, depth=0):
            master = master_playlist(text,base)
            selected,_ = select_variant(master)
            if selected:
                if depth >= 5:
                    raise ValueError('播放清单嵌套层级过多')
                self._get(selected['url'],lambda body,url:received(body,url,depth+1),resource,on_error=failed)
                return
            collector = VideoResources('')
            collector.add(base,kind='m3u8',status=200)
            collector.playlist(base,text)
            stats = collector.statistics(base)
            if stats['segmentCount'] < 0:
                raise ValueError('播放清单尚未结束，分片数量不固定')
            apply(stats)

        def failed(message):
            apply({'segmentCount':-1},message)

        self._get(variant_url,received,resource,on_error=failed)

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
