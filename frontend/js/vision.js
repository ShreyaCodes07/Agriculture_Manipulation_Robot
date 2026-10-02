/* ==========================================================================
   AGRICULTURE MANIPULATION ROBOT - VISION LAB & TARGET DETECTION CONTROLLER
   ========================================================================== */

import { getVisionDetection, startVisionDetection, stopVisionDetection, selectVisionTarget, navigateVisionTarget, updateVisionHSV } from './api.js';
import { showToast } from './ui.js';

let visionLoopInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    initVisionControls();
    startVisionLoop();
});

/* --------------------------------------------------------------------------
   1. Real-Time Vision Polling Loop (~4 Hz)
   -------------------------------------------------------------------------- */
function startVisionLoop() {
    updateVisionFeed();
    visionLoopInterval = setInterval(updateVisionFeed, 250);
}

async function updateVisionFeed() {
    try {
        const data = await getVisionDetection();
        if (!data) return;

        // 1. Update Camera Feed Image on Live Dashboard
        const dashboardFeed = document.getElementById('dashboardCameraFeed');
        if (dashboardFeed && data.camera_frame_b64) {
            dashboardFeed.src = data.camera_frame_b64;
            dashboardFeed.style.display = 'block';
            const placeholder = document.getElementById('dashboardCameraPlaceholder');
            if (placeholder) placeholder.style.display = 'none';
        }

        // 2. Update Camera Feed Image on Vision Lab Page
        const labFeed = document.getElementById('visionLabCameraFeed');
        if (labFeed && data.camera_frame_b64) {
            labFeed.src = data.camera_frame_b64;
            labFeed.style.display = 'block';
            const placeholder = document.getElementById('visionLabPlaceholder');
            if (placeholder) placeholder.style.display = 'none';
        }

        // 3. Update Vision Status Badges & Pills
        const statusPill = document.getElementById('visionStatusPill');
        if (statusPill) {
            statusPill.innerHTML = data.active
                ? `<span class="status-indicator-dot dot-active"></span> OpenCV Active (${data.detected_count} Targets)`
                : `<span class="status-indicator-dot dot-offline"></span> OpenCV Paused`;
        }

        // 4. Update Target Status Display
        const targetStatusSpan = document.getElementById('activeTargetStatus');
        if (targetStatusSpan) {
            targetStatusSpan.textContent = data.target_fruit_id 
                ? `Locked on ${data.target_fruit_id.toUpperCase()}` 
                : 'No Active Target';
        }

        // 5. Update Detected Objects Table on Vision Lab
        renderDetectedObjectsTable(data.objects, data.target_fruit_id);

    } catch (err) {
        // Backend offline, fallback handles display silently
    }
}

/* --------------------------------------------------------------------------
   2. Render Detected Fruits Table in Vision Lab
   -------------------------------------------------------------------------- */
function renderDetectedObjectsTable(objects, activeTargetId) {
    const tbody = document.getElementById('visionDetectionsTbody');
    if (!tbody) return;

    if (!objects || objects.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-secondary);">No fruit targets currently detected in camera FOV. Drive robot near crop rows!</td></tr>`;
        return;
    }

    tbody.innerHTML = objects.map(obj => {
        const isTarget = obj.fruit_id === activeTargetId;
        const confidencePct = Math.round(obj.confidence * 100);

        return `
            <tr style="${isTarget ? 'background: rgba(33, 150, 243, 0.12); font-weight: 600;' : ''}">
                <td><strong>${obj.fruit_id}</strong></td>
                <td>
                    <span class="badge badge-${obj.is_ripe ? 'success' : 'warning'}">${obj.label}</span>
                </td>
                <td>${confidencePct}%</td>
                <td><code>[${obj.bbox.join(', ')}]</code></td>
                <td>X: ${obj.field_x} cm, Y: ${obj.field_y} cm (${obj.distance_cm} cm away)</td>
                <td>
                    ${isTarget 
                        ? `<span class="badge badge-sim">🎯 LOCKED TARGET</span>`
                        : `<button class="btn btn-outline select-target-btn" data-fruit-id="${obj.fruit_id}" style="padding: 2px 8px; font-size: 0.8rem;">🎯 Lock Target</button>`
                    }
                </td>
            </tr>
        `;
    }).join('');

    // Attach click handlers to dynamic target buttons
    const targetBtns = tbody.querySelectorAll('.select-target-btn');
    targetBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            const fruitId = btn.getAttribute('data-fruit-id');
            try {
                await selectVisionTarget(fruitId);
                showToast(`🎯 Locked target onto ${fruitId}`, 'info');
                updateVisionFeed();
            } catch (err) {
                showToast(`Failed to select target: ${err.message}`, 'danger');
            }
        });
    });
}

/* --------------------------------------------------------------------------
   3. Vision Control Event Listeners
   -------------------------------------------------------------------------- */
function initVisionControls() {
    const btnStart = document.getElementById('btnStartVision');
    const btnStop = document.getElementById('btnStopVision');
    const btnNavigate = document.getElementById('btnNavigateTarget');
    const targetSelect = document.getElementById('visionTargetSelect');

    if (btnStart) {
        btnStart.addEventListener('click', async () => {
            try {
                await startVisionDetection();
                showToast('👁️ OpenCV Computer Vision Pipeline Started', 'success');
                updateVisionFeed();
            } catch (err) {
                showToast(err.message, 'danger');
            }
        });
    }

    if (btnStop) {
        btnStop.addEventListener('click', async () => {
            try {
                await stopVisionDetection();
                showToast('⏸ OpenCV Vision Pipeline Paused', 'warning');
                updateVisionFeed();
            } catch (err) {
                showToast(err.message, 'danger');
            }
        });
    }

    if (targetSelect) {
        targetSelect.addEventListener('change', async (e) => {
            const fruitId = e.target.value;
            try {
                await selectVisionTarget(fruitId);
                showToast(`🎯 Target fruit set to ${fruitId}`, 'info');
                updateVisionFeed();
            } catch (err) {
                showToast(err.message, 'danger');
            }
        });
    }

    if (btnNavigate) {
        btnNavigate.addEventListener('click', async () => {
            try {
                const res = await navigateVisionTarget();
                if (res.status === 'harvested') {
                    showToast(`🎉 ${res.message}`, 'success');
                } else {
                    showToast(`🚀 ${res.message}`, 'info');
                }
            } catch (err) {
                showToast(`Navigation error: ${err.message}`, 'danger');
            }
        });
    }

    // HSV Slider Change Listeners
    const hMin = document.getElementById('hMinSlider');
    const sMin = document.getElementById('sMinSlider');
    const vMin = document.getElementById('vMinSlider');

    const handleHsvChange = async () => {
        const hVal = parseInt(hMin ? hMin.value : 0);
        const sVal = parseInt(sMin ? sMin.value : 100);
        const vVal = parseInt(vMin ? vMin.value : 100);

        try {
            await updateVisionHSV(hVal, sVal, vVal);
            updateVisionFeed();
        } catch (err) {}
    };

    if (hMin) hMin.addEventListener('input', handleHsvChange);
    if (sMin) sMin.addEventListener('input', handleHsvChange);
    if (vMin) vMin.addEventListener('input', handleHsvChange);
}
