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
    property alias proxyEnable: useproxy.checked
    property alias proxyHostname: hostname.text
    property alias proxyPort: port.text
    property alias proxyUser: username.text
    property alias proxyPw: password.text

    signal proxyButtonClick()

    Settings {
        property alias autoPasteUrl:pasteUrl.checked
        property alias autoDownload:download.checked
        property alias autoDeco:decompression.checked
        property alias autoUsePW:usePW.checked
        property alias autoUsePWList:usePWList.checked
        property alias usePWListFlag: usePWList.checked
        property alias pwListText: pwEdit.text
        property alias proxyFlag: useproxy.checked
        property alias proxyHostname: hostname.text
        property alias proxyPort: port.text
        property alias proxyUser: username.text
        property alias proxyPw: password.text
    }

    Component.onCompleted: {
        proxyButtonClick()
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
                width:settingItem.width - 20
                onCheckedChanged: {
                    settings.exitDirectly = checked
                }
            }

            CCheckBox{
                id:pasteUrl
                text: "自动检测剪贴板的链接，然后更新下载链接"
                checked: true
                width:settingItem.width - 20
            }

            CCheckBox{
                id:download
                text: "下载链接更新后自动下载(启动该项后请不要手动输入URL)"
                checked: false
                width:settingItem.width - 20
            }

            CCheckBox{
                id:decompression
                text: "下载文件如果是压缩包则自动解压到当前文件夹"
                checked: true
                width:settingItem.width - 20
            }

            CCheckBox{
                id:usePW
                text: "解压失败后使用密码重新解压"
                checked: true
                enabled: decompression.checked
                width:settingItem.width - 20
            }

            CCheckBox{
                id:usePWList
                text: "启动密码库来遍历解压(分隔符是;),不启动则是默认使用域名解压"
                checked: true
                enabled: usePW.checked && decompression.checked
                width:settingItem.width - 20
            }

            CTextEdit{
                id:pwEdit
                width:settingItem.width - 20
                enabled: usePWList.enabled && usePWList.checked
                text:"123;234;345"
            }

            CCheckBox{
                id:useproxy
                text: "启用代理服务器"
                checked: false
                width:settingItem.width - 20
                onCheckedChanged: {
                    settingItem.proxyButtonClick()
                }
            }

            Row{
                spacing: 3
                width:settingItem.width - 20
                TextLoader{
                    text:"主机名"
                    height:hostname.height
                }

                CTextEdit{
                    id:hostname
                    width:settingItem.width/3
                    enabled: useproxy.checked
                    text:"127.0.0.1"
                }

                TextLoader{
                    text:"端口"
                    height:port.height
                }

                CTextEdit{
                    id:port
                    width:settingItem.width/3
                    enabled: useproxy.checked
                    text:"65530"
                }
            }

            Row{
                spacing: 3
                width:settingItem.width - 20
                TextLoader{
                    text:"用户名"
                    height:hostname.height
                }

                CTextEdit{
                    id:username
                    width:settingItem.width/3
                    enabled: useproxy.checked
                }

                TextLoader{
                    text:"密码"
                    height:port.height
                }

                CTextEdit{
                    id:password
                    width:settingItem.width/3
                    enabled: useproxy.checked
                    isPW: true
                }

                CPushButton{
                    id:proxyButton
                    text:"修改"
                    width:40
                    height:port.height
                    enabled: useproxy.checked
                    onClicked: settingItem.proxyButtonClick()
                }
            }
        }
    }
}
