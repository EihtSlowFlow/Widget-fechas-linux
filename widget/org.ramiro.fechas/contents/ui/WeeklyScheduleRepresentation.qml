import QtQuick
import QtQuick.Layouts
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components 3.0 as PlasmaComponents
import org.kde.kirigami as Kirigami

Item {
    id: root
    property var scheduleModel: []
    property var subjectsModel: []
    
    // Group schedule by day
    property var groupedSchedule: {
        let grouped = {};
        for (let i = 0; i < scheduleModel.length; i++) {
            let item = scheduleModel[i];
            let day = item.day_of_week;
            if (!grouped[day]) grouped[day] = [];
            grouped[day].push(item);
        }
        let result = [];
        // Hoy primero? El requerimiento dice: "Mostrar primero las materias correspondientes a hoy."
        // Y luego "Permitir recorrer el resto de los días de la semana."
        // Vamos a ordenar de hoy en adelante, y luego los previos.
        let currentDay = new Date().getDay(); 
        currentDay = currentDay === 0 ? 7 : currentDay;
        
        for (let offset = 0; offset < 7; offset++) {
            let day = currentDay + offset;
            if (day > 7) day -= 7;
            result.push({
                day_of_week: day,
                items: grouped[day] || []
            });
        }
        return result;
    }
    
    function getDayName(day) {
        const days = ["", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
        return days[day] || "";
    }
    
    function isToday(day) {
        let currentDay = new Date().getDay();
        currentDay = currentDay === 0 ? 7 : currentDay;
        return day === currentDay;
    }
    
    Flickable {
        anchors.fill: parent
        clip: true
        contentHeight: mainLayout.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        
        ColumnLayout {
            id: mainLayout
            width: parent.width
            spacing: Kirigami.Units.smallSpacing * 2
            
            // ─── Agenda Semanal ───
            Repeater {
                model: (root.scheduleModel.length > 0 || root.subjectsModel.length > 0) ? root.groupedSchedule : []
                delegate: ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing
                    
                    PlasmaComponents.Label {
                        text: (isToday(modelData.day_of_week) ? "▶ " : "") + getDayName(modelData.day_of_week) + (isToday(modelData.day_of_week) ? " (Hoy)" : "")
                        font.bold: true
                        font.pixelSize: Kirigami.Units.gridUnit * 0.8
                        color: isToday(modelData.day_of_week) ? Kirigami.Theme.highlightColor : Kirigami.Theme.textColor
                    }
                    
                    PlasmaComponents.Label {
                        visible: modelData.items.length === 0
                        text: "Sin cursada"
                        font.pixelSize: Kirigami.Units.gridUnit * 0.65
                        opacity: 0.6
                        Layout.leftMargin: Kirigami.Units.smallSpacing
                    }
                    
                    Repeater {
                        model: modelData.items
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            height: classRow.implicitHeight + Kirigami.Units.smallSpacing * 2
                            radius: Kirigami.Units.cornerRadius
                            color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g, Kirigami.Theme.backgroundColor.b, 0.4)
                            
                            RowLayout {
                                id: classRow
                                anchors.fill: parent
                                anchors.margins: Kirigami.Units.smallSpacing
                                spacing: Kirigami.Units.smallSpacing
                                
                                PlasmaComponents.Label {
                                    text: modelData.start_time + " – " + modelData.end_time
                                    font.bold: true
                                    font.pixelSize: Kirigami.Units.gridUnit * 0.7
                                    Layout.preferredWidth: Kirigami.Units.gridUnit * 4.5
                                }
                                
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    PlasmaComponents.Label {
                                        text: modelData.subject_name
                                        font.bold: true
                                        font.pixelSize: Kirigami.Units.gridUnit * 0.7
                                    }
                                    PlasmaComponents.Label {
                                        visible: modelData.location && modelData.location.length > 0
                                        text: "📍 " + modelData.location
                                        font.pixelSize: Kirigami.Units.gridUnit * 0.6
                                        opacity: 0.7
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            // ─── Separator ───
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Kirigami.Theme.textColor
                opacity: 0.1
                visible: root.groupedSchedule.length > 0 && root.subjectsModel.length > 0
            }
            
            // ─── Temario Semanal ───
            PlasmaComponents.Label {
                visible: root.subjectsModel.length > 0
                text: "Temario de la semana"
                font.bold: true
                font.pixelSize: Kirigami.Units.gridUnit * 0.8
                Layout.topMargin: Kirigami.Units.smallSpacing
            }
            
            Repeater {
                model: root.subjectsModel
                
                delegate: Rectangle {
                    Layout.fillWidth: true
                    height: subjectContent.implicitHeight + Kirigami.Units.smallSpacing * 2
                    radius: Kirigami.Units.cornerRadius
                    color: Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g, Kirigami.Theme.highlightColor.b, 0.1)
                    border.width: 1
                    border.color: Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g, Kirigami.Theme.highlightColor.b, 0.3)
                    
                    RowLayout {
                        id: subjectContent
                        anchors.fill: parent
                        anchors.margins: Kirigami.Units.smallSpacing
                        spacing: Kirigami.Units.smallSpacing
                        
                        PlasmaComponents.Label {
                            text: "📚"
                            font.pixelSize: Kirigami.Units.gridUnit * 1.2
                            Layout.alignment: Qt.AlignTop
                        }
                        
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            
                            RowLayout {
                                Layout.fillWidth: true
                                PlasmaComponents.Label {
                                    text: modelData.subject_name
                                    font.bold: true
                                    font.pixelSize: Kirigami.Units.gridUnit * 0.75
                                    color: Kirigami.Theme.highlightColor
                                }
                                Item { Layout.fillWidth: true }
                                PlasmaComponents.Label {
                                    text: "Semana " + modelData.week_number
                                    font.pixelSize: Kirigami.Units.gridUnit * 0.6
                                    opacity: 0.7
                                }
                            }
                            
                            // Units display (new model)
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                visible: modelData.units && modelData.units.length > 0

                                Repeater {
                                    model: modelData.units
                                    delegate: ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 1

                                        PlasmaComponents.Label {
                                            text: modelData.name
                                            font.bold: true
                                            font.pixelSize: Kirigami.Units.gridUnit * 0.65
                                            color: Kirigami.Theme.highlightColor
                                            opacity: 0.9
                                        }

                                        PlasmaComponents.Label {
                                            Layout.fillWidth: true
                                            visible: modelData.contents && modelData.contents.length > 0
                                            text: modelData.contents ? modelData.contents.map(c => "• " + c).join("\n") : ""
                                            font.pixelSize: Kirigami.Units.gridUnit * 0.6
                                            wrapMode: Text.WordWrap
                                            opacity: 0.8
                                        }

                                        PlasmaComponents.Label {
                                            visible: !modelData.contents || modelData.contents.length === 0
                                            text: "Sin contenidos configurados."
                                            font.pixelSize: Kirigami.Units.gridUnit * 0.6
                                            opacity: 0.5
                                            font.italic: true
                                        }
                                    }
                                }
                            }

                            PlasmaComponents.Label {
                                Layout.fillWidth: true
                                visible: (!modelData.units || modelData.units.length === 0)
                                text: "Sin contenidos asignados esta semana."
                                font.pixelSize: Kirigami.Units.gridUnit * 0.65
                                wrapMode: Text.WordWrap
                                opacity: 0.8
                            }
                        }
                    }
                }
            }
            
            // Empty state
            PlasmaComponents.Label {
                Layout.alignment: Qt.AlignHCenter
                visible: root.scheduleModel.length === 0 && root.subjectsModel.length === 0
                text: "📅 Sin agenda ni temario"
                opacity: 0.5
                font.pixelSize: Kirigami.Units.gridUnit * 0.7
                Layout.topMargin: Kirigami.Units.gridUnit * 2
            }
        }
    }
}
