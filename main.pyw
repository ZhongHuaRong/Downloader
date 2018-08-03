
import sys
import logging
import urllib
import urllib.request
from HttpsDownloader import HttpsDownloader
from DownloaderManager import DownloaderManager
from DownloaderAttributes import DownloaderAttributes
from Compress import Compress
from PyQt5.Qt import QApplication,Qt,QUrl,QNetworkRequest,QNetworkAccessManager
from PyQt5.QtQml import QQmlApplicationEngine,qmlRegisterType

def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    app.setOrganizationName("pyqt");
    app.setApplicationName("Downloader");

    logging.basicConfig(filename='Downloader.log', level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')
    print(sys.argv)
    qmlRegisterType(DownloaderManager,"zm.pyqt.Downloader",1,0,"DownloaderManager")
    qmlRegisterType(HttpsDownloader,"zm.pyqt.Downloader",1,0,"HttpsDownloader")
    qmlRegisterType(DownloaderAttributes,"zm.pyqt.DownloaderAttributes",1,0,"DownloaderAttributes")
    qmlRegisterType(Compress,"zm.pyqt.Compressor",1,0,"Compressor")

    # engine = QQmlApplicationEngine()
    # engine.load(QUrl("./qml/main.qml"))
    # if len(engine.rootObjects()) == 0:
    #     return -1
    manager = DownloaderManager()
    manager.downloadFile("https://github.com/RPCS3/rpcs3-binaries-win/releases/download/build-8cb749110f9545b06ea6e47e66a74b93a79c20d2/rpcs3-v0.0.5-7154-8cb74911_win64.7z","C:\\Users\\Administrator\\Desktop\\")

    return app.exec()

main()
