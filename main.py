
import sys
import time
from PyQt5.QtQml import QQmlApplicationEngine,qmlRegisterType
from PyQt5.Qt import QApplication,Qt,QObject
from PyQt5.Qt import pyqtSlot,pyqtSignal
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import QNetworkAccessManager,QNetworkRequest,QNetworkReply
from PyQt5.Qt import QThread,QUrl

def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    print(sys.argv)
    qmlRegisterType(Downloader,"zm.pyqt.Downloader",1,0,"Downloader")

    engine = QQmlApplicationEngine()
    engine.load(QUrl("main.qml"))
    if len(engine.rootObjects()) == 0:
        return -1
    return app.exec()

class DownloaderThread(QThread):
    pass
    # @pyqtSlot("qint64","qint64")
    # def loadding(self,receiver,total):
    #     print("success:",receiver/total * 100,"%")

class Downloader(QObject):
    #pyqtSignal
    input = pyqtSignal(str,arguments = ["msg"])
    downloadProgress = pyqtSignal("qint64","qint64","qint64",arguments = [ "receiver" , "total" , "timeStamp" ])

    #membernew
    manager = QNetworkAccessManager()
    thread = DownloaderThread()
    
    def __init__(self,parent = None):
        QObject.__init__(self,parent)
        self.manager.setParent(self)
        self.thread.moveToThread(self.thread)
        self.thread.start()

    def __del__(self):
        if self.thread.isRunning():
            self.thread.exit()
            self.thread.wait()

    @pyqtSlot(str)
    def getUrl(self,url):
        reply = self.manager.get(QNetworkRequest(QUrl(url)))
        #reply.downloadProgress.connect(self.thread.loadding)
        reply.downloadProgress.connect(self.getTimestamp)
        print(reply)

    @pyqtSlot("qint64","qint64")
    def getTimestamp(self,receiver,total):
        #获取时间戳，因为我不知道qml如何获取，然后发射信号给qml更新界面
        now = int(time.time())
        self.downloadProgress.emit(receiver,total,now)

    @pyqtSlot()
    def success(self):
        print("xiazai wanc")

main()
