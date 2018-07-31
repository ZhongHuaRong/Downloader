
import sys
import logging
from Downloader import Downloader
from Compress import Compress
from PyQt5.Qt import QApplication,Qt,QUrl
from PyQt5.QtQml import QQmlApplicationEngine,qmlRegisterType

def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    app.setOrganizationName("pyqt");
    app.setApplicationName("Downloader");

    logging.basicConfig(filename='Downloader.log', level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')
    print(sys.argv)
    qmlRegisterType(Downloader,"zm.pyqt.Downloader",1,0,"Downloader")
    qmlRegisterType(Compress,"zm.pyqt.Compressor",1,0,"Compressor")

    engine = QQmlApplicationEngine()
    engine.load(QUrl("./qml/main.qml"))
    if len(engine.rootObjects()) == 0:
        return -1
    return app.exec()

main()
