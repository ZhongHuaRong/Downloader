import QtQuick 2.9
import QtQuick.Window 2.2
import Qt.labs.platform 1.0
import zm.pyqt.Downloader 1.0

Window {
    id: window
    visible: true
    width: 640
    height: 480
    title: qsTr("辣鸡")

    MainWindow{
        id:mainWindow
        anchors.fill: parent

        onGetUrl: {
            downloader.getUrl(url)
        }
    }

    Downloader{
        id:downloader

        onDownloadProgress:{
            mainWindow.setDownProgress(receiver,total)
        }
    }

}
