import QtQuick 2.8
import zm.pyqt.Downloader 1.0
import Qt.labs.settings 1.0
import QtQuick.Controls 2.3

Item {
    id:page

    property alias count: listView.count
    property string optionsList: "[]"
    property string urlList: ""
    property string pathList: ""
    property string nameList: ""
    property string stateList: ""
    property string numList: ""

    signal toFinish(string url,string path,string name,string num,
                    string finishFile, string total,string curProgress, var taskOptions)
    signal toTrash(string url,string path,string name,string num,
                   string finishFile, string total,string curProgress, var taskOptions)
    signal deleteFile(string path,string name, var taskOptions)
    signal deleteFiles(var tasks)
    signal stopAllDownloads()
    signal viewOnExplorer(string path,string name)

    function optionsAt(index){
        var values = JSON.parse(optionsList || "[]")
        return values[index] || {}
    }

    function appendOptions(options){
        var values = JSON.parse(optionsList || "[]")
        while(values.length < listModel.count)
            values.push({})
        values.push(options || {})
        optionsList = JSON.stringify(values)
    }

    function removeOptions(index){
        var values = JSON.parse(optionsList || "[]")
        values.splice(index, 1)
        optionsList = JSON.stringify(values)
    }

    function activeNames(path){
        var names = []
        var folder = path.replace(/\\/g, "/").replace(/\/$/, "").toLowerCase()
        for(var i = 0; i < listModel.count; i++){
            var task = listModel.get(i)
            if(task.path.replace(/\\/g, "/").replace(/\/$/, "").toLowerCase() == folder)
                names.push(task.name)
        }
        return names
    }

    function insertNew(url,path,name,totalFile,taskOptions){
        taskOptions = taskOptions || {}
        if(path[path.length - 1] != "/")
            path += "/"
        if(taskOptions.kind)
            name = setting.reserveVideoName(name,path,taskOptions,activeNames(path))
        appendOptions(taskOptions)
        urlAppend(url)
        pathAppend(path)
        nameAppend(name)
        numAppend(totalFile)
        stateAppend("downloading")
        listModel.append({url:url, path:path, name:name, files:String(totalFile),
                          optionsJson:JSON.stringify(taskOptions)})
    }

    function syncVideoTask(index, attributes){
        if(index < 0 || index >= listModel.count || !attributes)
            return
        if(!optionsAt(index).kind)
            return
        var names = nameList.split('|')
        var counts = numList.split('|')
        names[index + 1] = attributes.fileName
        counts[index + 1] = String(attributes.totalFile)
        nameList = names.join('|')
        numList = counts.join('|')
        listModel.setProperty(index, "name", attributes.fileName)
        listModel.setProperty(index, "files", String(attributes.totalFile))
    }

    //删除任务有三种情况，一种是完成后去到已完成列表，一个是移除到已删除列表
    //最后一种是永久删除，不保留记录
    function removeTask(index,isFinish,toRecycleBin,
                        finishFile,total,curProgress){
        var u = listModel.get(index).url
        var p = listModel.get(index).path
        var n = listModel.get(index).name
        var f = listModel.get(index).files
        var options = optionsAt(index)
        urlRemove(index)
        pathRemove(index)
        nameRemove(index)
        stateRemove(index)
        numRemove(index)
        removeOptions(index)
        listModel.remove(index)
        if(isFinish){
            page.toFinish(u,
                          p,
                          n,
                          f,
                          finishFile,
                          total,
                          curProgress, options)
        }
        else if(toRecycleBin){
            page.toTrash(u,
                         p,
                         n,
                         f,
                         finishFile,
                         total,
                         curProgress, options)
        }
        else{
            page.deleteFile(p,
                            n, options)
        }
    }

    function removeAllTasks(){
        var tasks = []
        for(var i = 0; i < listModel.count; i++){
            var task = listModel.get(i)
            tasks.push({path: task.path, name: task.name, options: optionsAt(i)})
        }
        page.stopAllDownloads()
        listModel.clear()
        optionsList = "[]"
        urlList = ""
        pathList = ""
        nameList = ""
        numList = ""
        stateList = ""
        settings.sync()
        page.deleteFiles(tasks)
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

    function numAppend(str){
        numList += "|" + str
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

    function numRemove(index){
        var l = numList.split('|')
        numList = ""
        for(var n = 1; n < l.length; n++){
            if(n != index + 1)
                numAppend(l[n])
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
        value /= 1.0
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
        var numl = numList.split('|')

        for(var n = 1; n < ul.length; n++){
            listModel.append({
                                 url:ul[n],
                                 path:pl[n],
                                 name:nl[n],
                                 optionsJson:JSON.stringify(optionsAt(n - 1)),
                                 files:numl[n]
                             })
        }
    }

    DeleteAllDialog{
        id:deleteAllDialog
        taskCount:page.count
        x:(page.width - width) / 2
        y:(page.height - height) / 2
        onAccepted:page.removeAllTasks()
    }

    Settings{
        id:settings
        property alias downloadOptions: page.optionsList
        property alias downloadUrl: page.urlList
        property alias downloadPath: page.pathList
        property alias downloadName: page.nameList
        property alias downloadState: page.stateList
        property alias downloadNum: page.numList
    }

    ListView{
        id:listView
        cacheBuffer:Math.max(height, contentHeight)
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
                height:videoTask ? 100 : 80
                //color:index == listView.currentIndex ? "#98F5FF" : "white"
                x: 5

                property real total: attributes?attributes.total:0
                property real curProgress: attributes?attributes.curProgress:0
                property int  curTime: attributes?attributes.curTime:0
                property var  curSpeed: 0
                property int  preTime: 0
                property real preProgress: attributes?attributes.preProgress:0
                property string state: attributes?attributes.state:""
                property int finishFile: attributes?attributes.finishFile:0
                property int totalFile: attributes?attributes.totalFile:0
                property var attributes: 0
                property bool videoTask: !!JSON.parse(optionsJson || "{}").kind
                property bool activeTask: state == "downloading" || state == "resolving" || state == "merging"

                onStateChanged: {
                    if(delegateItem.state =="")
                        return
                    page.stateChanged(index,delegateItem.state)
                    if(delegateItem.state != "downloading"){
                        if(delegateItem.state == "finish"){
                            page.syncVideoTask(index, attributes)
                            page.removeTask(index,true,false,
                                            delegateItem.finishFile,
                                            delegateItem.total,
                                            delegateItem.curProgress)
                            return
                        }
//                        bar.stop()
                    }

                }

                Component.onCompleted: {
                    downloaderManager.setTaskOptions(JSON.parse(optionsJson || "{}"))
                    downloaderManager.setFileTotal(files)
                    downloaderManager.setPath(path)
                    downloaderManager.setUrl(url)
                    downloaderManager.setFileName(name)
                    var state = page.getState(index) =="pause"
                    attributes = downloaderManager.downloadFile(state)
                    page.syncVideoTask(index, attributes)
                }

                DownloaderManager{
                    id:downloaderManager
                    ffmpeg:setting.ffmpeg
                }

                Connections{
                    target:page
                    function onStopAllDownloads(){
                        downloaderManager.deleteFile()
                    }
                }

                Component.onDestruction:downloaderManager.deleteFile()

                Connections{
                    target:delegateItem.attributes || null
                    function onFileNameChanged(){page.syncVideoTask(index, delegateItem.attributes)}
                    function onTotalFileChanged(){page.syncVideoTask(index, delegateItem.attributes)}
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
                    text:attributes?attributes.taskName:""
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
                    value:videoTask && totalFile > 0 ? finishFile / totalFile * 100 : (total > 0 ? curProgress / total * 100 : 0)

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
                        case "resolving":
                            return "正在读取清单"
                        case "merging":
                            return "正在合并视频"
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
                        case "totalLessThanZero":
                            return "文件大小识别错误"
                        default:
                            return "未知状态"
                        }
                    }
                    color:{
                        switch(delegateItem.state){
                        case "downloadError":
                        case "fileOpenError":
                        case "fileWriteError":
                        case "networkError":
                            return "#ff0000"
                        case "NoDownload":
                        case "downloading":
                        case "pause":
                        case "finish":
                        default:
                            return "#445266"
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
                        if(delegateItem.state == "merging")
                            return "停止"
                        if(delegateItem.activeTask)
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

                TextLoader{
                    visible:delegateItem.videoTask
                    text:delegateItem.attributes ? delegateItem.attributes.message : ""
                    width:parent.width
                    elide:Text.ElideRight
                    anchors.top:totalFileText.bottom
                    anchors.topMargin:4
                }

                MouseArea{
                    anchors.fill: parent
                    z:stateButton.z - 1
                    acceptedButtons:Qt.RightButton
                    onClicked: {
                        if(mouse.button == Qt.RightButton){
                            popup.x = mouse.x
                            popup.y = mouse.y
                            popup.open()
                        }
                    }
                }

                Menu{
                    id:popup

                    Action{
                        id:startAction
                        text:qsTr("开始下载")
                        checkable: false
                        enabled: !delegateItem.activeTask
                        onTriggered: {
                            popup.close()
                            downloaderManager.pauseDown()
                        }
                    }

                    Action{
                        id:pauseAction
                        text:delegateItem.state == "merging" ? "停止合并" : "暂停下载"
                        checkable: false
                        enabled:!startAction.enabled
                        onTriggered: {
                            popup.close()
                            downloaderManager.pauseDown()
                        }
                    }

                    Action{
                        id:view
                        text:qsTr("打开所在文件夹")
                        checkable: false
                        onTriggered: {
                            popup.close()
                            page.viewOnExplorer(path,name)
                        }
                    }

                    Action{
                        id:removeAction
                        text:qsTr("移至已删除")
                        checkable: false
                        onTriggered: {
                            popup.close()
                            downloaderManager.deleteFile()
                            page.removeTask(index,false,true,
                                            delegateItem.finishFile,
                                            delegateItem.total,
                                            delegateItem.curProgress)
                        }
                    }

                    Action{
                        id:deleteAction
                        text:qsTr("永久删除")
                        checkable: false
                        onTriggered: {
                            popup.close()
                            downloaderManager.deleteFile()
                            page.removeTask(index,false,false,
                                            delegateItem.finishFile,
                                            delegateItem.total,
                                            delegateItem.curProgress)
                        }
                    }

                    MenuSeparator{}

                    Action{
                        text:qsTr("全部删除")
                        enabled:page.count > 0
                        onTriggered: {
                            popup.close()
                            deleteAllDialog.open()
                        }
                    }
                }

            }
        }
    }

}
