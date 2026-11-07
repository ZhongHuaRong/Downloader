import QtQuick 2.8
import QtQuick.Controls 2.3

Dialog {
    id:dialog
    property int taskCount: 0

    title:qsTr("Delete All")
    width:340
    modal:true
    standardButtons:Dialog.Yes | Dialog.No

    contentItem:Label {
        text:qsTr("Delete all %1 tasks in the current list?\nIncomplete downloads will be removed. Completed files will be kept.").arg(dialog.taskCount)
        wrapMode:Text.WordWrap
    }
}
