#
import sys
import logging
from PyQt5.Qt import QApplication, Qt, QUrl
from PyQt5.QtQml import QQmlApplicationEngine, qmlRegisterType
from Core.SettingsManager import SettingsManager
from Core.Compress import Compress
from Network.HttpsDownloader import HttpsDownloader
from Network.DownloaderManager import DownloaderManager
from Network.DownloaderAttributes import DownloaderAttributes

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    app.setOrganizationName('ZM')
    app.setApplicationName("Downloader")

    logging.basicConfig(
        filename='Downloader.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s')
    print(sys.argv)
    qmlRegisterType(
        DownloaderManager,
        "zm.pyqt.Downloader",
        1, 0,
        "DownloaderManager")
    qmlRegisterType(
        HttpsDownloader,
        "zm.pyqt.Downloader",
        1, 0,
        "HttpsDownloader")
    qmlRegisterType(
        DownloaderAttributes,
        "zm.pyqt.Downloader",
        1, 0,
        "DownloaderAttributes")
    qmlRegisterType(
        Compress,
        "zm.pyqt.Compressor",
        1, 0,
        "Compressor")
    qmlRegisterType(
        SettingsManager,
        "zm.pyqt.Setting",
        1, 0,
        "Setting")

    engine = QQmlApplicationEngine()
    engine.load(QUrl("./ui/main.qml"))
    if len(engine.rootObjects()) == 0:
        exit()
    app.exec()