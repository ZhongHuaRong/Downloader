import QtQuick 2.9
import QtQuick.Layouts 1.3
import QtQuick.Dialogs 1.3
import Qt.labs.settings 1.0

Item {
    id:urlPage

    property var settingItem: ""
    property int  type: 0

    signal newOne(string url,string path,string fileName)

    function getNewUrl(url){
        sourceEdit.text = url
    }

    function urlType(url){
        if(url.length == 0)
            return 0
        var text = url.split('://')
        if (text.length < 1)
            return 0
        else if(text[0] == "http" || text[0] == "https")
            return 1
        else if(text[0] == "thunder")
            return 2
        else
            return 0
    }

    function startDownload(name){
        //该信号在多个文件下载时优化
        urlPage.newOne(sourceEdit.text,targetEdit.text,name)
    }

    Settings {
        property alias lastSelectDownloadPath: targetEdit.text
    }

    Component.onCompleted: {
        setting.haveNewUrl.connect(urlPage.getNewUrl)
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
            readOnly: settingItem.downloadFlag
            onTextChanged: {
                type = urlType(text)
                switch(type){
                case 0:
                    //未知类型或者未填写
                    loader.source = ""
                    break;
                case 1:
                    //http类型
                    loader.source = "./HttpSetting.qml"
                    break;
                case 2:
                    //BT类型
                    break;
                }

//                filemsgItem.fileName = downloader.checkFileName(sourceEdit.text,targetEdit.text)
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
            placeholderText:"输入路劲"
            text:fileDialog.shortcuts.desktop.split("file:///")[1]
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

    Loader{
        id:loader
        anchors.right: parent.right
        anchors.rightMargin: 0
        anchors.left: parent.left
        anchors.leftMargin: 0
        anchors.top: targetRow.bottom
        anchors.topMargin: 0
        anchors.bottom:parent.bottom
        anchors.bottomMargin: 0

        onLoaded: {
            switch(type){
            case 0:
                //未知类型或者未填写
                loader.source = ""
                break;
            case 1:
                //http类型
                loader.item.download.connect(urlPage.startDownload)
                loader.item.setFileName(sourceEdit.text,targetEdit.text)
                break;
            case 2:
                //BT类型
                break;
            }
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
