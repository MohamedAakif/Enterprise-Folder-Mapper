import logging, re, socket
import subprocess, sys, os

from PySide6.QtWidgets import QApplication
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QTimer

from dotenv import load_dotenv


#log Configuration
logging.basicConfig(level=logging.WARNING, format="[%(levelname)s] %(message)s")
log = logging.getLogger("Folder Mapper")

#.env file and path configuration
if getattr(sys, 'frozen', False):
    _SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DOTENV_PATH = os.path.join(_SCRIPT_DIR, ".env")
load_dotenv(DOTENV_PATH)

HOSTNAME = os.getenv("fileserver_hostname")
folder_names = [name.strip() for name in os.getenv("FOLDER_NAMES", "").split(",")]
remap_folder_check = [check.strip() for check in os.getenv("remap_checklist", "").split(",")]

if not HOSTNAME:
    log.error("FILESERVER_HOSTNAME not found in .env — check ENV_FILE path or .env contents")
    sys.exit(1)

if not folder_names or folder_names == ['']:
    log.error("FOLDER_NAMES not found or empty in .env")
    sys.exit(1)

#Configuring GUI
app = QApplication(sys.argv)

ui_file = QFile(os.path.join(_SCRIPT_DIR, "GUI_Folder Mapper.ui"))
ui_file.open(QFile.ReadOnly)

loader = QUiLoader()
window = loader.load(ui_file)

screen = app.primaryScreen().availableGeometry()

x = (screen.width() - window.width()) //2
y = (screen.height() - window.height()) //2
window.move(x,y)
ui_file.close()

window.searchnotificationtxt.hide() # Hide the notification panel

#List of all folders
shared_folder = {
    name: fr"\\{HOSTNAME}\{name}"
    for name in folder_names
    }

#publish shared_folder list in gui
window.folderslist.addItems(shared_folder.keys())


### Supporting Functions ###
#Notification
notification_timer = QTimer()
notification_timer.setSingleShot(True)
notification_timer.timeout.connect(window.searchnotificationtxt.hide)

def show_notification(message, success=True):

    if success:
        bg_color = "#166534"      # Dark Green
        border = "#22C55E"
    else:
        bg_color = "#991B1B"      # Dark Red
        border = "#EF4444"

    window.searchnotificationtxt.setStyleSheet(f"""
        QLabel {{
            background-color: {bg_color};
            color: white;
            border: 1px solid {border};
            border-radius: 8px;
            padding: 6px;
            font-weight: bold;
        }}
    """)

    window.searchnotificationtxt.setText(message)
    window.searchnotificationtxt.show()
    notification_timer.start(5000)
    QApplication.processEvents()

#Drive letter verification
def get_available_drive(prefered_letter, used_drives):
    drive_letter = prefered_letter.upper()

    while (
        os.path.exists(f"{drive_letter}:\\") 
        or f"{drive_letter}:" in used_drives
        ):
            if drive_letter >= "Z":
                return None
            drive_letter = chr(ord(drive_letter)+1)
    return f"{drive_letter}:"

#Find Existing Mapped Folder
def get_existing_mapping(unc_path):
    result = subprocess.run(["net", "use"], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        m = re.search(r"([A-Z]:)\s+(\\\\.+?)(?=\s{2,}|$)", line)
        if m and m.group(2).strip().lower() == unc_path.lower():
            return m.group(1)
    return None

#Network Verification
def server_reachability(hostname, port=445, timeout=2):
    try:
        with socket.create_connection((hostname, port), timeout=timeout):
            return True
    except (socket.timeout, OSError):
        return False

#Folder Existence Check
def folder_exists(unc_path):
    return os.path.exists(unc_path)

### Main Functions ###
#Mapping Selected Items

def mapfolders():
    show_notification(f"⌛Starting Mapping Process", True)
    if not server_reachability(HOSTNAME):
        log.error(f"Server '{HOSTNAME}' is not reachable. Aborting map operation.")
        show_notification(f"❌ Server '{HOSTNAME}' is not reachable", False)
        return

    selected_items = window.folderslist.selectedItems()
    used_drives = set()

    if not selected_items:
        log.warning("No Folders Selected")
        show_notification("❌ Invalid: No Folders Selected", False)
        return

    success_count = 0
    failed_count = 0
    skipped_count = 0

    for item in selected_items:

        folder_name = item.text()
        unc_path = shared_folder.get(folder_name)
        if not unc_path:
            log.warning(f"No path found for {folder_name}")
            failed_count += 1
            continue

        if not folder_exists(unc_path):
            log.warning(f"Folder does not exist or is unreachable: {unc_path}")
            failed_count += 1
            continue

        existing_drive = get_existing_mapping(unc_path)
        if existing_drive:
            log.info(f"{folder_name} already mapped to {existing_drive}")
            show_notification(f"ℹ️ {folder_name} already mapped to {existing_drive}", True)
            skipped_count += 1
            continue

        drive = get_available_drive(folder_name[0], used_drives)

        if drive is None:
            log.warning(f"No available drive letter for {folder_name}")
            failed_count += 1
            continue
        used_drives.add(drive)

        try:
            subprocess.run(
                ["net", "use", drive, unc_path, "/persistent:yes"],
                check=True
                )
            log.info(f"Mapped {drive} -> {unc_path}")
            success_count += 1

        except subprocess.CalledProcessError as e:
            log.warning(f"Command 'net use {drive} {unc_path}' failed : {e}")
            failed_count += 1
    
        except Exception as e:
            log.error(f"Unexpected error: {e}")
            failed_count += 1

    if failed_count == 0 and success_count == 0 and skipped_count > 0:
        show_notification(f"ℹ️ All {skipped_count} folder(s) already mapped", True)
    elif failed_count == 0:
        msg = f"✅ Mapped {success_count} folder(s)"
        if skipped_count:
            msg += f", {skipped_count} already mapped"
        show_notification(msg, True)
    else:
        msg = f"⚠️ Mapped {success_count}, failed {failed_count}"
        if skipped_count:
            msg += f", {skipped_count} already mapped"
        show_notification(msg, False)

window.mapselectedbutton.clicked.connect(mapfolders)

# Remove all mapped folder button
def removeallfolders(drives_to_Remove=None, notify=True):
    remove_count = 0
    if notify:
        show_notification(f"⌛Starting Removing Process", True)
    try:
        if drives_to_Remove is None:
            drives_to_Remove = []
            currentfolders = subprocess.run(["net", "use"],
                capture_output=True,
                text=True
            )

            if currentfolders.returncode != 0:
                log.warning(f"'net use' returned non-zero: {currentfolders.stderr}")

            for line in currentfolders.stdout.splitlines():
                m = re.search(r"([A-Z]:)\s+(\\\\.+?)(?=\s{2,}|$)", line)
                if not m:
                    continue
                unc_path = m.group(2).strip()

                for check in remap_folder_check:
                    if check.lower() in unc_path.lower():
                        drive = m.group(1)
                        drives_to_Remove.append(drive)
                        break
        for drive in drives_to_Remove:
            try:
                subprocess.run(
                    ["net", "use", drive, "/delete", "/y"], 
                    check=True)
                remove_count += 1
            except subprocess.CalledProcessError as e:
                log.warning(f"Remove failed : {e}")

    except Exception as e:
        log.error(f"Unexpected error: {e}")

    log.info(f"Removed {remove_count} mapped folder(s)")

    if notify:
        if remove_count == 0:
            show_notification("⚠️ No mapped folders found to remove", False)
        else:
            show_notification(f"✅ Removed {remove_count} mapped folder(s)", True)

window.removebutton.clicked.connect(lambda: removeallfolders())

# Remap all folder
def remapfolders():
    shares_to_remap = set()
    drives_found = set()
    used_drives = set()
    show_notification(f"⌛Starting Remapping Process", True)

    failed_count = 0
    success_count = 0

    if not server_reachability(HOSTNAME):
        log.error(f"Server '{HOSTNAME}' is not reachable. Aborting remap operation.")
        show_notification(f"❌ Server '{HOSTNAME}' is not reachable", False)
        return

    try:
        currentfolders = subprocess.run(["net", "use"],
            capture_output=True,
            text=True
        )

        if currentfolders.returncode != 0:
            log.warning(f"'net use' returned non-zero: {currentfolders.stderr}")
            show_notification(f"❌ Invalid: No available mapped folders", False)
            return

        for line in currentfolders.stdout.splitlines():
            m = re.search(r"([A-Z]:)\s+(\\\\.+?)(?=\s{2,}|$)", line)
            if not m:
                continue
            unc_path = m.group(2).strip()

            for check in remap_folder_check:
                if check.lower() in unc_path.lower():
                    shares_to_remap.add(unc_path)
                    drives_found.add(m.group(1))
                    break
        log.info(f"Found {len(shares_to_remap)} shares to remap")

        removeallfolders(drives_found, notify=False)

        for old_unc in shares_to_remap:
            new_unc = old_unc

            for check in remap_folder_check:
                new_unc = re.sub(
                    re.escape(check),
                    HOSTNAME,
                    new_unc,
                    flags=re.IGNORECASE
                    )
            parts = [p for p in new_unc.split("\\") if p]
            if len(parts) < 2:
                log.warning(f"Could not parse share name from: {new_unc}")
                failed_count += 1
                continue

            share_name = parts[1]

            if not folder_exists(new_unc):
                log.warning(f"Folder does not exist or is unreachable: {new_unc}")
                failed_count += 1
                continue

            drive = get_available_drive(share_name[0], used_drives)

            if drive is None:
                log.warning(f"No available drive letter for {share_name}")
                failed_count += 1
                continue

            used_drives.add(drive)

            try:
                subprocess.run(
                    ["net","use",drive,new_unc,"/persistent:yes"],
                    check=True
                    )
                log.info(f"Mapped {drive} -> {new_unc}")
                success_count += 1

            except subprocess.CalledProcessError as e:
                log.warning(f"Remap failed : {e}")
                failed_count += 1

            except Exception as e:
                log.error(f"Unexpected error: {e}")
                failed_count += 1  

    except Exception as e:
        log.error(f"Unexpected error: {e}")

    if not shares_to_remap:
        show_notification("⚠️ No matching shares found to remap", False)
    elif failed_count == 0:
        show_notification(f"✅ Remapped {success_count} folder(s)", True)
    else:
        show_notification(f"⚠️ Remapped {success_count}, failed {failed_count}", False)


window.remapbutton.clicked.connect(remapfolders)

#closing all
window.show()
window.raise_()
window.activateWindow()
sys.exit(app.exec())