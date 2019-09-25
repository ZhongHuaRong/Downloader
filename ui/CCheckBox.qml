import QtQuick 2.0
import QtQuick.Controls.Styles 1.4
import QtQuick.Controls 1.2

CheckBox {
    id: cCheckBox
    text: qsTr("")
    width:100
    height:30
    style:CheckBoxStyle{
        label: Component{
            Label{
                color: enabled?"#445266":"#cdcdcd"
                font.pixelSize: 14
                font.family: "黑体"
                text:cCheckBox.text
            }
        }
    }
}
