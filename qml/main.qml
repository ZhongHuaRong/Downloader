import QtQuick 2.9
import QtQuick.Window 2.2
import Qt.labs.platform 1.0

Window {
    id: window
    visible: true
    width: 450
    height: 300
    title: qsTr("辣鸡")

    MainWindow{
        id:mainWindow
        anchors.fill: parent
    }

}
