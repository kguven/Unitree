document.addEventListener('DOMContentLoaded', () => {
    console.log('Habibot Control App Loaded');

    const statusConn = document.getElementById('status-conn');
    const statusBatt = document.getElementById('status-batt');
    const btnToggle = document.getElementById('btn-10');

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
            
            if (data.battery) {
                statusBatt.innerText = `Battery: ${data.battery}%`;
            }
            
            // Sync toggle button state if needed (in case changed from elsewhere)
            if (data.chat_active !== undefined) {
                const isActive = btnToggle.classList.contains('active');
                if (isActive !== data.chat_active) {
                    updateToggleUI(btnToggle, data.chat_active);
                }
            }
            
        } catch (err) {
            statusConn.classList.add('disconnected');
            statusConn.innerText = "Disconnected";
        }
    }, 5000);
});
