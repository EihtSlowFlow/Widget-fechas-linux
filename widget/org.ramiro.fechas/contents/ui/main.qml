import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components 3.0 as PlasmaComponents
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root

    Plasmoid.backgroundHints: PlasmaCore.Types.DefaultBackground | PlasmaCore.Types.ConfigurableBackground

    // ─── Data Properties ─────────────────────────────────────
    property var eventsModel: []
    property var subjectsModel: []
    property var weeklyScheduleModel: []
    property string lastSync: ""
    property string syncStatus: "pending"
    property string syncError: ""
    property int eventCount: 0
    property bool isSyncing: false
    property bool pollingExistingSync: false
    property var dismissedBadges: ({}) // Collection to avoid executing mark-seen twice

    readonly property int maxVisibleEvents: Math.max(1, plasmoid.configuration.maxVisibleEvents || 20)
    readonly property var visibleEventsModel: eventsModel.slice(0, maxVisibleEvents)

    // ─── Paths (resolved dynamically at startup) ─────────────
    property string userHome: ""
    property string installDir: ""
    readonly property string cacheFilePath: userHome + "/.local/share/fechas-academicas/cache.json"
    readonly property string installPathFile: userHome + "/.config/fechas-academicas/install_path"

    // ─── Read cache via executable DataSource ────────────────
    Plasma5Support.DataSource {
        id: cacheReader
        engine: "executable"
        connectedSources: []

        onNewData: (sourceName, data) => {
            var stdout = data["stdout"];
            if (stdout && stdout.trim().length > 0) {
                try {
                    var json = JSON.parse(stdout);
                    root.lastSync = json.last_sync || "";
                    root.syncStatus = json.sync_status || "pending";
                    root.syncError = json.sync_error || "";
                    var allEvents = json.events || [];
                    root.eventsModel = allEvents.filter(function(e) { return e.is_completed !== true; });
                    root.eventCount = root.eventsModel.length;
                    root.subjectsModel = json.current_subjects || [];
                    root.weeklyScheduleModel = json.weekly_schedule || [];
                    console.log("[FechasAcadémicas] Loaded " + root.eventCount + " events, " + root.subjectsModel.length + " subjects, " + root.weeklyScheduleModel.length + " schedule entries");
                } catch (e) {
                    console.log("[FechasAcadémicas] Error parsing cache: " + e);
                }
            } else {
                console.log("[FechasAcadémicas] Empty response from: " + sourceName);
            }
            disconnectSource(sourceName);
        }
    }

    function reloadCache() {
        cacheReader.connectSource("cat " + cacheFilePath);
    }

    // ─── Launch main app ─────────────────────────────────────
    Plasma5Support.DataSource {
        id: appLauncher
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => {
            disconnectSource(sourceName);
        }
    }

    function openMainApp() {
        if (installDir) {
            appLauncher.connectSource("python3 " + installDir + "/app/main.py &");
        }
    }

    // ─── Mark event as seen ──────────────────────────────────
    Plasma5Support.DataSource {
        id: markSeenLauncher
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => {
            disconnectSource(sourceName);
        }
    }

    function markEventSeen(eventId) {
        if (!eventId || typeof eventId !== "string" || !eventId.match(/^[a-zA-Z0-9_-]+$/)) return;
        if (dismissedBadges[eventId]) return;
        
        var updated = Object.assign({}, dismissedBadges);
        updated[eventId] = true;
        dismissedBadges = updated;
        
        if (installDir) {
            markSeenLauncher.connectSource("python3 " + installDir + "/backend/event_actions.py mark-seen " + eventId);
        }
    }

    // ─── Force sync ──────────────────────────────────────────
    Plasma5Support.DataSource {
        id: syncLauncher
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => {
            var exitCode = data["exit code"];
            var stdout = data["stdout"] || "";
            
            if (exitCode === 3) {
                console.log("[FechasAcadémicas] Sync already running (code 3). Polling lock...");
                root.syncStatus = "already_running";
                root.pollingExistingSync = true;
                lockCheckTimer.start();
            } else {
                syncTimeoutTimer.stop();
                if (exitCode === 0) {
                    console.log("[FechasAcadémicas] Sync finished successfully.");
                    root.isSyncing = false;
                    reloadCache();
                } else {
                    console.log("[FechasAcadémicas] Sync error (code " + exitCode + "). Output: " + stdout);
                    root.isSyncing = false;
                    reloadCache();
                }
            }
            
            disconnectSource(sourceName);
        }
    }

    Plasma5Support.DataSource {
        id: lockCheckLauncher
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => {
            var exitCode = data["exit code"];
            
            if (exitCode === 0) {
                console.log("[FechasAcadémicas] Lock is free, reloading cache.");
                root.isSyncing = false;
                root.pollingExistingSync = false;
                syncTimeoutTimer.stop();
                reloadCache();
            } else {
                // Sigue ocupado. Volvemos a consultar si debemos seguir haciéndolo
                if (root.pollingExistingSync) {
                    lockCheckTimer.start();
                }
            }
            disconnectSource(sourceName);
        }
    }

    Timer {
        id: lockCheckTimer
        interval: 3000
        running: false
        repeat: false
        onTriggered: {
            if (installDir && root.pollingExistingSync) {
                lockCheckLauncher.connectSource("python3 " + installDir + "/backend/fechas_sync.py --check-lock");
            }
        }
    }

    Timer {
        id: syncTimeoutTimer
        interval: 120000 // 120 seconds
        running: false
        repeat: false
        onTriggered: {
            console.log("[FechasAcadémicas] Sync timed out in UI.");
            root.syncStatus = "background";
            root.pollingExistingSync = false; // Detener el polling
            root.isSyncing = false; // Habilitamos la interfaz explícitamente tras el timeout
        }
    }

    function forceSync() {
        if (installDir && !root.isSyncing) {
            root.isSyncing = true;
            root.pollingExistingSync = false;
            syncTimeoutTimer.start();
            syncLauncher.connectSource("python3 " + installDir + "/backend/fechas_sync.py");
        }
    }

    // ─── Refresh timer (reread cache every X secs) ───────────
    Timer {
        interval: Math.max(10, plasmoid.configuration.refreshIntervalSec || 60) * 1000
        running: true
        repeat: true
        onTriggered: reloadCache()
    }

    // ─── Resolve $HOME, discover install path, and initial load ──
    Plasma5Support.DataSource {
        id: homeResolver
        engine: "executable"
        connectedSources: ["echo $HOME"]
        onNewData: (sourceName, data) => {
            var home = data["stdout"].trim();
            if (home.length > 0) {
                root.userHome = home;
                console.log("[FechasAcadémicas] Home: " + home);
                // Discover install path from config file
                installPathReader.connectSource("cat " + root.installPathFile);
            }
            disconnectSource(sourceName);
        }
    }

    Plasma5Support.DataSource {
        id: installPathReader
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => {
            var path = (data["stdout"] || "").trim();
            if (path.length > 0) {
                root.installDir = path;
                console.log("[FechasAcadémicas] Install dir: " + path);
            } else {
                console.log("[FechasAcadémicas] No install_path found, app/sync buttons disabled");
            }
            reloadCache();
            disconnectSource(sourceName);
        }
    }

    Component.onCompleted: {
        // Home resolver triggers the chain: resolve home → read install_path → load cache
    }

    // ─── Widget representations ──────────────────────────────
    compactRepresentation: CompactRepresentation {}
    fullRepresentation: FullRepresentation {}

    preferredRepresentation: (plasmoid.location === PlasmaCore.Types.Desktop || plasmoid.location === PlasmaCore.Types.Floating) ? fullRepresentation : compactRepresentation

    toolTipMainText: "Fechas Académicas"
    toolTipSubText: {
        if (eventsModel.length === 0) return "Sin eventos próximos";
        var next = eventsModel[0];
        return next.title + " en " + next.days_remaining + " días";
    }
}
