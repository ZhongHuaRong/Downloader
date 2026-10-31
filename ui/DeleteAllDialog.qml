import QtQuick 2.8
import QtQuick.Controls 2.3

Dialog {
    id:dialog
    property int taskCount: 0

    title:qsTr("全部删除")
    width:340
    modal:true
    footer:DialogButtonBox {
        Button {
            text:qsTr("确定")
            DialogButtonBox.buttonRole:DialogButtonBox.AcceptRole
        }
        Button {
            text:qsTr("取消")
            DialogButtonBox.buttonRole:DialogButtonBox.RejectRole
        }
    }

    contentItem:Label {
        text:qsTr("确定删除当前列表中的全部 %1 个任务吗？\n未完成的下载文件将被删除，已完成的文件会保留。").arg(dialog.taskCount)
        wrapMode:Text.WordWrap
    }
}
