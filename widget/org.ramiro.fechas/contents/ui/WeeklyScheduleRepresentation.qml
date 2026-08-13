import QtQuick
import QtQuick.Layouts
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components 3.0 as PlasmaComponents
import org.kde.kirigami as Kirigami

Item {
    id: root
    property var scheduleModel: []
    property var subjectsModel: []
    property var todayWeather: null
    property var returnWeather: null
    
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
    
    function getWeatherIcon(code, isDay) {
        var dayIcons = {0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️", 45: "🌫️", 48: "🌫️", 51: "🌦️", 53: "🌦️", 55: "🌧️", 61: "🌧️", 63: "🌧️", 65: "🌧️", 71: "🌨️", 73: "🌨️", 75: "🌨️", 80: "🌦️", 81: "🌧️", 82: "🌧️", 95: "⛈️", 96: "⛈️", 99: "⛈️"};
        var nightIcons = {0: "🌙", 1: "🌙", 2: "☁️", 3: "☁️"};
        if (!isDay && nightIcons[code] !== undefined) return nightIcons[code];
        return dayIcons[code] !== undefined ? dayIcons[code] : "🌡️";
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
                model: (root.scheduleModel.length > 0 || root.subjectsModel.length > 0 || root.todayWeather !== null) ? root.groupedSchedule : []
                delegate: ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing
                    
                    PlasmaComponents.Label {
                        text: (isToday(modelData.day_of_week) ? "▶ " : "") + getDayName(modelData.day_of_week) + (isToday(modelData.day_of_week) ? " (Hoy)" : "")
                        font.bold: true
                        font.pixelSize: Kirigami.Units.gridUnit * 0.8
                        color: isToday(modelData.day_of_week) ? Kirigami.Theme.highlightColor : Kirigami.Theme.textColor
                    }
                    
                    // ─── Bloque meteorológico (solo hoy) ───
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing
                        visible: isToday(modelData.day_of_week) && root.todayWeather !== null

                        // Clima actual
                        Rectangle {
                            Layout.fillWidth: true
                            height: weatherCurrentRow.implicitHeight + Kirigami.Units.smallSpacing * 2
                            radius: Kirigami.Units.cornerRadius
                            color: Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g, Kirigami.Theme.highlightColor.b, 0.15)
                            visible: root.todayWeather && root.todayWeather.current

                            RowLayout {
                                id: weatherCurrentRow
                                anchors.fill: parent
                                anchors.margins: Kirigami.Units.smallSpacing
                                spacing: Kirigami.Units.smallSpacing

                                PlasmaComponents.Label {
                                    text: {
                                        if (!root.todayWeather || !root.todayWeather.current) return "";
                                        var c = root.todayWeather.current;
                                        var icon = getWeatherIcon(c.weather_code, c.is_day);
                                        var loc = root.todayWeather.location_name || "";
                                        return icon + " " + Math.round(c.temperature) + " °C · Sensación " + Math.round(c.apparent_temperature) + " °C";
                                    }
                                    font.pixelSize: Kirigami.Units.gridUnit * 0.7
                                    font.bold: true
                                }

                                Item { Layout.fillWidth: true }

                                PlasmaComponents.Label {
                                    visible: root.todayWeather && root.todayWeather.location_name
                                    text: root.todayWeather ? ("📍 " + (root.todayWeather.location_name || "")) : ""
                                    font.pixelSize: Kirigami.Units.gridUnit * 0.55
                                    opacity: 0.7
                                }
                            }
                        }

                        // Aviso de dato desactualizado
                        PlasmaComponents.Label {
                            visible: root.todayWeather && root.todayWeather.is_stale === true
                            text: "⚠ Pronóstico sin actualizar"
                            font.pixelSize: Kirigami.Units.gridUnit * 0.55
                            font.italic: true
                            opacity: 0.6
                        }

                        // Pronóstico horario compacto
                        Flow {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing
                            visible: root.todayWeather && root.todayWeather.hourly && root.todayWeather.hourly.length > 0

                            Repeater {
                                model: {
                                    if (!root.todayWeather || !root.todayWeather.hourly) return [];
                                    var currentHourStr = root.todayWeather.current && root.todayWeather.current.time ? root.todayWeather.current.time.substring(11, 13) : "00";
                                    var currentHour = parseInt(currentHourStr);
                                    var targetHour = 23;
                                    
                                    if (root.returnWeather && root.returnWeather.status === "upcoming" && root.returnWeather.estimated_return_at) {
                                        var targetStr = root.returnWeather.estimated_return_at;
                                        // Verificar si la fecha de estimación es la misma fecha del current_time
                                        var currentDay = root.todayWeather.current && root.todayWeather.current.time ? root.todayWeather.current.time.substring(0, 10) : "";
                                        if (currentDay && targetStr.substring(0, 10) === currentDay) {
                                            targetHour = parseInt(targetStr.substring(11, 13)) + 1;
                                            if (targetHour > 23) targetHour = 23;
                                        }
                                    }

                                    var filtered = [];
                                    for (var i = 0; i < root.todayWeather.hourly.length; i++) {
                                        var h = root.todayWeather.hourly[i];
                                        var hourStr = h.time ? h.time.substring(11, 13) : "";
                                        var hour = parseInt(hourStr);
                                        if (hour >= currentHour && hour <= targetHour) {
                                            filtered.push(h);
                                        }
                                    }
                                    return filtered;
                                }

                                delegate: Rectangle {
                                    width: Kirigami.Units.gridUnit * 3.2
                                    height: Kirigami.Units.gridUnit * 3
                                    radius: Kirigami.Units.cornerRadius
                                    color: {
                                        // Resaltar hora de fin de actividad
                                        if (root.returnWeather && root.returnWeather.status === "upcoming" && root.returnWeather.last_activity) {
                                            var endTime = root.returnWeather.last_activity.end_time;
                                            var hourStr = modelData.time ? modelData.time.substring(11, 16) : "";
                                            if (endTime && hourStr.substring(0, 2) === endTime.substring(0, 2)) {
                                                return Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g, Kirigami.Theme.highlightColor.b, 0.25);
                                            }
                                        }
                                        return Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g, Kirigami.Theme.backgroundColor.b, 0.4);
                                    }
                                    border.width: {
                                        if (root.returnWeather && root.returnWeather.status === "upcoming" && root.returnWeather.last_activity) {
                                            var endTime2 = root.returnWeather.last_activity.end_time;
                                            var hourStr2 = modelData.time ? modelData.time.substring(11, 16) : "";
                                            if (endTime2 && hourStr2.substring(0, 2) === endTime2.substring(0, 2)) return 1;
                                        }
                                        return 0;
                                    }
                                    border.color: Kirigami.Theme.highlightColor

                                    ColumnLayout {
                                        anchors.centerIn: parent
                                        spacing: 1

                                        PlasmaComponents.Label {
                                            Layout.alignment: Qt.AlignHCenter
                                            text: modelData.time ? modelData.time.substring(11, 16) : ""
                                            font.pixelSize: Kirigami.Units.gridUnit * 0.5
                                            font.bold: true
                                            opacity: 0.7
                                        }
                                        PlasmaComponents.Label {
                                            Layout.alignment: Qt.AlignHCenter
                                            text: getWeatherIcon(modelData.weather_code, modelData.is_day)
                                            font.pixelSize: Kirigami.Units.gridUnit * 0.8
                                        }
                                        PlasmaComponents.Label {
                                            Layout.alignment: Qt.AlignHCenter
                                            text: Math.round(modelData.temperature) + "°"
                                            font.pixelSize: Kirigami.Units.gridUnit * 0.55
                                            font.bold: true
                                        }
                                    }
                                }
                            }
                        }

                        // Bloque vuelta a casa
                        Rectangle {
                            Layout.fillWidth: true
                            visible: root.returnWeather !== null && root.returnWeather.status === "upcoming"
                            height: returnCol.implicitHeight + Kirigami.Units.smallSpacing * 2
                            radius: Kirigami.Units.cornerRadius
                            color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g, Kirigami.Theme.backgroundColor.b, 0.5)
                            border.width: 1
                            border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.1)

                            ColumnLayout {
                                id: returnCol
                                anchors.fill: parent
                                anchors.margins: Kirigami.Units.smallSpacing
                                spacing: 2

                                PlasmaComponents.Label {
                                    text: {
                                        if (!root.returnWeather || !root.returnWeather.last_activity) return "";
                                        var act = root.returnWeather.last_activity;
                                        var endIcon = root.returnWeather.weather_at_end ? getWeatherIcon(root.returnWeather.weather_at_end.weather_code, root.returnWeather.weather_at_end.is_day) : "";
                                        return endIcon + " Al terminar " + act.subject_name + " — " + act.end_time;
                                    }
                                    font.bold: true
                                    font.pixelSize: Kirigami.Units.gridUnit * 0.7
                                }

                                PlasmaComponents.Label {
                                    text: {
                                        if (!root.returnWeather) return "";
                                        var w = null;
                                        if (root.returnWeather.return_temperature !== null && root.returnWeather.return_temperature !== undefined) {
                                            w = root.returnWeather.weather_at_return || root.returnWeather.weather_at_end;
                                        } else {
                                            return "Pronóstico de regreso no disponible para hoy.";
                                        }
                                        if (!w) return "";
                                        
                                        var line = Math.round(w.temperature) + " °C · Sensación " + Math.round(w.apparent_temperature) + " °C";
                                        if (w.precipitation_probability !== null && w.precipitation_probability !== undefined) {
                                            line += " · Lluvia " + w.precipitation_probability + " %";
                                        }
                                        if (w.wind_speed !== null && w.wind_speed !== undefined) {
                                            line += " · Viento " + Math.round(w.wind_speed) + " km/h";
                                        }
                                        return line;
                                    }
                                    font.pixelSize: Kirigami.Units.gridUnit * 0.6
                                    opacity: 0.8
                                }

                                PlasmaComponents.Label {
                                    visible: root.returnWeather && root.returnWeather.temperature_diff !== null && root.returnWeather.temperature_diff !== undefined
                                    text: {
                                        if (!root.returnWeather || root.returnWeather.current_temperature === null || root.returnWeather.current_temperature === undefined) return "";
                                        if (root.returnWeather.return_temperature === null || root.returnWeather.return_temperature === undefined) return "";
                                        var curr = Math.round(root.returnWeather.current_temperature);
                                        var end = Math.round(root.returnWeather.return_temperature);
                                        var diff = root.returnWeather.temperature_diff;
                                        var arrow = diff < 0 ? "↓" : (diff > 0 ? "↑" : "→");
                                        var labelStr = (root.returnWeather.return_trip_minutes !== undefined && root.returnWeather.return_trip_minutes === 0) ? "Al terminar " : "Vuelta ";
                                        return "Ahora " + curr + " °C → " + labelStr + end + " °C (" + arrow + Math.abs(Math.round(diff)) + " °C)";
                                    }
                                    font.pixelSize: Kirigami.Units.gridUnit * 0.55
                                    font.bold: true
                                    color: {
                                        if (!root.returnWeather) return Kirigami.Theme.textColor;
                                        var diff = root.returnWeather.temperature_diff;
                                        if (diff < -5) return "#64B5F6"; // Refresca mucho
                                        if (diff < 0) return "#90CAF9";  // Refresca algo
                                        if (diff > 5) return "#FF8A65";  // Calienta mucho
                                        return Kirigami.Theme.textColor;
                                    }
                                }
                            }
                        }

                        // Actividades finalizadas
                        PlasmaComponents.Label {
                            Layout.fillWidth: true
                            visible: root.returnWeather !== null && root.returnWeather.status === "completed" && isToday(modelData.day_of_week)
                            text: "✔ Las actividades de hoy ya finalizaron."
                            font.pixelSize: Kirigami.Units.gridUnit * 0.6
                            font.italic: true
                            opacity: 0.6
                        }
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
