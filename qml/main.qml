import QtQuick 2.9
import QtQuick.Window 2.2
import Qt.labs.platform 1.0
import zm.pyqt.Setting 1.0
import Qt.labs.settings 1.0

Window {
    id: window
    visible: true
    width: 450
    height: 600
    color:"#ffffff"
    title: qsTr("辣鸡")

    onVisibilityChanged: {
        if(window.visibility == Window.Minimized){
            window.hide()
        }
    }

    onClosing:{
        if(settings.exitDirectly){
            close.accepted = true
            return
        }
        close.accepted = false
        window.hide()
    }

    Setting{
        id:setting
    }

    Settings {
        id:settings
        property bool exitDirectly:false
        property alias windowX:window.x
        property alias windowY:window.y
        property alias windowW:window.width
        property alias windowH:window.height
    }

    SystemTrayIcon{
        id:trayIcon
        visible: true
        iconSource: "../app.ico"

        onActivated: {
            switch(reason){
            case SystemTrayIcon.Unknown:
                break;
            case SystemTrayIcon.Context:
                menu.open()
                break;
            case SystemTrayIcon.DoubleClick:
                break;
            case SystemTrayIcon.Trigger:
                window.show()
                window.raise()
                window.requestActivate()
                break;
            case SystemTrayIcon.MiddleClick:
                break;
            }
        }

        menu: Menu {
            MenuItem{
                text:qsTr("显示主面板")
                onTriggered: window.show()
            }

            MenuItem{
                text:qsTr("开始全部任务")
            }

            MenuItem{
                text:qsTr("暂停所有任务")
            }

            MenuItem {
                text: qsTr("退出")
                onTriggered: Qt.quit()
            }
        }
    }

    MainWindow{
        id:mainWindow
        anchors.fill:parent
    }

}
