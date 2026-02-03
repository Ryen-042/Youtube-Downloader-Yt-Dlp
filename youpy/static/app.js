/**
 * YouPy Web GUI - Frontend JavaScript
 */

// State
let currentVideoData = null;
let currentPlaylistData = null;
let selectedStreams = [];
let eventSource = null;
let completedVideoIds = new Set(); // Track completed downloads to prevent duplicates

// DOM Elements
const elements = {
    // Single Video
    singleUrl: document.getElementById('singleUrl'),
    fetchStreamsBtn: document.getElementById('fetchStreamsBtn'),
    videoInfo: document.getElementById('videoInfo'),
    videoThumbnail: document.getElementById('videoThumbnail'),
    videoTitle: document.getElementById('videoTitle'),
    videoDuration: document.getElementById('videoDuration'),
    videoUploadDate: document.getElementById('videoUploadDate'),
    alreadyDownloaded: document.getElementById('alreadyDownloaded'),
    streamSelection: document.getElementById('streamSelection'),
    streamsTableBody: document.getElementById('streamsTableBody'),
    singleAudioOnly: document.getElementById('singleAudioOnly'),
    singleWriteDesc: document.getElementById('singleWriteDesc'),
    downloadSingleBtn: document.getElementById('downloadSingleBtn'),
    
    // Playlist
    playlistUrl: document.getElementById('playlistUrl'),
    fetchPlaylistBtn: document.getElementById('fetchPlaylistBtn'),
    playlistInfo: document.getElementById('playlistInfo'),
    playlistTitle: document.getElementById('playlistTitle'),
    playlistCount: document.getElementById('playlistCount'),
    playlistStart: document.getElementById('playlistStart'),
    playlistEnd: document.getElementById('playlistEnd'),
    selectAllPlaylist: document.getElementById('selectAllPlaylist'),
    selectRangePlaylist: document.getElementById('selectRangePlaylist'),
    selectAllCheckbox: document.getElementById('selectAllCheckbox'),
    playlistTableBody: document.getElementById('playlistTableBody'),
    playlistAudioOnly: document.getElementById('playlistAudioOnly'),
    playlistWriteDesc: document.getElementById('playlistWriteDesc'),
    downloadPlaylistBtn: document.getElementById('downloadPlaylistBtn'),
    
    // Batch
    batchLinks: document.getElementById('batchLinks'),
    loadLinksBtn: document.getElementById('loadLinksBtn'),
    saveLinksBtn: document.getElementById('saveLinksBtn'),
    batchAudioOnly: document.getElementById('batchAudioOnly'),
    batchWriteDesc: document.getElementById('batchWriteDesc'),
    downloadBatchBtn: document.getElementById('downloadBatchBtn'),
    
    // Progress
    progressPanel: document.getElementById('progressPanel'),
    noDownloadsMsg: document.getElementById('noDownloadsMsg'),
    activeDownloadsCount: document.getElementById('activeDownloadsCount'),
    completedList: document.getElementById('completedList'),
    
    // Modals & Toast
    loadingModal: new bootstrap.Modal(document.getElementById('loadingModal')),
    loadingMessage: document.getElementById('loadingMessage'),
    toast: new bootstrap.Toast(document.getElementById('toastNotification')),
    toastTitle: document.getElementById('toastTitle'),
    toastBody: document.getElementById('toastBody'),
    toastIcon: document.getElementById('toastIcon'),
};

// Utility Functions
function showLoading(message = 'Loading...') {
    elements.loadingMessage.textContent = message;
    elements.loadingModal.show();
}

function hideLoading() {
    elements.loadingModal.hide();
}

function showToast(title, message, type = 'info') {
    elements.toastTitle.textContent = title;
    elements.toastBody.textContent = message;
    
    const iconClasses = {
        'info': 'bi-info-circle text-primary',
        'success': 'bi-check-circle text-success',
        'error': 'bi-exclamation-triangle text-danger',
        'warning': 'bi-exclamation-circle text-warning'
    };
    
    elements.toastIcon.className = `bi ${iconClasses[type] || iconClasses.info} me-2`;
    elements.toast.show();
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatSpeed(bytesPerSec) {
    return formatBytes(bytesPerSec) + '/s';
}

function formatEta(seconds) {
    if (!seconds || seconds < 0) return '---';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    // Format YYYYMMDD to readable date
    if (dateStr.length === 8) {
        const year = dateStr.substring(0, 4);
        const month = dateStr.substring(4, 6);
        const day = dateStr.substring(6, 8);
        return `${day}/${month}/${year}`;
    }
    return dateStr;
}

// API Functions
async function fetchStreams(url) {
    const response = await fetch('/api/fetch-streams', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    });
    return response.json();
}

async function fetchPlaylist(url) {
    const response = await fetch('/api/fetch-playlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    });
    return response.json();
}

async function startDownload(url, formatIds, audioOnly, writeDesc) {
    const response = await fetch('/api/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, format_ids: formatIds, audio_only: audioOnly, write_desc: writeDesc })
    });
    return response.json();
}

async function startPlaylistDownload(playlistUrl, entries, audioOnly, writeDesc) {
    const response = await fetch('/api/download-playlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ playlist_url: playlistUrl, entries, audio_only: audioOnly, write_desc: writeDesc })
    });
    return response.json();
}

async function getBatchLinks() {
    const response = await fetch('/api/batch-links');
    return response.json();
}

async function saveBatchLinks(content) {
    const response = await fetch('/api/batch-links', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
    });
    return response.json();
}

async function startBatchDownload(links, audioOnly, writeDesc) {
    const response = await fetch('/api/download-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ links, audio_only: audioOnly, write_desc: writeDesc })
    });
    return response.json();
}

// Single Video Functions
function displayVideoInfo(data) {
    currentVideoData = data;
    
    elements.videoThumbnail.src = data.thumbnail || '';
    elements.videoTitle.textContent = data.title;
    elements.videoDuration.textContent = data.duration;
    elements.videoUploadDate.textContent = formatDate(data.upload_date);
    
    if (data.already_downloaded) {
        elements.alreadyDownloaded.classList.remove('d-none');
    } else {
        elements.alreadyDownloaded.classList.add('d-none');
    }
    
    elements.videoInfo.classList.remove('d-none');
}

function displayStreams(streams) {
    elements.streamsTableBody.innerHTML = '';
    selectedStreams = [];
    
    let categoryIndex = 0;
    for (const [category, streamList] of Object.entries(streams)) {
        categoryIndex++;
        streamList.forEach((stream, streamIndex) => {
            const row = document.createElement('tr');
            row.className = 'stream-row';
            row.dataset.category = category;
            row.dataset.categoryIndex = categoryIndex;
            row.dataset.streamIndex = streamIndex + 1;
            row.dataset.formatId = stream.format_id;
            
            const isAudio = category.startsWith('audio/');
            const isVideo = category.startsWith('video/');
            const isAudioVideo = category.startsWith('audio-video/');
            
            // Add category-based row color class
            if (isAudio) row.classList.add('stream-audio');
            else if (isVideo) row.classList.add('stream-video');
            else if (isAudioVideo) row.classList.add('stream-audiovideo');
            
            let codecInfo = '';
            if (stream.vcodec) codecInfo += stream.vcodec.split('.')[0];
            if (stream.vcodec && stream.acodec) codecInfo += ' / ';
            if (stream.acodec) codecInfo += stream.acodec.split('.')[0];
            
            // Format TBR (total bitrate)
            const tbr = stream.tbr ? `${Math.round(stream.tbr)} kbps` : '-';
            
            row.innerHTML = `
                <td><input type="checkbox" class="form-check-input stream-checkbox" data-format-id="${stream.format_id}" data-type="${isAudio ? 'audio' : (isVideo ? 'video' : 'audio-video')}"></td>
                <td><span class="badge ${isAudio ? 'bg-info' : (isVideo ? 'bg-warning' : 'bg-success')}">${category}</span></td>
                <td>${stream.format_note}</td>
                <td>${stream.filesize_formatted}</td>
                <td>${tbr}</td>
                <td><small>${codecInfo}</small></td>
            `;
            
            row.addEventListener('click', (e) => {
                if (e.target.type !== 'checkbox') {
                    const checkbox = row.querySelector('.stream-checkbox');
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change'));
                }
            });
            
            elements.streamsTableBody.appendChild(row);
        });
    }
    
    // Add event listeners to checkboxes
    document.querySelectorAll('.stream-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', handleStreamSelection);
    });
    
    elements.streamSelection.classList.remove('d-none');
    elements.downloadSingleBtn.disabled = true;
}

function handleStreamSelection(e) {
    const checkbox = e.target;
    const formatId = checkbox.dataset.formatId;
    const type = checkbox.dataset.type;
    const row = checkbox.closest('tr');
    
    if (checkbox.checked) {
        // If audio-video is selected, deselect all others
        if (type === 'audio-video') {
            document.querySelectorAll('.stream-checkbox:checked').forEach(cb => {
                if (cb !== checkbox) {
                    cb.checked = false;
                    cb.closest('tr').classList.remove('selected');
                }
            });
            selectedStreams = [formatId];
        } else {
            // Remove any audio-video selections
            document.querySelectorAll('.stream-checkbox[data-type="audio-video"]:checked').forEach(cb => {
                cb.checked = false;
                cb.closest('tr').classList.remove('selected');
            });
            
            // If same type is already selected, replace it
            const existingIndex = selectedStreams.findIndex(id => {
                const cb = document.querySelector(`.stream-checkbox[data-format-id="${id}"]`);
                return cb && cb.dataset.type === type;
            });
            
            if (existingIndex !== -1) {
                const oldId = selectedStreams[existingIndex];
                document.querySelector(`.stream-checkbox[data-format-id="${oldId}"]`).checked = false;
                document.querySelector(`.stream-checkbox[data-format-id="${oldId}"]`).closest('tr').classList.remove('selected');
                selectedStreams.splice(existingIndex, 1);
            }
            
            // Limit to 2 selections (1 video + 1 audio)
            if (selectedStreams.length >= 2) {
                showToast('Selection Limit', 'You can only select up to 2 streams (1 video + 1 audio)', 'warning');
                checkbox.checked = false;
                return;
            }
            
            selectedStreams.push(formatId);
        }
        row.classList.add('selected');
    } else {
        selectedStreams = selectedStreams.filter(id => id !== formatId);
        row.classList.remove('selected');
    }
    
    elements.downloadSingleBtn.disabled = selectedStreams.length === 0;
}

// Playlist Functions
function displayPlaylistInfo(data) {
    currentPlaylistData = data;
    
    elements.playlistTitle.textContent = data.title;
    elements.playlistCount.textContent = `${data.count} videos`;
    elements.playlistEnd.value = data.count;
    elements.playlistEnd.max = data.count;
    elements.playlistStart.max = data.count;
    
    elements.playlistTableBody.innerHTML = '';
    
    data.entries.forEach((entry, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><input type="checkbox" class="form-check-input playlist-checkbox" data-index="${index}" data-id="${entry.id}" data-url="${entry.url}"></td>
            <td>${index + 1}</td>
            <td class="text-truncate" style="max-width: 300px;" title="${entry.title}">${entry.title}</td>
            <td>${entry.duration_formatted}</td>
            <td>${entry.downloaded ? '<span class="badge bg-success">Downloaded</span>' : '<span class="badge bg-secondary">Not Downloaded</span>'}</td>
        `;
        elements.playlistTableBody.appendChild(row);
    });
    
    // Update checkbox listeners
    document.querySelectorAll('.playlist-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updatePlaylistDownloadButton);
    });
    
    elements.playlistInfo.classList.remove('d-none');
    elements.downloadPlaylistBtn.disabled = true;
}

function updatePlaylistDownloadButton() {
    const checkedCount = document.querySelectorAll('.playlist-checkbox:checked').length;
    elements.downloadPlaylistBtn.disabled = checkedCount === 0;
    elements.downloadPlaylistBtn.innerHTML = `<i class="bi bi-download"></i> Download Selected (${checkedCount})`;
}

function getSelectedPlaylistEntries() {
    const entries = [];
    document.querySelectorAll('.playlist-checkbox:checked').forEach(checkbox => {
        entries.push({
            id: checkbox.dataset.id,
            url: checkbox.dataset.url,
            index: parseInt(checkbox.dataset.index) + 1
        });
    });
    return entries;
}

// Progress/SSE Functions
function initProgressStream() {
    if (eventSource) {
        eventSource.close();
    }
    
    eventSource = new EventSource('/api/progress');
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.keepalive) return;
        
        if (data.status === 'playlist_completed' || data.status === 'batch_completed') {
            showToast('Download Complete', data.message, 'success');
            return;
        }
        
        updateProgress(data);
    };
    
    eventSource.onerror = () => {
        console.log('SSE connection error, reconnecting...');
        setTimeout(initProgressStream, 3000);
    };
}

function updateProgress(data) {
    const videoId = data.video_id;
    let progressItem = document.getElementById(`progress-${videoId}`);
    
    elements.noDownloadsMsg.classList.add('d-none');
    
    // Handle both "finished" (from yt-dlp hook) and "completed" (from post-processing)
    if (data.status === 'completed' || data.status === 'finished') {
        // Prevent duplicate entries (both finished and completed events fire)
        if (completedVideoIds.has(videoId)) {
            return;
        }
        completedVideoIds.add(videoId);
        
        if (progressItem) {
            progressItem.remove();
        }
        addToCompleted(data.title || videoId);
        updateActiveCount();
        return;
    }
    
    if (data.status === 'error') {
        if (progressItem) {
            progressItem.classList.add('error');
            progressItem.querySelector('.stats').innerHTML = `<span class="text-danger">Error: ${data.error || 'Unknown error'}</span>`;
        }
        showToast('Download Error', data.error || 'An error occurred', 'error');
        updateActiveCount();
        return;
    }
    
    if (!progressItem) {
        progressItem = document.createElement('div');
        progressItem.id = `progress-${videoId}`;
        progressItem.className = 'progress-item downloading';
        progressItem.innerHTML = `
            <div class="title">${data.title || videoId}</div>
            <div class="progress">
                <div class="progress-bar" role="progressbar" style="width: 0%"></div>
            </div>
            <div class="stats">
                <span class="percent">0%</span>
                <span class="speed">-- /s</span>
                <span class="eta">ETA: ---</span>
            </div>
        `;
        elements.progressPanel.insertBefore(progressItem, elements.noDownloadsMsg);
    }
    
    // Update progress
    const percent = data.percent || 0;
    progressItem.querySelector('.progress-bar').style.width = `${percent}%`;
    progressItem.querySelector('.percent').textContent = `${percent.toFixed(1)}%`;
    progressItem.querySelector('.speed').textContent = data.speed ? formatSpeed(data.speed) : '-- /s';
    progressItem.querySelector('.eta').textContent = `ETA: ${formatEta(data.eta)}`;
    
    if (data.title) {
        progressItem.querySelector('.title').textContent = data.title;
    }
    
    updateActiveCount();
}

function updateActiveCount() {
    const count = document.querySelectorAll('.progress-item:not(.completed):not(.error)').length;
    elements.activeDownloadsCount.textContent = count;
    
    if (count === 0) {
        elements.noDownloadsMsg.classList.remove('d-none');
    }
}

function addToCompleted(title) {
    const firstChild = elements.completedList.firstChild;
    if (firstChild && firstChild.classList && !firstChild.classList.contains('completed-item')) {
        elements.completedList.innerHTML = '';
    }
    
    const item = document.createElement('div');
    item.className = 'completed-item';
    item.innerHTML = `<i class="bi bi-check-circle"></i> ${title}`;
    elements.completedList.insertBefore(item, elements.completedList.firstChild);
}

// Event Listeners
elements.fetchStreamsBtn.addEventListener('click', async () => {
    const url = elements.singleUrl.value.trim();
    if (!url) {
        showToast('Error', 'Please enter a YouTube URL', 'error');
        return;
    }
    
    showLoading('Fetching video streams...');
    try {
        const data = await fetchStreams(url);
        hideLoading();
        
        if (data.error) {
            showToast('Error', data.error, 'error');
            return;
        }
        
        displayVideoInfo(data);
        displayStreams(data.streams);
    } catch (error) {
        hideLoading();
        showToast('Error', 'Failed to fetch streams', 'error');
    }
});

elements.singleAudioOnly.addEventListener('change', (e) => {
    if (e.target.checked) {
        elements.streamSelection.classList.add('d-none');
        elements.downloadSingleBtn.disabled = !elements.singleUrl.value.trim();
    } else {
        if (currentVideoData) {
            elements.streamSelection.classList.remove('d-none');
            elements.downloadSingleBtn.disabled = selectedStreams.length === 0;
        }
    }
});

elements.downloadSingleBtn.addEventListener('click', async () => {
    const url = elements.singleUrl.value.trim();
    const audioOnly = elements.singleAudioOnly.checked;
    const writeDesc = elements.singleWriteDesc.checked;
    
    let formatIds = selectedStreams.join('+');
    if (audioOnly) {
        formatIds = 'bestaudio';
    }
    
    if (!url) {
        showToast('Error', 'Please enter a YouTube URL', 'error');
        return;
    }
    
    try {
        const result = await startDownload(url, formatIds, audioOnly, writeDesc);
        if (result.error) {
            showToast('Error', result.error, 'error');
        } else {
            showToast('Download Started', 'The video download has been started', 'success');
        }
    } catch (error) {
        showToast('Error', 'Failed to start download', 'error');
    }
});

elements.fetchPlaylistBtn.addEventListener('click', async () => {
    const url = elements.playlistUrl.value.trim();
    if (!url) {
        showToast('Error', 'Please enter a playlist URL', 'error');
        return;
    }
    
    showLoading('Fetching playlist info...');
    try {
        const data = await fetchPlaylist(url);
        hideLoading();
        
        if (data.error) {
            showToast('Error', data.error, 'error');
            return;
        }
        
        displayPlaylistInfo(data);
    } catch (error) {
        hideLoading();
        showToast('Error', 'Failed to fetch playlist', 'error');
    }
});

elements.selectAllCheckbox.addEventListener('change', (e) => {
    document.querySelectorAll('.playlist-checkbox').forEach(cb => {
        cb.checked = e.target.checked;
    });
    updatePlaylistDownloadButton();
});

elements.selectAllPlaylist.addEventListener('click', () => {
    document.querySelectorAll('.playlist-checkbox').forEach(cb => {
        cb.checked = true;
    });
    elements.selectAllCheckbox.checked = true;
    updatePlaylistDownloadButton();
});

elements.selectRangePlaylist.addEventListener('click', () => {
    const start = parseInt(elements.playlistStart.value) || 1;
    const end = parseInt(elements.playlistEnd.value) || currentPlaylistData.count;
    
    document.querySelectorAll('.playlist-checkbox').forEach((cb, index) => {
        cb.checked = (index + 1 >= start && index + 1 <= end);
    });
    updatePlaylistDownloadButton();
});

elements.downloadPlaylistBtn.addEventListener('click', async () => {
    const url = elements.playlistUrl.value.trim();
    const entries = getSelectedPlaylistEntries();
    const audioOnly = elements.playlistAudioOnly.checked;
    const writeDesc = elements.playlistWriteDesc.checked;
    
    if (entries.length === 0) {
        showToast('Error', 'Please select at least one video', 'error');
        return;
    }
    
    try {
        const result = await startPlaylistDownload(url, entries, audioOnly, writeDesc);
        if (result.error) {
            showToast('Error', result.error, 'error');
        } else {
            showToast('Downloads Started', `Started downloading ${result.count} videos`, 'success');
        }
    } catch (error) {
        showToast('Error', 'Failed to start playlist download', 'error');
    }
});

elements.loadLinksBtn.addEventListener('click', async () => {
    try {
        const data = await getBatchLinks();
        elements.batchLinks.value = data.raw || '';
        showToast('Loaded', 'Links loaded from video-links.txt', 'info');
    } catch (error) {
        showToast('Error', 'Failed to load links', 'error');
    }
});

elements.saveLinksBtn.addEventListener('click', async () => {
    try {
        await saveBatchLinks(elements.batchLinks.value);
        showToast('Saved', 'Links saved to video-links.txt', 'success');
    } catch (error) {
        showToast('Error', 'Failed to save links', 'error');
    }
});

elements.downloadBatchBtn.addEventListener('click', async () => {
    const links = elements.batchLinks.value
        .split('\n')
        .map(l => l.trim())
        .filter(l => l);
    
    const audioOnly = elements.batchAudioOnly.checked;
    const writeDesc = elements.batchWriteDesc.checked;
    
    if (links.length === 0) {
        showToast('Error', 'Please enter at least one video URL', 'error');
        return;
    }
    
    try {
        const result = await startBatchDownload(links, audioOnly, writeDesc);
        if (result.error) {
            showToast('Error', result.error, 'error');
        } else {
            showToast('Downloads Started', `Started downloading ${result.count} videos`, 'success');
        }
    } catch (error) {
        showToast('Error', 'Failed to start batch download', 'error');
    }
});

// Allow Enter key to trigger fetch
elements.singleUrl.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        elements.fetchStreamsBtn.click();
    }
});

elements.playlistUrl.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        elements.fetchPlaylistBtn.click();
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initProgressStream();
});
