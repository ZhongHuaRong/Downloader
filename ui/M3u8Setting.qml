import QtQuick 2.9
import QtQuick.Controls 1.4

Item {
    id:m3u8Item
    property string url: ""
    property string selectedVariant:""
    property var resource: setting.video.resources.length ? setting.video.resources[0] : null
    property string variantsJson:JSON.stringify(resource ? resource.variants.map(function(item){return {url:item.url,label:item.label}}) : [])
    property var selectedInfo:{
        var values = resource ? resource.variants : []
        for(var n = 0; n < values.length; n++)
            if(values[n].url == selectedVariant) return values[n]
        return values[0] || {}
    }
    property alias fileName: nameEdit.text

    function setMsg(baseUrl, name, path){
        url = baseUrl
        selectedVariant = ""
        nameEdit.text = name
        m3u8Item.parent.inspectVideo(url)
    }

    function downloadButtonClick(){
        var variants = resource ? resource.variants : []
        var selected = variants.length ? variants[Math.max(0,quality.currentIndex)].url : ""
        var options = resource ? setting.video.taskOptions(resource.id,selected) : {kind:"m3u8",url:url}
        m3u8Item.parent.videoDownload([{url:resource ? resource.url : url,name:nameEdit.text,options:options}])
    }

    MyScrollView{
        anchors.fill:parent
        Column{
            width:m3u8Item.width - 15
            spacing:10
            padding:5

            Row{
                width:parent.width - 10
                spacing:10
                TextLoader{
                    id:nameLabel
                    text:"文件名:"
                    height:nameEdit.height
                }
                CTextEdit{
                    id:nameEdit
                    objectName:"m3u8Name"
                    width:parent.width - nameLabel.width - 10
                    placeholderText:"合并后的视频文件名，例如 video.mkv"
                }
            }

            Row{
                spacing:10
                TextLoader{text:"清晰度:"; height:30}
                ComboBox{
                    id:quality
                    objectName:"m3u8Quality"
                    width:180
                    height:30
                    currentIndex:{
                        var values = JSON.parse(m3u8Item.variantsJson)
                        for(var n = 0; n < values.length; n++)
                            if(values[n].url == m3u8Item.selectedVariant) return n
                        return 0
                    }
                    onActivated:{
                        m3u8Item.selectedVariant = JSON.parse(m3u8Item.variantsJson)[currentIndex].url
                        m3u8Item.parent.inspectVideoVariant(m3u8Item.resource.id,m3u8Item.selectedVariant)
                    }
                    model:JSON.parse(m3u8Item.variantsJson).map(function(item){return item.label})
                }
            }

            TextLoader{
                objectName:"m3u8Segments"
                text:"视频分片：" + (m3u8Item.selectedInfo.segmentCount >= 0 ? m3u8Item.selectedInfo.segmentCount : m3u8Item.selectedInfo.counting ? "正在统计…" : "未获取")
            }

            TextLoader{
                width:parent.width - 10
                wrapMode:Text.Wrap
                text:setting.video.error || setting.video.status
                color:setting.video.error ? "#cc3333" : "#445266"
            }

            TextLoader{
                width:parent.width - 10
                wrapMode:Text.Wrap
                text:setting.ffmpeg.ready ? "分片将下载到临时目录，合并后的视频保存到上方下载目录。" : "请先在设置中选择并检测 FFmpeg。"
            }

            CPushButton{
                id:downloadButton
                objectName:"m3u8Download"
                text:"下载"
                enabled:nameEdit.text.trim().length > 0 && setting.ffmpeg.ready && !setting.video.busy
                onClicked:m3u8Item.downloadButtonClick()
            }
        }
    }
}
