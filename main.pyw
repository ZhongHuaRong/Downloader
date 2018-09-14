
import sys
import logging
import urllib
import urllib.request
from HttpsDownloader import HttpsDownloader
from DownloaderManager import DownloaderManager
from DownloaderAttributes import DownloaderAttributes
from Setting import Setting
from Compress import Compress
from PyQt5.Qt import QApplication,QGuiApplication,Qt,QUrl,QNetworkRequest,QNetworkAccessManager
from PyQt5.QtQml import QQmlApplicationEngine,qmlRegisterType
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    app.setOrganizationName("pyqt");
    app.setApplicationName("Downloader");

    logging.basicConfig(filename='Downloader.log', level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')
    print(sys.argv)
    qmlRegisterType(DownloaderManager,"zm.pyqt.Downloader",1,0,"DownloaderManager")
    qmlRegisterType(HttpsDownloader,"zm.pyqt.Downloader",1,0,"HttpsDownloader")
    qmlRegisterType(DownloaderAttributes,"zm.pyqt.Downloader",1,0,"DownloaderAttributes")
    qmlRegisterType(Compress,"zm.pyqt.Compressor",1,0,"Compressor")
    qmlRegisterType(Setting,"zm.pyqt.Setting",1,0,"Setting")

    engine = QQmlApplicationEngine()
    engine.load(QUrl("./qml/main.qml"))
    if len(engine.rootObjects()) == 0:
        return -1
    return app.exec()

main()
