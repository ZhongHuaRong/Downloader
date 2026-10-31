from PyQt5.Qt import QObject, pyqtSlot, pyqtProperty
from Network.DownloaderAttributes import DownloaderAttributes
from Network.HttpsDownloader import HttpsDownloader
from Network.M3u8Downloader import M3u8Downloader


class DownloaderManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._http = HttpsDownloader(self)
        self._m3u8 = M3u8Downloader(self)
        self._active = None
        self._ffmpeg = None

    @pyqtProperty(QObject)
    def ffmpeg(self):
        return self._ffmpeg

    @ffmpeg.setter
    def ffmpeg(self, value):
        self._ffmpeg = value
        self._m3u8.ffmpeg = value

    @pyqtSlot(str)
    def setPath(self, value):
        self._http.attributes.path = value
        self._m3u8.attributes.path = value

    @pyqtSlot(str)
    def setUrl(self, value):
        self._http.attributes.url = value.strip()
        self._m3u8.attributes.url = value.strip()

    @pyqtSlot(int)
    def setFileTotal(self, value):
        self._http.attributes.setTotalFile(value)
        self._m3u8.attributes.setTotalFile(value)

    @pyqtSlot(str)
    def setFileName(self, value):
        self._http.attributes.fileName = value
        self._m3u8.attributes.fileName = value

    @pyqtSlot('QVariantMap')
    def setTaskOptions(self, value):
        self._http.attributes.taskOptions = value
        self._m3u8.attributes.taskOptions = value

    @pyqtSlot(bool, result=DownloaderAttributes)
    def downloadFile(self, isPause):
        options = self._http.attributes.taskOptions
        self._active = self._m3u8 if options.get('kind') == 'm3u8' else self._http
        self._active.startDownload(isPause)
        return self._active.attributes

    @pyqtSlot()
    def pauseDown(self):
        if self._active:
            self._active.pauseDown()

    @pyqtSlot()
    def deleteFile(self):
        if self._active:
            self._active.deleteFile()
