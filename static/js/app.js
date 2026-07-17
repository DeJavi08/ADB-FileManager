const socket = io({
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000
});

let currentPath = '/sdcard/';
let isConnected = false;
let isRunning = false;
let isFolderLoading = false;
let showFiles = true;
let statusCheckInterval = null;
let connectionCheckInterval = null;

// ====================================================================
// Socket Events
// ====================================================================

socket.on('connect', () => {
    addLog('info', 'Connected to server');
    checkConnection();
});

socket.on('disconnect', () => {
    addLog('warning', 'Disconnected from server (reconnecting...)');
    updateConnectionStatus(false);
});

socket.on('reconnect', () => {
    addLog('info', 'Reconnected to server');
    checkConnection();
});

socket.on('progress_update', (data) => {
    updateProgress(data);
});

// ====================================================================
// Connection & Device
// ====================================================================

async function checkConnection() {
    try {
        const response = await fetch('/api/devices', { signal: AbortSignal.timeout(5000) });
        const data = await response.json();

        if (data.devices && data.devices.length > 0) {
            isConnected = true;
            updateConnectionStatus(true, data.devices[0].serial);
            document.getElementById('device-model').textContent = data.info?.model || 'Unknown';
            document.getElementById('device-android').textContent = data.info?.android_version || '-';
            document.getElementById('device-storage').textContent = data.info?.storage_total || '-';

            if (!isRunning && !isFolderLoading) {
                loadFolder(currentPath);
            }
        } else {
            isConnected = false;
            updateConnectionStatus(false);
            document.getElementById('device-model').textContent = 'No device';
            document.getElementById('device-android').textContent = '-';
            document.getElementById('device-storage').textContent = '-';

            if (!isRunning) {
                document.getElementById('folder-content').innerHTML = `
                    <div class="empty-folder">
                        <div class="icon">📱</div>
                        <p>No device connected</p>
                    </div>
                `;
            }
        }
    } catch (error) {
        if (!isRunning) {
            addLog('warning', 'Connection check failed: ' + error.message);
        }
    }
}

function updateConnectionStatus(connected, serial = '') {
    const dot = document.getElementById('status-dot');
    const label = document.getElementById('status-label');
    const name = document.getElementById('device-name');

    if (connected) {
        dot.className = 'status-dot connected';
        label.textContent = 'Connected';
        name.textContent = serial ? '(' + serial + ')' : '';
    } else {
        dot.className = 'status-dot disconnected';
        label.textContent = 'Disconnected';
        name.textContent = '';
    }
}

// ====================================================================
// File Manager - Toggle Files
// ====================================================================

function toggleFiles() {
    showFiles = !showFiles;
    document.getElementById('toggle-files-btn').textContent = showFiles ? '📄 Hide Files' : '📄 Show Files';
    loadFolder(currentPath);
}

async function loadFolder(path) {
    if (isRunning) {
        document.getElementById('folder-content').innerHTML = `
            <div class="empty-folder">
                <div class="icon">⏳</div>
                <p>Backup in progress... Folder browsing paused</p>
            </div>
        `;
        return;
    }

    if (isFolderLoading) return;
    isFolderLoading = true;

    if (!isConnected) {
        document.getElementById('folder-content').innerHTML = `
            <div class="empty-folder">
                <div class="icon">📱</div>
                <p>Device not connected</p>
            </div>
        `;
        isFolderLoading = false;
        return;
    }

    try {
        const response = await fetch('/api/folder?path=' + encodeURIComponent(path), {
            signal: AbortSignal.timeout(10000)
        });
        const data = await response.json();

        if (data.error) {
            document.getElementById('folder-content').innerHTML = `
                <div class="empty-folder">
                    <div class="icon">⚠️</div>
                    <p>Error: ${data.error}</p>
                    <p style="font-size:12px;color:#666;margin-top:10px;">Try: /sdcard/</p>
                </div>
            `;
            isFolderLoading = false;
            return;
        }

        currentPath = data.current_path || path;
        renderBreadcrumb(data);
        renderFolderItems(data);
        document.getElementById('selected-path').value = currentPath;

    } catch (error) {
        if (!isRunning) {
            document.getElementById('folder-content').innerHTML = `
                <div class="empty-folder">
                    <div class="icon">⚠️</div>
                    <p>Failed to load folder: ${error.message}</p>
                </div>
            `;
        }
    }

    isFolderLoading = false;
}

function renderBreadcrumb(data) {
    const breadcrumb = document.getElementById('breadcrumb');
    let path = data.current_path || currentPath;
    let parts = path.split('/').filter(p => p);
    let html = '<span class="crumb root" onclick="loadFolder(\'/\')"> /</span>';
    let current = '';

    for (const part of parts) {
        current += '/' + part;
        html += '<span class="sep">/</span>';
        html += '<span class="crumb" onclick="loadFolder(\'' + current + '\')">' + part + '</span>';
    }

    breadcrumb.innerHTML = html;
}

function renderFolderItems(data) {
    const container = document.getElementById('folder-content');

    if (!data.items || data.items.length === 0) {
        container.innerHTML = `
            <div class="empty-folder">
                <div class="icon">📂</div>
                <p>This folder is empty</p>
            </div>
        `;
        return;
    }

    let html = '';

    // Parent folder
    if (data.parent && data.parent !== data.current_path) {
        html += `
            <div class="folder-item" onclick="loadFolder('${data.parent}')">
                <span class="icon">📁</span>
                <span class="name dir">..</span>
                <span class="size"></span>
                <span class="type">Parent</span>
            </div>
        `;
    }

    const folders = data.items.filter(item => item.is_dir);
    const files = data.items.filter(item => !item.is_dir);

    // Render folders
    for (const item of folders) {
        html += `
            <div class="folder-item" onclick="loadFolder('${item.path}')">
                <span class="icon">📁</span>
                <span class="name dir">${item.name}</span>
                <span class="size"></span>
                <span class="type">Folder</span>
                <button class="select-btn" onclick="event.stopPropagation(); selectFolder('${item.path}')">Select</button>
            </div>
        `;
    }

    // Render files (if showFiles is true)
    if (showFiles && files.length > 0) {
        if (folders.length > 0) {
            html += `
                <div style="padding:8px 12px;color:#666;font-size:11px;border-top:1px solid #1a1a2e;margin-top:5px;">
                    ─── Files (${files.length}) ───
                </div>
            `;
        }

        for (const item of files) {
            let icon = '📄';
            const ext = item.name.split('.').pop().toLowerCase();
            if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext)) icon = '🖼️';
            else if (['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv'].includes(ext)) icon = '🎬';
            else if (['mp3', 'wav', 'flac', 'aac', 'ogg'].includes(ext)) icon = '🎵';
            else if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) icon = '📦';
            else if (['pdf'].includes(ext)) icon = '📕';
            else if (['doc', 'docx'].includes(ext)) icon = '📘';
            else if (['xls', 'xlsx'].includes(ext)) icon = '📊';
            else if (['ppt', 'pptx'].includes(ext)) icon = '📙';
            else if (['apk'].includes(ext)) icon = '📱';

            const sizeDisplay = item.size > 0 ? item.size_formatted : '0 B';

            html += `
                <div class="folder-item" style="cursor:default;">
                    <span class="icon">${icon}</span>
                    <span class="name" style="color:#a0aec0;">${item.name}</span>
                    <span class="size">${sizeDisplay}</span>
                    <span class="type">File</span>
                    <button class="select-btn" onclick="event.stopPropagation(); selectFile('${item.path}')">Select</button>
                </div>
            `;
        }
    }

    container.innerHTML = html;
}

function selectFolder(path) {
    document.getElementById('source').value = path;
    document.getElementById('selected-path').value = path;
    addLog('info', 'Selected folder: ' + path);
}

function selectFile(path) {
    document.getElementById('source').value = path;
    document.getElementById('selected-path').value = path;
    addLog('info', 'Selected file: ' + path);
}

function selectCurrentPath() {
    const path = document.getElementById('selected-path').value;
    document.getElementById('source').value = path;
    addLog('info', 'Selected: ' + path);
}

function refreshFolder() {
    if (!isRunning) {
        loadFolder(currentPath);
    }
}

function goHome() {
    if (!isRunning) {
        loadFolder('/sdcard/');
    }
}

function goToDCIM() {
    if (!isRunning) {
        loadFolder('/sdcard/DCIM/');
    }
}

// ====================================================================
// Output Folder Browser
// ====================================================================

async function browseOutput() {
    try {
        const response = await fetch('/api/browse_folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();

        if (data.folder) {
            document.getElementById('destination').value = data.folder;
            addLog('info', '📁 Output folder set to: ' + data.folder);
        } else if (data.error) {
            addLog('error', 'Failed to browse: ' + data.error);
        }
    } catch (error) {
        addLog('error', 'Error browsing folder: ' + error.message);
    }
}

function openOutputFolder() {
    const path = document.getElementById('destination').value.trim();
    if (!path) {
        addLog('warning', 'No destination folder set');
        return;
    }

    try {
        fetch('/api/open_folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: path })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                addLog('error', 'Failed to open folder: ' + data.error);
            } else {
                addLog('info', '📁 Opened folder: ' + path);
            }
        })
        .catch(error => {
            addLog('error', 'Error opening folder: ' + error.message);
        });
    } catch (error) {
        addLog('error', 'Error: ' + error.message);
    }
}

// ====================================================================
// Backup Controls
// ====================================================================

async function startBackup() {
    if (isRunning) return;

    const source = document.getElementById('source').value.trim();
    const destination = document.getElementById('destination').value.trim();

    if (!source) {
        addLog('error', 'Please enter source folder');
        return;
    }
    if (!destination) {
        addLog('error', 'Please enter destination folder');
        return;
    }

    let fixedSource = source;
    if (!fixedSource.startsWith('/')) {
        fixedSource = '/' + fixedSource;
    }
    if (!fixedSource.endsWith('/') && !fixedSource.includes('.')) {
        fixedSource = fixedSource + '/';
    }
    document.getElementById('source').value = fixedSource;

    addLog('info', 'Starting backup: ' + fixedSource + ' -> ' + destination);

    try {
        const response = await fetch('/api/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: fixedSource, destination: destination })
        });
        const data = await response.json();

        if (data.error) {
            addLog('error', data.error);
        } else {
            isRunning = true;
            document.getElementById('btn-start').disabled = true;
            document.getElementById('btn-stop').disabled = false;
            addLog('success', 'Backup started!');
            document.getElementById('folder-content').innerHTML = `
                <div class="empty-folder">
                    <div class="icon">⏳</div>
                    <p>Backup in progress...</p>
                    <p style="font-size:12px;color:#666;">Folder browsing paused</p>
                </div>
            `;
        }
    } catch (error) {
        addLog('error', 'Error: ' + error.message);
    }
}

async function stopBackup() {
    if (!isRunning) return;

    addLog('warning', 'Stopping backup...');
    try {
        await fetch('/api/stop', { method: 'POST' });
        isRunning = false;
        document.getElementById('btn-start').disabled = false;
        document.getElementById('btn-stop').disabled = true;
        addLog('info', 'Backup stopped');
        setTimeout(() => loadFolder(currentPath), 1000);
    } catch (error) {
        addLog('error', 'Error: ' + error.message);
    }
}

// ====================================================================
// Progress Updates
// ====================================================================

function updateProgress(data) {
    const percent = data.percentage || 0;

    document.getElementById('progress-fill').style.width = percent + '%';
    document.getElementById('progress-fill').textContent = percent.toFixed(1) + '%';

    document.getElementById('stat-processed').textContent = data.processed_bytes_formatted || '0 B';
    document.getElementById('stat-speed').textContent = data.current_speed_display || '0 B/s';
    document.getElementById('stat-elapsed').textContent = data.elapsed || '0s';
    document.getElementById('stat-eta').textContent = data.eta || '-';

    document.getElementById('status-text').textContent = data.status ? data.status.charAt(0).toUpperCase() + data.status.slice(1) : 'Idle';
    document.getElementById('status-message').textContent = data.message || '';

    if (data.status === 'completed') {
        isRunning = false;
        document.getElementById('btn-start').disabled = false;
        document.getElementById('btn-stop').disabled = true;
        addLog('success', data.message);
        setTimeout(() => loadFolder(currentPath), 2000);
    } else if (data.status === 'failed') {
        isRunning = false;
        document.getElementById('btn-start').disabled = false;
        document.getElementById('btn-stop').disabled = true;
        addLog('error', data.message);
        setTimeout(() => loadFolder(currentPath), 2000);
    } else if (data.status === 'running') {
        const currentPercent = Math.floor(percent);
        if (currentPercent % 10 === 0 && currentPercent > 0) {
            const lastLogged = parseInt(localStorage.getItem('lastLoggedPercent') || '0');
            if (currentPercent !== lastLogged) {
                localStorage.setItem('lastLoggedPercent', currentPercent.toString());
                addLog('info', 'Progress: ' + currentPercent + '% - ' + data.processed_bytes_formatted);
            }
        }
    }
}

// ====================================================================
// Logs
// ====================================================================

function addLog(type, message) {
    const container = document.getElementById('log-container');
    const time = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = 'log-entry ' + type;
    entry.innerHTML = '<span class="time">[' + time + ']</span> ' + message;
    container.appendChild(entry);
    container.scrollTop = container.scrollHeight;

    while (container.children.length > 100) {
        container.removeChild(container.firstChild);
    }
}

// ====================================================================
// Auto Refresh
// ====================================================================

connectionCheckInterval = setInterval(checkConnection, 30000);

statusCheckInterval = setInterval(async () => {
    try {
        const response = await fetch('/api/status', { signal: AbortSignal.timeout(5000) });
        const data = await response.json();
        updateProgress(data);
    } catch (e) {}
}, 3000);

// ====================================================================
// INIT
// ====================================================================

document.addEventListener('DOMContentLoaded', function() {
    checkConnection();
    addLog('info', 'Select a folder from File Manager or enter path manually');
    addLog('info', 'Recommended: /sdcard/DCIM/ for photos');
    addLog('info', '📄 Toggle "Show Files" to see files');
});