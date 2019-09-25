import QtQuick.Window 2.3
import QtQuick 2.9
import QtQuick.Controls 2.2

Window  {
    id:dialog
    modality : Qt.ApplicationModal
    property bool exitCheck: false
    property alias informativeText: text1.text

    signal accept()
    signal cancel()

    onClosing:{
        close.accepted = false
        cancel()
        dialog.hide()
    }

    CCheckBox {
        id: checkBox
        x: 75
        y: 340
        text: qsTr("Check Box")
    }

    Text {
        id: text1
        x: 75
        y: 48
        width: 499
        height: 278
        text: qsTr("Text")
        font.pixelSize: 14
        font.family: "微软雅黑"
        color: "#445266"
    }

    CPushButton {
        id: yesButton
        x: 375
        y: 397
        text: qsTr("确认")
        onClicked: {
            dialog.accept()
            dialog.hide()
        }
    }

    CPushButton {
        id: noButton
        x: 489
        y: 397
        text: qsTr("取消")
        onClicked: {
            dialog.cancel()
            dialog.hide()
        }
    }
}
