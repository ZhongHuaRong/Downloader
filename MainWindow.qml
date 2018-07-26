import QtQuick 2.8

Item {
    id:mainWindow

    signal getUrl(var url)

    function showBox(title,msg,buttons){
        messageDialog.title = title
        messageDialog.text = msg
        messageDialog.buttons = buttons
        messageDialog.open()
    }

    function setDownProgress(success,total,timeStamp){
        filemsgItem.setProgress(success,total,timeStamp)
    }

    Component.onCompleted: {
        edit.setText("https://www.talkpal.com/static/talkpal.exe")
    }

    Row {
        id: row
        height: 40
        anchors.right: parent.right
        anchors.rightMargin: 0
        anchors.left: parent.left
        anchors.leftMargin: 0
        anchors.top: parent.top
        anchors.topMargin: 0
        spacing: 10
        padding: 5

        TextLoader {
            id: path
            text: qsTr("Path:")
            height:edit.height
        }

        CTextEdit{
            id:edit
            width:parent.width - path.width - pushButton.width - 30
            placeholderText:"输入URL"
        }

        CPushButton {
            id: pushButton
            height:edit.height
            width:50
            text:"find"
            onClicked: {
                mainWindow.getUrl(edit.getText())
            }
        }
    }

    FileMsgItem{
        id:filemsgItem
        anchors.top: row.bottom
        anchors.topMargin: 0
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 0
        anchors.left: parent.left
        anchors.leftMargin: 0
        anchors.right: parent.right
        anchors.rightMargin: 0

    }
}
