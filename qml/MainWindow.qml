import QtQuick 2.8

Item {
    id:mainWindow

    DownloadPage{
        id:page1
        anchors.top: parent.top
        anchors.topMargin: 0
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 0
        anchors.left: parent.left
        anchors.leftMargin: 0
        width:page2.visible?parent.width/2:parent.width
        onExpand: {
            if(flag){
                window.width *= 2
                page2.visible = true
            }
            else{
                window.width /= 2
                page2.visible = false
            }
        }
        settingItem:page2
    }

    SettingPage{
        id:page2
        anchors.right: parent.right
        anchors.rightMargin: 0
        anchors.top: parent.top
        anchors.topMargin: 0
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 0
        width:parent.width/2
        visible: false
    }
}
