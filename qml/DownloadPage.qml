import QtQuick 2.8
import zm.pyqt.Downloader 1.0
import zm.pyqt.Compressor 1.0
import QtQuick.Dialogs 1.3

Item {
    id:page

    property var settingItem: 0

    signal expand(bool flag)

    function showMsg(title,msg){
        messageDialog.text = msg
        messageDialog.title = title
        messageDialog.icon = StandardIcon.Information
        messageDialog.open()
    }

    function showError(msg){
        messageDialog.text = msg
        messageDialog.title = "错误"
        messageDialog.icon = StandardIcon.Critical
        messageDialog.open()
    }

    function stopDown(){
        downloader.stopDown()
        filemsgItem.stop()
    }

    function startDown(){
        downloader.startDownload(sourceEdit.text,filemsgItem.fileName,targetEdit.text)
    }

    Component.onCompleted: {
        sourceEdit.text = ("https://www.talkpal.com/static/talkpal.exe")
        targetEdit.text = ("C:\\Users\\Administrator\\Desktop")
    }

    Downloader{
        id:downloader

        onShowMsg:{
            showMsg(title,msg)
        }

        onShowError:{
            page.stopDown()
            page.showError(err)
        }

        onPasteUrlChanged:{
            if(settingItem.pasteUrlFlag)
                sourceEdit.text = url
            //这里运行这句话主要是怕链接是复制同一个,并没有触发textChanged
            filemsgItem.fileName = downloader.checkFileName(sourceEdit.text,targetEdit.text)

            if(settingItem.downloadFlag)
                startDown()
        }

        onFinishChanged:{
            if(!downloader.finish)
                return
            if(settingItem.decoFlag){
                var str = ""
                if(settingItem.usePWFlag){
                    str = sourceEdit.text.split("/")[2] + ";"
                    if(settingItem.usePWListFlag)
                        str += settingItem.pwList
                }
                compressor.compressFile(targetEdit.text + filemsgItem.fileName,targetEdit.text,str)
            }
        }
    }

    Compressor{
        id:compressor
    }

    Row {
        id: sourceRow
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
            id: sourcePath
            text: qsTr("source Path:")
            height:sourceEdit.height
        }

        CTextEdit{
            id:sourceEdit
            width:parent.width - sourcePath.width - 30
            placeholderText:"输入URL"
            enabled: !downloader.downloading
            onTextChanged: {
                filemsgItem.fileName = downloader.checkFileName(sourceEdit.text,targetEdit.text)
            }
        }

    }


    Row {
        id: targetRow
        height: 40
        anchors.right: parent.right
        anchors.rightMargin: 0
        anchors.left: parent.left
        anchors.leftMargin: 0
        anchors.top: sourceRow.bottom
        anchors.topMargin: 0
        spacing: 10
        padding: 5

        TextLoader {
            id: targetPath
            text: qsTr("target Path:")
            height:targetEdit.height
        }

        CTextEdit{
            id:targetEdit
            width:parent.width - targetPath.width -  findPath.width - 35
            placeholderText:"输入URL"
            enabled: !downloader.downloading
        }

        CPushButton{
            id:findPath
            text:"选择路径"
            height:targetEdit.height
            onClicked: {
                fileDialog.open()
            }
        }
    }


    Row{
        id:buttonRow
        spacing: 10
        padding: 10
        anchors.top: targetRow.bottom
        anchors.topMargin: 0
        anchors.right: parent.right
        anchors.rightMargin: 0
        anchors.left: parent.left
        anchors.leftMargin: 0

        CPushButton {
            id: downButon
            width:100
            text:"下载"
            enabled: !downloader.downloading
            onClicked: {
                startDown()
            }
        }


        CPushButton {
            id: pushButton
            width:100
            text:downloader.pause?"继续":"暂停"
            enabled: downloader.downloading
            onClicked: {
                downloader.pauseDown(!downloader.pause)
            }
        }


        CPushButton {
            id: stopButton
            width:100
            text:"停止下载"
            enabled: downloader.downloading
            onClicked: {
                stopDown()
            }
        }

        CPushButton {
            id: settingButton
            width:100
            checkable: true
            text:checked?"隐藏":"显示"
            onClicked: expand(checked)
        }
    }

    FileMsgItem{
        id:filemsgItem
        anchors.top: buttonRow.bottom
        anchors.topMargin: 0
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 0
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.right: parent.right
        anchors.rightMargin: 10
        total: downloader.total
        curProgress:downloader.curProgress
        curTime:downloader.curTime
        state:{
            if(downloader.downloading){
                if(downloader.pause)
                    return "暂停中"
                else
                    return "正在下载..."
            }
            else {
                if(downloader.finish){
                    filemsgItem.stop()
                    return "下载完成"
                }
                else
                    return "未开始下载"
            }
        }

    }

    MessageDialog {
        id: messageDialog
        title: "May I have your attention please"
        text: "It's so cool that you are using Qt Quick."
        icon:StandardIcon.Information
        onYes: {
            //
        }
    }

    FileDialog{
        id:fileDialog
        title: "选择一个路径"
        folder: shortcuts.desktop
        selectFolder:true
        onAccepted: {
            var str  = fileDialog.fileUrls[0].split("file:///")
            targetEdit.text = str[1]
        }
    }

}
