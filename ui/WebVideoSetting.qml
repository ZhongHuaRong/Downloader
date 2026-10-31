import QtQuick 2.9
import QtQuick.Controls 1.4

Item {
    id:results
    objectName:"webVideoResults"
    height:content.implicitHeight
    property int selectedCount:0
    property int resourceCount:resourceModel.count
    signal previewClicked(string resourceId,bool force)

    function refresh(){
        var resources = setting.video.resources
        var ids = resources.map(function(item){return item.id})
        for(var i = resourceModel.count - 1; i >= 0; i--){
            if(ids.indexOf(resourceModel.get(i).resourceId) < 0)
                resourceModel.remove(i)
        }
        for(var n = 0; n < resources.length; n++){
            var resource = resources[n]
            var row = -1
            for(var j = 0; j < resourceModel.count; j++){
                if(resourceModel.get(j).resourceId == resource.id){row = j; break}
            }
            var values = {resourceId:resource.id,kind:resource.kind,url:resource.url,
                          variantsJson:JSON.stringify(resource.variants),duration:resource.duration || 0,
                          preview:resource.preview || "",previewBusy:!!resource.previewBusy,previewError:resource.previewError || ""}
            if(row < 0){
                values.selectedFlag = false
                values.fileNameValue = setting.videoFileName(resource.url,resource.kind)
                values.selectedVariant = resource.variantUrl || resource.url
                resourceModel.append(values)
            }
            else{
                for(var key in values)
                    resourceModel.setProperty(row,key,values[key])
            }
        }
        updateSelectedCount()
    }

    function updateSelectedCount(){
        var count = 0
        for(var i = 0; i < resourceModel.count; i++)
            if(resourceModel.get(i).selectedFlag)
                count++
        selectedCount = count
    }

    function selectedTasks(){
        var tasks = []
        for(var i = 0; i < resourceModel.count; i++){
            var item = resourceModel.get(i)
            if(item.selectedFlag)
                tasks.push({url:item.url,name:item.fileNameValue,
                            options:setting.video.taskOptions(item.resourceId,item.selectedVariant)})
        }
        return tasks
    }

    function requestVisiblePreviews(top,height){
        for(var i = 0; i < repeater.count; i++){
            var item = repeater.itemAt(i)
            if(item && results.y + item.y < top + height && results.y + item.y + item.height > top)
                results.previewClicked(resourceModel.get(i).resourceId,false)
        }
    }

    function durationLabel(value){
        if(!value || value <= 0)
            return "时长未知"
        var seconds = Math.round(value)
        return Math.floor(seconds / 60) + ":" + (seconds % 60 < 10 ? "0" : "") + seconds % 60
    }

    Component.onCompleted:refresh()
    Connections{
        target:setting.video
        function onChanged(){results.refresh()}
    }

    ListModel{id:resourceModel}
    Column{
        id:content
        width:parent.width
        spacing:8

        TextLoader{
            text:"已发现 " + resourceModel.count + " 组资源 · 已选 " + results.selectedCount + " 组"
        }
        TextLoader{
            width:parent.width
            wrapMode:Text.Wrap
            text:"发布标题：" + (setting.video.title || "未获取")
        }
        TextLoader{
            width:parent.width
            wrapMode:Text.Wrap
            text:"发布时间：" + (setting.video.publishedDate || setting.video.rawPublishedDate || "未获取")
        }

        Repeater{
            id:repeater
            model:resourceModel
            Rectangle{
                id:resourceItem
                objectName:"videoResource"
                property int rowIndex:index
                width:content.width
                height:selectedFlag ? 134 : 94
                color:"#fafafa"
                border.color:"#dfdfe7"

                Row{
                    id:resourceRow
                    x:8
                    y:8
                    spacing:8
                    width:parent.width - 16
                    CCheckBox{
                        objectName:"videoSelected"
                        width:22
                        checked:selectedFlag
                        onClicked:{
                            resourceModel.setProperty(resourceItem.rowIndex,"selectedFlag",checked)
                            results.updateSelectedCount()
                        }
                    }
                    Rectangle{
                        width:100
                        height:72
                        color:"#e9ecf0"
                        Image{
                            anchors.fill:parent
                            source:preview
                            fillMode:Image.PreserveAspectFit
                            asynchronous:true
                        }
                        TextLoader{
                            anchors.fill:parent
                            horizontalAlignment:Text.AlignHCenter
                            verticalAlignment:Text.AlignVCenter
                            wrapMode:Text.Wrap
                            visible:!preview || previewBusy
                            text:previewBusy ? "正在获取…" : previewError ? "获取失败\n点击重试" : "暂无预览\n点击获取"
                        }
                        MouseArea{
                            objectName:"videoPreview"
                            anchors.fill:parent
                            cursorShape:Qt.PointingHandCursor
                            onClicked:results.previewClicked(resourceId,true)
                        }
                    }
                    Column{
                        width:resourceRow.width - 138
                        spacing:4
                        TextLoader{
                            width:parent.width
                            elide:Text.ElideRight
                            text:"资源 " + (resourceItem.rowIndex + 1) + " · " + (kind || "").toUpperCase()
                        }
                        TextLoader{text:results.durationLabel(duration)}
                        ComboBox{
                            id:quality
                            objectName:"videoQuality"
                            width:Math.min(160,parent.width)
                            height:26
                            visible:JSON.parse(variantsJson).length > 1
                            model:JSON.parse(variantsJson).map(function(item){return item.label})
                            currentIndex:{
                                var values = JSON.parse(variantsJson)
                                for(var n = 0; n < values.length; n++)
                                    if(values[n].url == selectedVariant) return n
                                return 0
                            }
                            onActivated:resourceModel.setProperty(resourceItem.rowIndex,"selectedVariant",JSON.parse(variantsJson)[currentIndex].url)
                        }
                    }
                }

                Row{
                    objectName:"videoNameRow"
                    visible:selectedFlag
                    x:8
                    y:94
                    width:parent.width - 16
                    spacing:6
                    TextLoader{id:nameLabel; text:"文件名:"; height:30}
                    CTextEdit{
                        id:nameEdit
                        objectName:"videoName"
                        width:parent.width - nameLabel.width - titleButton.width - 12
                        text:fileNameValue
                        onTextChanged:{
                            if(text != fileNameValue)
                                resourceModel.setProperty(resourceItem.rowIndex,"fileNameValue",text)
                        }
                    }
                    CPushButton{
                        id:titleButton
                        objectName:"videoTitleName"
                        width:90
                        text:"按标题命名"
                        enabled:setting.video.title.length > 0
                        onClicked:resourceModel.setProperty(resourceItem.rowIndex,"fileNameValue",setting.titleFileName(setting.video.title,setting.video.publishedDate,fileNameValue))
                    }
                }
            }
        }
    }
}
