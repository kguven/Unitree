document.addEventListener('DOMContentLoaded', () => {
    console.log('Habibot Control App Loaded');

    const statusConn = document.getElementById('status-conn');
    const statusBatt = document.getElementById('status-batt');
    const btnToggle = document.getElementById('btn-10');
    const btnPhoto = document.getElementById('btn-11');
    const btnSettings = document.getElementById('btn-12');

    // Modal Elements
    const modal = document.getElementById("settings-modal");
    const span = document.getElementsByClassName("close")[0];
    const saveSettingsBtn = document.getElementById("save-settings");
    const photoUrlInput = document.getElementById("photo-url");
    const photoIntervalInput = document.getElementById("photo-interval");

    // Button click handler
    document.querySelectorAll('.cmd-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const btnId = btn.id;
            const btnName = btn.querySelector('span').innerText;

            console.log(`Command: ${btnName} (${btnId})`);

            // Check if it's the toggle button
            if (btnId === 'btn-10') {
                toggleChat(btn);
                return;
            }
            if (btnId === 'btn-11') {
                togglePhoto(btn);
                return;
            }
            if (btnId === 'btn-12') {
                openSettings();
                return;
            }
            if (btnId === 'btn-13') {
                toggleLiveCamera(btn);
                return;
            }

            // Visual feedback
            btn.classList.add('processing');

            try {
                const response = await fetch('/api/trigger_action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ button_id: btnId })
                });

                const result = await response.json();
                console.log('Result:', result);

                if (result.success) {
                    // Success animation or feedback
                } else {
                    alert('Command failed: ' + result.error);
                }
            } catch (err) {
                console.error('Error:', err);
                statusConn.classList.add('disconnected');
                statusConn.innerText = 'Disconnected';
            } finally {
                btn.classList.remove('processing');
            }
        });
    });

    // Specific logic for Toggle Chat (Button 10)
    async function toggleChat(btn) {
        const isCurrentlyActive = btn.classList.contains('active');
        const newState = !isCurrentlyActive;

        // Optimistic UI update
        updateToggleUI(btn, newState);

        try {
            const response = await fetch('/api/toggle_chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ active: newState })
            });
            const result = await response.json();

            if (!result.success) {
                // Revert if failed
                updateToggleUI(btn, isCurrentlyActive);
                alert('Failed to toggle chat');
            }
        } catch (err) {
            console.error('Network Error:', err);
            updateToggleUI(btn, isCurrentlyActive);
        }
    }



    // Live Camera Logic
    function toggleLiveCamera(btn) {
        const isCurrentlyActive = btn.classList.contains('active');
        const newState = !isCurrentlyActive;
        const liveContainer = document.getElementById('live-camera-container');
        const liveVideo = document.getElementById('live-video');

        if (newState) {
            btn.classList.add('active');
            btn.classList.remove('inactive');
            btn.querySelector('span').innerText = "Live Camera: ON";

            // Start Stream
            liveContainer.style.display = 'block';
            liveVideo.src = "/video_feed";
        } else {
            btn.classList.add('inactive');
            btn.classList.remove('active');
            btn.querySelector('span').innerText = "Live Camera: OFF";

            // Stop Stream
            liveContainer.style.display = 'none';
            liveVideo.src = "";
        }
    }

    // Specific logic for Photo Toggle (Button 11)
    async function togglePhoto(btn) {
        const isCurrentlyActive = btn.classList.contains('active');
        const newState = !isCurrentlyActive;

        updatePhotoUI(btn, newState);

        try {
            const response = await fetch('/api/photo_mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ active: newState })
            });
            const result = await response.json();
            if (!result.success) {
                updatePhotoUI(btn, isCurrentlyActive);
                alert('Failed to toggle photo mode');
            }
        } catch (err) {
            console.error('Network Error:', err);
            updatePhotoUI(btn, isCurrentlyActive);
        }
    }

    function updatePhotoUI(btn, active) {
        if (active) {
            btn.classList.add('active');
            btn.classList.remove('inactive');
            btn.querySelector('span').innerText = "Photo Upload: ON";
            btn.querySelector('i').className = "fas fa-camera";
            // Removed startCameraPreview() as requested
        } else {
            btn.classList.add('inactive');
            btn.classList.remove('active');
            btn.querySelector('span').innerText = "Photo Upload: OFF";
            btn.querySelector('i').className = "fas fa-camera-retro";
            // Removed stopCameraPreview()
        }
    }

    // Settings Modal Logic
    async function openSettings() {
        const settingsModal = document.getElementById("settings-modal");
        settingsModal.style.display = "flex";
        // Fetch current settings
        try {
            const res = await fetch('/api/photo_settings');
            const data = await res.json();
            photoUrlInput.value = data.url;
            photoIntervalInput.value = data.interval;
        } catch (e) { console.error(e); }
    }

    // Generic Modal Close Logic
    const settingsModal = document.getElementById("settings-modal");
    const cameraModal = document.getElementById("camera-modal");

    // Close Buttons
    document.getElementById("close-settings").onclick = () => {
        settingsModal.style.display = "none";
    }
    document.getElementById("close-camera").onclick = () => {
        cameraModal.style.display = "none";
        // Also turn off the toggle button state
        const btn = document.getElementById('btn-13');
        toggleLiveCamera(btn, false); // force off
    }

    // Windows click outside to close
    window.onclick = function (event) {
        if (event.target == settingsModal) {
            settingsModal.style.display = "none";
        }
        if (event.target == cameraModal) {
            cameraModal.style.display = "none";
            const btn = document.getElementById('btn-13');
            toggleLiveCamera(btn, false);
        }
    }

    saveSettingsBtn.onclick = async function () {
        const url = photoUrlInput.value;
        const interval = photoIntervalInput.value;

        try {
            await fetch('/api/photo_settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url, interval: interval })
            });
            settingsModal.style.display = "none";
            alert("Settings saved!");
        } catch (e) {
            alert("Failed to save settings");
        }
    }


    function updateToggleUI(btn, active) {
        if (active) {
            btn.classList.add('active');
            btn.classList.remove('inactive');
            btn.querySelector('span').innerText = "Gemini Chat: ON";
            btn.querySelector('i').className = "fas fa-microphone";
        } else {
            btn.classList.add('inactive');
            btn.classList.remove('active');
            btn.querySelector('span').innerText = "Gemini Chat: OFF";
            btn.querySelector('i').className = "fas fa-microphone-slash";
        }
    }

    // Periodic Heartbeat / Status Check
    setInterval(async () => {
        try {
            // This endpoint would return battery level and connection status
            // For now, we assume if fetch works, we are connected.
            const response = await fetch('/api/status');
            const data = await response.json();

            statusConn.classList.remove('disconnected');
            statusConn.innerText = "Connected";

            if (data.battery !== undefined) {
                statusBatt.innerText = `${data.battery}%`;
            }

            // Sync toggle button state if needed (in case changed from elsewhere)
            if (data.chat_active !== undefined) {
                const isActive = btnToggle.classList.contains('active');
                if (isActive !== data.chat_active) {
                    updateToggleUI(btnToggle, data.chat_active);
                }
            }
            if (data.photo_active !== undefined) {
                const isActive = btnPhoto.classList.contains('active');
                if (isActive !== data.photo_active) {
                    updatePhotoUI(btnPhoto, data.photo_active);
                }
            }

        } catch (err) {
            statusConn.classList.add('disconnected');
            statusConn.innerText = "Disconnected";
        }
    }, 5000);
});
