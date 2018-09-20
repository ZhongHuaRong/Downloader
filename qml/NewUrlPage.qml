import QtQuick 2.9
import QtQuick.Layouts 1.3
import QtQuick.Dialogs 1.3
import Qt.labs.settings 1.0

Item {
    id:urlPage

    property var settingItem: ""
    property int  type: 0

    signal newOne(string url,string path,string fileName,string pages)

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
                    loader.item.setFileName(sourceEdit.text,targetEdit.text)
                    break;
                case 2:
                    //BT类型
                    loader.source = "./BTSetting.qml"
                    loader.item.setFileName(sourceEdit.text,targetEdit.text)
                    break;
                }
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

        // 放在这里实现，用信号绑定的话会出现重复的情况，
        // 除非解除绑定，不过解除绑定需要花费很多功夫去检测
        function httpDownload(name,pages){
            console.debug("httpDownload")
            urlPage.newOne(sourceEdit.text,targetEdit.text,name,pages)
        }

        function btDownload(url,name){
            console.debug("httpDownload")
            urlPage.newOne(url,targetEdit.text,name,"1")
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
