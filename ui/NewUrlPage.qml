import QtQuick 2.9
import QtQuick.Layouts 1.3
import QtQuick.Dialogs 1.3
import Qt.labs.settings 1.0

Item {
    id:urlPage

    property var settingItem: ""
    property int  type: 0

    signal newVideoTasks(var tasks,string path)
    signal inspectM3u8(string url)
    signal cancelVideo()
    signal recognizeVideo(string url,bool manual)
    signal finishVideoRecognition()
    signal stopVideoRecognition()
    signal previewVideo(string resourceId,bool force)

    function configureSource(){
        if(!loader.item)
            return
        var url = setting.getBaseUrl(sourceEdit.text).trim()
        if(type == 1 || type == 4)
            loader.item.setMsg(url, type == 4 ? setting.videoFileName(url,"m3u8") : setting.checkFileName(url,targetEdit.text),targetEdit.text)
        else if(type == 2)
            loader.item.setFileName(url,targetEdit.text)
    }

    signal newOne(string url,string path,string fileName,string pages)

    function getNewUrl(url){
        sourceEdit.text = url
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
                urlPage.cancelVideo()
                var url = setting.getBaseUrl(sourceEdit.text).trim()
                type = setting.getUrlType(url)
                var nextSource = type == 1 ? "./HttpSetting.qml" : type == 4 ? "./M3u8Setting.qml" : type == 2 ? "./BTSetting.qml" : ""
                if(loader.source.toString() == nextSource || loader.source.toString().endsWith(nextSource.substring(1)) && nextSource.length > 0)
                    urlPage.configureSource()
                else
                    loader.source = nextSource
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
            objectName:"targetPath"
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
        objectName:"sourceConfiguration"
        anchors.right: parent.right
        anchors.rightMargin: 0
        anchors.left: parent.left
        anchors.leftMargin: 0
        anchors.top: targetRow.bottom
        anchors.topMargin: 0
        anchors.bottom:parent.bottom
        anchors.bottomMargin: 0

        onLoaded:urlPage.configureSource()

        function recognizeVideo(url,manual){urlPage.recognizeVideo(url,manual)}
        function finishRecognition(){urlPage.finishVideoRecognition()}
        function stopRecognition(){urlPage.stopVideoRecognition()}
        function previewVideo(resourceId,force){urlPage.previewVideo(resourceId,force)}

        function videoDownload(tasks){
            urlPage.newVideoTasks(tasks,targetEdit.text)
        }

        function inspectVideo(url){
            urlPage.inspectM3u8(url)
        }

        // 放在这里实现，用信号绑定的话会出现重复的情况，
        // 除非解除绑定，不过解除绑定需要花费很多功夫去检测
        function httpDownload(baseUrl,name,pages){
            console.debug("httpDownload")
            urlPage.newOne(baseUrl,targetEdit.text,name,pages)
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
