import QtQuick 2.8
import Qt.labs.settings 1.0

Item {
    id:settingItem

    property alias pasteUrlFlag: pasteUrl.checked
    property alias downloadFlag: download.checked
    property alias decoFlag: decompression.checked
    property alias usePWFlag: usePW.checked
    property alias usePWListFlag: usePWList.checked
    property alias pwList: pwEdit.text

    Settings {
        property alias autoPasteUrl:pasteUrl.checked
        property alias autoDownload:download.checked
        property alias autoDeco:decompression.checked
        property alias autoUsePW:usePW.checked
        property alias autoUsePWList:usePWList.checked
        property alias usePWListFlag: usePWList.checked
        property alias pwListText: pwEdit.text
    }

    MyScrollView{
        anchors.fill: parent

        Column{
            padding:10
            spacing: 5

            CCheckBox{
                id:exitApp
                text: "关闭主面板后直接退出程序"
                checked: settings.exitDirectly
                onCheckedChanged: {
                    settings.exitDirectly = checked
                }
            }

            CCheckBox{
                id:pasteUrl
                text: "自动检测剪贴板的链接，然后更新下载链接"
                checked: true
            }

            CCheckBox{
                id:download
                text: "下载链接更新后自动下载(启动该项后请不要手动输入URL)"
                checked: false
            }

            CCheckBox{
                id:decompression
                text: "下载文件如果是压缩包则自动解压到当前文件夹"
                checked: true
            }

            CCheckBox{
                id:usePW
                text: "解压失败后使用密码重新解压"
                checked: true
                enabled: decompression.checked
            }

            CCheckBox{
                id:usePWList
                text: "启动密码库来遍历解压(分隔符是;),不启动则是默认使用域名解压"
                checked: true
                enabled: usePW.checked && decompression.checked
            }

            CTextEdit{
                id:pwEdit
                width:settingItem.width - 20
                enabled: usePWList.enabled && usePWList.checked
                text:"123;234;345"
            }
        }
    }
}
