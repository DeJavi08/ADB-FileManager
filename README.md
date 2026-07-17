# 📱 Android Backup Professional

<div align="center">

![Android](https://img.shields.io/badge/Android-Backup-blue?style=for-the-badge&logo=android)
![Python](https://img.shields.io/badge/Python-3.10+-green?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-Web%20UI-red?style=for-the-badge&logo=flask)
![Windows](https://img.shields.io/badge/Windows-Native-0078D6?style=for-the-badge&logo=windows)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**Professional Android Backup Tool with Web Interface, Streaming Pipeline & Resume Support**

[Features](#-features) • [System Requirements](#-system-requirements) • [Installation](#-installation) • [Usage Guide](#-usage-guide) • [Troubleshooting](#-troubleshooting)

</div>

---

## 📸 Screenshots

<div align="center">
  <img src="https://raw.githubusercontent.com/DeJavi08/ADB-FileManager/420a4a127b53b973fdd4782705bbc88ceac9a4e6/Demo.png" alt="Android Backup Professional UI" width="90%">
  <br>
  <em>Web interface with File Manager, Real-time Progress, and Activity Log</em>
</div>

---

## ✨ Features

### 🚀 Core Features
* **Streaming Pipeline** – Data streams directly from Android to computer without temporary files.
* **ADB exec-out** – Uses optimized `adb exec-out` for maximum transfer speed.
* **No Temp Files** – Direct streaming pipeline: Android → `tar` → `adb` → Windows `tar` → Destination.
* **Real-time Progress** – Live monitoring with speed, ETA, percentage, and file count.

### 📂 File Manager
* **Browse Android Folders** – Navigate your Android file system directly from the web UI.
* **Show/Hide Files** – Toggle between viewing folders only or all items.
* **Smart File Icons** – Visual distinction for images, videos, audio, documents, and archives.
* **Quick Navigation** – One-click shortcuts to Home (`/sdcard/`), DCIM, and parent folders.

### 💾 Backup Controls
* **Flexible Destination** – Choose any Windows folder with a built-in native folder browser.
* **Open Output Folder** – Open the backup destination directly in Windows Explorer from the UI.
* **Resume Support** – Auto-detect and seamlessly resume interrupted backups.
* **Stop/Start Controls** – Full control to pause or cancel the backup process at any time.

### 📊 Real-time Monitoring
* **Progress Bar** – Visual percentage indicator.
* **Speed Tracking** – Displays current and average transfer speeds.
* **ETA Calculator** – Smart estimation of remaining time.
* **Activity Log** – Timestamped, color-coded event logging for easy debugging.

---

## 🖥️ System Requirements

| Requirement | Details |
| :--- | :--- |
| **OS** | Windows 10 / 11 (Native) |
| **Python** | 3.10 or higher |
| **ADB** | Android Platform Tools (installed and added to system **PATH**) |
| **Android** | Device with USB Debugging enabled |
| **Browser** | Chrome, Firefox, Edge, or any modern web browser |

---

## 📦 Installation

### 1. Clone Repository
```bash
git clone [https://github.com/DeJavi08/ADB-FileManager.git](https://github.com/DeJavi08/ADB-FileManager.git)
cd ADB-FileManager

```

### 2. Install Dependencies

```bash
pip install -r requirements.txt

```

### 3. Setup ADB

1. Download **Android Platform Tools** for Windows.
2. Extract the zip file and add the folder path to your system **PATH** environment variable.

### 4. Enable USB Debugging on Android

1. Go to **Settings** → **About Phone** → Tap **Build Number** 7 times.
2. Go back to **Settings** → **System** (or Developer Options) → Enable **USB Debugging**.

### 5. Run the Application

```bash
python backup_app.py

```

### 6. Open Web Interface

Navigate to [http://localhost:5000](http://localhost:5000) in your browser.

---

## 🚀 Usage Guide

### Quick Start

1. Connect your Android device via USB with USB Debugging enabled.
2. Launch the app and open `http://localhost:5000`.
3. Browse or enter your target source folder (e.g., `/sdcard/DCIM/`).
4. Select your backup destination folder on the computer.
5. Click **Start Backup** and monitor the live progress.

### File Manager Navigation

| Action | Description |
| --- | --- |
| **Click Folder** | Navigate deeper into the selected directory. |
| **Click "Select"** | Set the current folder as the backup source. |
| **📷 DCIM** | Quick jump straight to the camera folder. |
| **🏠 Home** | Return to the root user storage (`/sdcard/`). |
| **🔄 Refresh** | Reload the current folder contents. |
| **📄 Show/Hide Files** | Toggle the visibility of files within folders. |

### Backup Controls

| Button | Function |
| --- | --- |
| ▶ **Start Backup** | Begin the data streaming process. |
| ⏹ **Stop** | Gracefully halt the running backup. |
| 📂 **Browse** | Open native Windows folder picker to choose destination. |
| 📁 **Open** | Open the designated destination folder in Windows Explorer. |

---

## 📁 Project Structure

```text
android-backup-professional/
├── backup_app.py          # Main application executable
├── requirements.txt       # Python dependencies
├── README.md              # Documentation
├── Demo.png               # UI Preview Screenshot
├── templates/
│   └── index.html        # Web UI template
├── static/
│   ├── css/
│   │   └── style.css     # UI Stylesheet
│   └── js/
│       └── app.js        # Frontend WebSocket & UI logic
├── backup_states/        # Session state files for resume support (auto-created)
└── backup/               # Default local backup folder

```

---

## ⚙️ Configuration

### Default Settings

* **Source Folder:** `/sdcard/DCIM/`
* **Destination:** `backup` (relative local directory)
* **Chunk Size:** `1 MB`
* **Auto-refresh:** 30 seconds for connection state, 3 seconds for active status.

### Custom Modification

You can directly edit `backup_app.py` to change:

* `chunk_size` – Optimizes data packet streaming throughput.
* `ping_timeout` – Adjusts WebSocket connection stability tolerances.
* `port` – Server port binding (Default: `5000`).

---

## 🛠️ Troubleshooting

### ❌ "No Android device connected"

**Solution:** Verify physical connection and ADB state:

```bash
# Check if device is properly recognized
adb devices

# If it returns an empty list, restart the ADB daemon
adb kill-server
adb start-server

```

### ❌ "Folder is empty" or size detection fails

**Solution:**

* Ensure the target directory actually exists via shell: `adb shell ls /sdcard/`
* Try standard pathways like `/sdcard/Download/` to isolate permission locks.

### ❌ "ADB not available"

**Solution:** Ensure ADB is declared in system variables. Test availability globally using:

```bash
adb version

```

### ❌ Port 5000 already in use

**Solution:** Modify the port mapping inside `backup_app.py`:

```python
# Change port argument from 5000 to 8080
socketio.run(app, host='0.0.0.0', port=8080)

```

---

## 🔧 Advanced Details

### File Type Detection Guide

| Extension | Icon | Description |
| --- | --- | --- |
| `.jpg`, `.png`, `.gif` | 🖼️ | Images |
| `.mp4`, `.avi`, `.mkv` | 🎬 | Videos |
| `.mp3`, `.wav`, `.flac` | 🎵 | Audio Tracks |
| `.zip`, `.rar`, `.7z` | 📦 | Compressed Archives |
| `.pdf` | 📕 | PDF Documents |
| `.doc`, `.docx` | 📘 | Word Documents |
| `.xls`, `.xlsx` | 📊 | Spreadsheets |
| `.apk` | 📱 | Android Application Packages |

### 📊 Performance Benchmarks

| Scenario | File Count | Total Size | Average Speed | Memory Footprint |
| --- | --- | --- | --- | --- |
| **Photos Only** | ~1,000 | 2 GB | 25–35 MB/s | ~100 MB |
| **Videos Only** | ~100 | 50 GB | 30–40 MB/s | ~150 MB |
| **Mixed Media** | ~50,000 | 100 GB | 20–30 MB/s | ~200 MB |

> *Note: Actual speeds depend heavily on your physical USB cable rating (USB 2.0 vs 3.0/C) and storage drive read/write caps.*

---

## ⚠️ Limitations & Disclaimer

* **Platform Lock:** Built specifically to leverage native Windows APIs (`tar.exe`); Linux and macOS environments are currently unsupported.
* **Data Responsibility:** This tool acts as a transfer bridge. Always verify the byte size of completed backups before wiping your source device. The developers hold no liability for data loss.

---

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.

---

Made with ❤️ for the Android community

[Report Bug](https://www.google.com/search?q=https://github.com/DeJavi08/ADB-FileManager/issues) • [Request Feature](https://www.google.com/search?q=https://github.com/DeJavi08/ADB-FileManager/issues) • [Star on GitHub](https://www.google.com/search?q=https://github.com/DeJavi08/ADB-FileManager)
