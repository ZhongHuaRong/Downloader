import QtQuick 2.8
import zm.pyqt.Downloader 1.0
import Qt.labs.settings 1.0

Item {
    id:page

    property alias count: listView.count
    property string urlList: ""
    property string pathList: ""
    property string nameList: ""
    property string stateList: ""

    function insertNew(url,path,name){
        path += "/"
        console.debug(url,path,name)
        listModel.append({
                             url:url,
                             path:path,
                             name:name
                         })
        urlAppend(url)
        pathAppend(path)
        nameAppend(name)
        stateAppend("downloading")
    }

    function removeFinish(index){
        urlRemove(index)
        pathRemove(index)
        nameRemove(index)
        stateRemove(index)
        listModel.remove(index)
    }

    function urlAppend(str){
        urlList += "|" + str
    }

    function pathAppend(str){
        pathList += "|" + str
    }

    function nameAppend(str){
        nameList += "|" + str
    }

    function stateAppend(str){
        stateList += "|" + str
    }

    function urlRemove(index){
        var l = urlList.split('|')
        urlList = ""
        for(var n = 1; n < l.length; n++){
            if(n != index + 1)
                urlAppend(l[n])
        }
    }

    function pathRemove(index){
        var l = pathList.split('|')
        pathList = ""
        for(var n = 1; n < l.length; n++){
            if(n != index + 1)
                pathAppend(l[n])
        }
    }

    function nameRemove(index){
        var l = nameList.split('|')
        nameList = ""
        for(var n = 1; n < l.length; n++){
            if(n != index + 1)
                nameAppend(l[n])
        }
    }

    function stateRemove(index){
        var l = stateList.split('|')
        stateList = ""
        for(var n = 1; n < l.length; n++){
            if(n != index + 1)
                stateAppend(l[n])
        }
    }

    function stateChanged(index,state){
        var l = stateList.split('|')
        stateList = ""
        for(var n = 1; n < l.length; n++){
            if(n == index + 1)
                stateAppend(state)
            else
                stateAppend(l[n])
        }
    }

    function getState(index){
        console.debug(stateList)
        var l = stateList.split('|')
        return l[index + 1]
    }

    function changeToString(value){
        var n = 0
        while(value>1024){
            value /= 1024.0
            n++
        }

        var m
        switch(n){
        case 0:
            m = "B"
            break
        case 1:
            m = "KB"
            break
        case 2:
            m = "MB"
            break
        case 3:
            m = "GB"
            break
        }

        return value.toFixed(2) + " " + m
    }

    // 加载历史信息
    Component.onCompleted: {
        var ul = urlList.split('|')
        var pl = pathList.split('|')
        var nl = nameList.split('|')

        for(var n = 1; n < ul.length; n++){
            listModel.append({
                                 url:ul[n],
                                 path:pl[n],
                                 name:nl[n]
                             })
        }
    }

    Settings{
        id:settings
        property alias downloadUrl: page.urlList
        property alias downloadPath: page.pathList
        property alias downloadName: page.nameList
        property alias downloadState: page.stateList
    }

    ListView{
        id:listView
        anchors.fill: parent
        clip:true
        model: ListModel{
            id:listModel
        }
        delegate: contactsDelegate

        Component{
            id:contactsDelegate
            Rectangle{
                id:delegateItem
                width:listView.width - 10
                height:80
                //color:index == listView.currentIndex ? "#98F5FF" : "white"
                anchors.left: parent.left
                anchors.leftMargin: 5

                property real total: attributes?attributes.total:0
                property int  curProgress: attributes?attributes.curProgress:0
                property int  curTime: attributes?attributes.curTime:0
                property var  curSpeed: 0
                property int  preTime: 0
                property int  preProgress: attributes?attributes.preProgress:0
                property string state: attributes?attributes.state:""
                property int finishFile: attributes?attributes.finishFile:0
                property int totalFile: attributes?attributes.totalFile:0
                property var attributes: 0

                onStateChanged: {
                    if(delegateItem.state =="")
                        return
                    page.stateChanged(index,delegateItem.state)
                    if(delegateItem.state != "downloading"){
                        if(delegateItem.state == "finish"){
                            page.removeFinish(index)
                            return
                        }
                        bar.stop()
                    }

                }

                Component.onCompleted: {
                    downloaderManager.setFileTotal(1)
                    downloaderManager.setPath(path)
                    downloaderManager.setUrl(url)
                    downloaderManager.setFileName(name)
                    // 提前获取下载状态，因为获取attribute的时候默认是正在下载的情况
                    var state = page.getState(index) =="pause"
                    attributes = downloaderManager.downloadFile(state)
                }

                DownloaderManager{
                    id:downloaderManager
                }

                onCurTimeChanged: {
                    if(preTime == curTime)
                        return
                    curSpeed = (curProgress - preProgress) / (curTime - preTime)
                    preTime = curTime
                    preProgress = curProgress
                }

                function stop(){
                    bar.stop()
                }

                function reset(){
                    total = 0.0
                    curProgress = 0.0
                    curTime = 0
                    curSpeed  = 0.0
                }


                TextLoader{
                    id:fileNameText
                    text:attributes?attributes.fileName:""
                    anchors.top: parent.top
                    anchors.topMargin: 10
                }

                CProgressBar{
                    id:bar
                    anchors.top: fileNameText.bottom
                    anchors.topMargin: 5
                    anchors.right: downState.left
                    anchors.rightMargin: 20
                    anchors.left: parent.left
                    anchors.leftMargin: 0
                    height:20
                    value:curProgress / total * 100

                    TextLoader{
                        id:percentage
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                        anchors.fill: parent
                        text:(bar.value).toFixed(2) + "%"
                    }
                }

                TextLoader{
                    id:downState
                    text:{
                        switch(delegateItem.state){
                        case "downloadError":
                            return "下载出现错误"
                        case "NoDownload":
                            return "未开始下载  "
                        case "downloading":
                            return "正在下载中  "
                        case "pause":
                            return "暂停任务    "
                        case "finish":
                            return "下载完成    "
                        case "fileOpenError":
                        case "fileWriteError":
                            return "文件可能丢失"
                        case "networkError":
                            return "网络出现错误"
                        }
                    }
                    color:{
                        switch(delegateItem.state){
                        case "NoDownload":
                        case "downloading":
                        case "pause":
                        case "finish":
                            return "#445266"
                        case "downloadError":
                        case "fileOpenError":
                        case "fileWriteError":
                        case "networkError":
                            return "#ff0000"
                        }
                    }
                    anchors.top: fileNameText.bottom
                    anchors.topMargin: 5
                    anchors.right: downloadSpeed.left
                    anchors.rightMargin: 20
                }

                TextLoader{
                    id:downloadSpeed
                    text:page.changeToString(curSpeed) + "/s"
                    anchors.top: fileNameText.bottom
                    anchors.topMargin: 5
                    anchors.right: stateButton.left
                    anchors.rightMargin: 20
                }

                CPushButton{
                    id:stateButton
                    text:{
                        if(delegateItem.state == "downloading")
                            return "暂停"
                        else
                            return "继续"
                    }
                    width:50
                    height:20
                    anchors.top: fileNameText.bottom
                    anchors.topMargin: 5
                    anchors.right: parent.right
                    anchors.rightMargin: 0
                    onClicked: {
                        downloaderManager.pauseDown()
                    }
                }

                TextLoader{
                    id:fileSize
                    anchors.top: stateButton.bottom
                    anchors.topMargin: 5
                    anchors.left: parent.left
                    anchors.leftMargin: 0
                    text:"文件大小:" + page.changeToString(total)
                }

                TextLoader{
                    id:down
                    anchors.top: stateButton.bottom
                    anchors.topMargin: 5
                    anchors.left: fileSize.right
                    anchors.leftMargin: 10
                    text:"已下载:"+page.changeToString(curProgress)
                }

                TextLoader{
                    id:totalFileText
                    anchors.top: stateButton.bottom
                    anchors.topMargin: 5
                    anchors.left: down.right
                    anchors.leftMargin: 20
                    anchors.right: parent.right
                    anchors.rightMargin: 0
                    text:"已完成/总数量:"+finishFile + "/" + totalFile
                }

            }
        }
    }

}
