import QtQuick
import QtQuick.Layouts
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components 3.0 as PlasmaComponents
import org.kde.kirigami as Kirigami

Item {
    id: fullRoot

    Layout.preferredWidth: Kirigami.Units.gridUnit * 24
    Layout.preferredHeight: Kirigami.Units.gridUnit * 20
    Layout.minimumWidth: Kirigami.Units.gridUnit * 18
    Layout.minimumHeight: Kirigami.Units.gridUnit * 14

    function urgencyColor(urgency) {
        switch (urgency) {
            case "red":    return "#F44336";
            case "orange": return "#FF9800";
            case "yellow": return "#FFC107";
            case "green":  return "#4CAF50";
            default:       return Kirigami.Theme.textColor;
        }
    }

    function groupLabel(daysRemaining) {
        if (daysRemaining < 0) return "⚠ Vencidos";
        if (daysRemaining === 0) return "🔴 Hoy";
        if (daysRemaining <= 2) return "🟠 Próximos días";
        if (daysRemaining <= 7) return "🟡 Esta semana";
        return "🟢 Más adelante";
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Kirigami.Units.smallSpacing * 2
        spacing: Kirigami.Units.smallSpacing

        // ─── Header ─────────────────────────────────────────
        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            Kirigami.Icon {
                source: "view-calendar-upcoming-events"
                Layout.preferredWidth: Kirigami.Units.iconSizes.small
                Layout.preferredHeight: Kirigami.Units.iconSizes.small
            }

            PlasmaComponents.Label {
                text: "Fechas Académicas"
                font.bold: true
                font.pixelSize: Kirigami.Units.gridUnit * 0.85
                Layout.fillWidth: true
            }

            PlasmaComponents.Label {
                text: root.eventCount + " eventos"
                font.pixelSize: Kirigami.Units.gridUnit * 0.6
                opacity: 0.6
            }
        }

        // ─── Separator ──────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Kirigami.Theme.textColor
            opacity: 0.1
        }

        // ─── Subjects List ──────────────────────────────────
        ListView {
            id: subjectsList
            Layout.fillWidth: true
            Layout.preferredHeight: contentHeight
            Layout.maximumHeight: Kirigami.Units.gridUnit * 8
            visible: root.subjectsModel && root.subjectsModel.length > 0
            interactive: false
            spacing: Kirigami.Units.smallSpacing
            
            model: root.subjectsModel
            
            delegate: Rectangle {
                width: subjectsList.width
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
                                text: "Semana " + modelData.week_number + " (Día " + modelData.day_of_week + "/7)"
                                font.pixelSize: Kirigami.Units.gridUnit * 0.6
                                opacity: 0.7
                            }
                        }
                        
                        PlasmaComponents.Label {
                            Layout.fillWidth: true
                            text: {
                                if (modelData.topics && modelData.topics.length > 0) {
                                    return modelData.topics.map(t => "• " + t).join("\n");
                                }
                                return "Sin temas asignados esta semana.";
                            }
                            font.pixelSize: Kirigami.Units.gridUnit * 0.65
                            wrapMode: Text.WordWrap
                            opacity: 0.8
                        }
                    }
                }
            }
        }
        
        // Separator if subjects exist
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Kirigami.Theme.textColor
            opacity: 0.1
            visible: root.subjectsModel && root.subjectsModel.length > 0
        }

        // ─── Event list ─────────────────────────────────────
        ListView {
            id: eventList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 2
            boundsBehavior: Flickable.StopAtBounds

            model: root.eventsModel

            // Group section headers
            section.property: "urgency"
            section.delegate: Item {
                width: eventList.width
                height: Kirigami.Units.gridUnit * 1.2

                PlasmaComponents.Label {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: {
                        // Map urgency to group label
                        switch (section) {
                            case "red": return "🔴 Urgente";
                            case "orange": return "🟠 Próximos días";
                            case "yellow": return "🟡 Esta semana";
                            case "green": return "🟢 Más adelante";
                            default: return section;
                        }
                    }
                    font.bold: true
                    font.pixelSize: Kirigami.Units.gridUnit * 0.6
                    opacity: 0.7
                }
            }

            delegate: Rectangle {
                width: eventList.width
                height: Kirigami.Units.gridUnit * 3
                radius: Kirigami.Units.cornerRadius
                color: Qt.rgba(
                    Kirigami.Theme.backgroundColor.r,
                    Kirigami.Theme.backgroundColor.g,
                    Kirigami.Theme.backgroundColor.b,
                    mouseArea.containsMouse ? 0.8 : 0.4
                )

                // Urgency left border
                Rectangle {
                    width: 3
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    radius: Kirigami.Units.cornerRadius
                    color: urgencyColor(modelData.urgency)
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: Kirigami.Units.smallSpacing
                    spacing: Kirigami.Units.smallSpacing

                    // Days counter
                    PlasmaComponents.Label {
                        Layout.preferredWidth: Kirigami.Units.gridUnit * 2.5
                        horizontalAlignment: Text.AlignHCenter
                        text: modelData.days_remaining === 0 ? "HOY" :
                              modelData.days_remaining < 0 ? "⚠" :
                              modelData.days_remaining + "d"
                        font.bold: true
                        font.pixelSize: Kirigami.Units.gridUnit * 0.8
                        color: urgencyColor(modelData.urgency)
                    }

                    // Event info
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1

                        PlasmaComponents.Label {
                            Layout.fillWidth: true
                            text: modelData.title
                            font.pixelSize: Kirigami.Units.gridUnit * 0.65
                            font.bold: true
                            elide: Text.ElideRight
                            maximumLineCount: 1
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            PlasmaComponents.Label {
                                text: modelData.source_name || ""
                                font.pixelSize: Kirigami.Units.gridUnit * 0.5
                                opacity: 0.5
                                elide: Text.ElideRight
                            }

                            PlasmaComponents.Label {
                                text: "•"
                                font.pixelSize: Kirigami.Units.gridUnit * 0.5
                                opacity: 0.3
                            }

                            PlasmaComponents.Label {
                                text: {
                                    function fmt(iso) {
                                        var d = new Date(iso);
                                        var months = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];
                                        return d.getDate() + " " + months[d.getMonth()];
                                    }
                                    try {
                                        if (modelData.start_date && modelData.start_date.length > 0) {
                                            return fmt(modelData.start_date) + " → " + fmt(modelData.due_date);
                                        } else {
                                            return fmt(modelData.due_date);
                                        }
                                    } catch (e) { return ""; }
                                }
                                font.pixelSize: Kirigami.Units.gridUnit * 0.5
                                opacity: 0.5
                            }
                        }
                    }

                    // "Nuevo" badge
                    Rectangle {
                        visible: modelData.is_new === true
                        Layout.alignment: Qt.AlignVCenter
                        Layout.preferredWidth: newLbl.implicitWidth + 8
                        Layout.preferredHeight: newLbl.implicitHeight + 4
                        radius: height / 2
                        color: "#2196F3"

                        PlasmaComponents.Label {
                            id: newLbl
                            anchors.centerIn: parent
                            text: "🆕"
                            font.pixelSize: Kirigami.Units.gridUnit * 0.45
                        }
                    }
                }

                MouseArea {
                    id: mouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                }
            }

            // Empty state
            PlasmaComponents.Label {
                anchors.centerIn: parent
                visible: root.eventCount === 0
                text: "📅 Sin eventos próximos\nAgregá eventos desde la aplicación"
                horizontalAlignment: Text.AlignHCenter
                opacity: 0.5
                font.pixelSize: Kirigami.Units.gridUnit * 0.7
            }
        }

        // ─── Separator ──────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Kirigami.Theme.textColor
            opacity: 0.1
        }

        // ─── Footer: Sync status + Action buttons ───────────
        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            SyncIndicator {
                compact: false
            }

            Item { Layout.fillWidth: true }

            PlasmaComponents.ToolButton {
                icon.name: "view-refresh"
                PlasmaComponents.ToolTip { text: "Sincronizar ahora" }
                onClicked: root.forceSync()
            }

            PlasmaComponents.ToolButton {
                icon.name: "configure"
                PlasmaComponents.ToolTip { text: "Abrir Centro de Gestión" }
                onClicked: root.openMainApp()
            }
        }
    }
}
