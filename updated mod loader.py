import os
import requests
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QPushButton, QLineEdit, QTextEdit,
    QLabel, QListWidget, QListWidgetItem,
    QFileDialog
)
from PySide6.QtCore import Qt

# =========================
# CONFIG
# =========================

MODS_DIR = Path(os.environ["APPDATA"]) / ".minecraft" / "versions" / "neoforge" / "mods"
MODS_DIR.mkdir(parents=True, exist_ok=True)

MC_VERSION = "1.21.1"
LOADER = "neoforge"

search_results = {}

# =========================
# HELPERS
# =========================

def get_installed():
    return [f.name for f in MODS_DIR.glob("*.jar")]

# =========================
# MODRINTH API
# =========================

def search_mods(query):
    url = "https://api.modrinth.com/v2/search"
    r = requests.get(url, params={"query": query}).json()
    return r.get("hits", [])

def get_project(project_id):
    url = f"https://api.modrinth.com/v2/project/{project_id}"
    return requests.get(url).json()

def get_version(project_id):
    url = f"https://api.modrinth.com/v2/project/{project_id}/version"
    versions = requests.get(url).json()

    for v in versions:
        if MC_VERSION in v["game_versions"] and LOADER in v["loaders"]:
            return v

    return None

def download_mod(version):
    file = version["files"][0]
    path = MODS_DIR / file["filename"]

    if path.exists():
        return f"SKIP: {file['filename']}"

    data = requests.get(file["url"]).content

    with open(path, "wb") as f:
        f.write(data)

    return f"DOWNLOADED: {file['filename']}"

# =========================
# GUI
# =========================

class ModManager(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Minecraft Mod Manager (NeoForge)")
        self.resize(800, 600)

        layout = QVBoxLayout()

        # =========================
        # PATH WRITER (ADDED BACK)
        # =========================

        self.path_box = QLineEdit(str(MODS_DIR))
        self.path_btn = QPushButton("Set Mods Folder")
        self.path_btn.clicked.connect(self.set_path)

        layout.addWidget(QLabel("Mods Folder Path"))
        layout.addWidget(self.path_box)
        layout.addWidget(self.path_btn)

        # INSTALLED LIST
        layout.addWidget(QLabel("Installed Mods"))
        self.installed_list = QListWidget()
        layout.addWidget(self.installed_list)

        # SEARCH
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search or describe mods...")

        self.search_btn = QPushButton("Search Mods")
        self.search_btn.clicked.connect(self.search)

        layout.addWidget(self.search_box)
        layout.addWidget(self.search_btn)

        # RESULTS
        self.results = QListWidget()
        layout.addWidget(self.results)

        # BUTTONS
        self.desc_btn = QPushButton("Show Description")
        self.desc_btn.clicked.connect(self.show_description)

        self.install_btn = QPushButton("Apply Install")
        self.install_btn.clicked.connect(self.install_selected)

        layout.addWidget(self.desc_btn)
        layout.addWidget(self.install_btn)

        # LOG
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.setLayout(layout)
        self.refresh_installed()

    # =========================
    # PATH FUNCTION
    # =========================

    def set_path(self):
        global MODS_DIR

        MODS_DIR = Path(self.path_box.text().strip())
        MODS_DIR.mkdir(parents=True, exist_ok=True)

        self.log.append(f"Mods folder set to:\n{MODS_DIR}\n")
        self.refresh_installed()

    # =========================
    # UI FUNCTIONS
    # =========================

    def refresh_installed(self):
        self.installed_list.clear()
        for mod in get_installed():
            self.installed_list.addItem(mod)

    def search(self):
        query = self.search_box.text().strip()

        self.results.clear()
        search_results.clear()

        if not query:
            return

        hits = search_mods(query)

        for h in hits[:10]:
            title = h["title"]
            pid = h["project_id"]

            item = QListWidgetItem(title)
            item.setCheckState(Qt.Unchecked)

            self.results.addItem(item)
            search_results[title] = pid

    def show_description(self):
        item = self.results.currentItem()

        if not item:
            self.log.append("Select a mod first.")
            return

        pid = search_results.get(item.text())
        if not pid:
            return

        data = get_project(pid)

        self.log.append("\n====================")
        self.log.append(data.get("title", "Unknown"))
        self.log.append(data.get("description", "No description"))
        self.log.append("====================\n")

    def install_selected(self):
        for i in range(self.results.count()):
            item = self.results.item(i)

            if item.checkState() == Qt.Checked:

                name = item.text()
                pid = search_results.get(name)

                if not pid:
                    continue

                self.log.append(f"Installing {name}...")

                version = get_version(pid)

                if not version:
                    self.log.append(f"NO NeoForge 1.21.1 version: {name}")
                    continue

                result = download_mod(version)
                self.log.append(result)

        self.refresh_installed()
        self.log.append("\nDONE!")

# =========================
# RUN
# =========================

if __name__ == "__main__":
    app = QApplication([])
    window = ModManager()
    window.show()
    app.exec()