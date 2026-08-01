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
    property string lastSync: ""
    property string syncStatus: "pending"
    property string syncError: ""
    property int eventCount: 0
    property bool isSyncing: false

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
                    root.eventsModel = json.events || [];
                    root.eventCount = root.eventsModel.length;
                    root.subjectsModel = json.current_subjects || [];
                    console.log("[FechasAcadémicas] Loaded " + root.eventCount + " events, " + root.subjectsModel.length + " subjects");
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

    // ─── Force sync ──────────────────────────────────────────
    Plasma5Support.DataSource {
        id: syncLauncher
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => {
            var exitCode = data["exit code"];
            var stdout = data["stdout"] || "";
            
            syncTimeoutTimer.stop();
            
            if (exitCode === 3) {
                console.log("[FechasAcadémicas] Sync already running (code 3).");
                root.syncStatus = "already_running";
                delayedReloadTimer.start();
            } else if (exitCode === 0) {
                console.log("[FechasAcadémicas] Sync finished successfully.");
                reloadCache();
            } else {
                console.log("[FechasAcadémicas] Sync error (code " + exitCode + "). Output: " + stdout);
                reloadCache();
            }
            
            root.isSyncing = false;
            disconnectSource(sourceName);
        }
    }

    Timer {
        id: delayedReloadTimer
        interval: 3000
        running: false
        repeat: false
        onTriggered: {
            // Restore status from cache if we temporarily set it to already_running
            if (root.syncStatus === "already_running") {
                root.syncStatus = "pending"; // Fallback, reloadCache will overwrite it
            }
            reloadCache();
        }
    }

    Timer {
        id: syncTimeoutTimer
        interval: 120000 // 120 seconds
        running: false
        repeat: false
        onTriggered: {
            console.log("[FechasAcadémicas] Sync timed out in UI.");
            root.isSyncing = false;
            root.syncStatus = "background";
        }
    }

    function forceSync() {
        if (installDir && !root.isSyncing) {
            root.isSyncing = true;
            syncTimeoutTimer.start();
            syncLauncher.connectSource("python3 " + installDir + "/backend/fechas_sync.py");
        }
    }

    // ─── Refresh timer (reread cache every 60s) ──────────────
    Timer {
        interval: 60000
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
        if (eventCount === 0) return "Sin eventos próximos";
        var next = eventsModel[0];
        if (!next) return "";
        return next.title + " en " + next.days_remaining + " días";
    }
}
