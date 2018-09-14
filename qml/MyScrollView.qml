import QtQuick 2.7
import QtQuick.Layouts 1.3
import QtQuick.Controls.Styles 1.4
import QtQuick.Controls 1.2

ScrollView {
    id:scroll
    highlightOnFocus: true

    style:ScrollViewStyle{
        id:scrollStyle
        incrementControl : Component{Rectangle{border.width: 0}}
        decrementControl : Component{Rectangle{border.width: 0}}

        scrollBarBackground : Component{
            Rectangle {
                implicitWidth: 10
                implicitHeight: 10
                color: "white"
                border.width: 0
            }
        }

        handle:Component{
            Rectangle {
                implicitWidth: 10
                implicitHeight: 10
                color: "#e6e6ec"
                radius: 3.5
                border.width: 0
            }
        }

        transientScrollBars:false

    }
}
