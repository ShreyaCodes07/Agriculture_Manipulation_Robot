/* ==========================================================================
   AGRICULTURE MANIPULATION ROBOT - MISSION PLANNER & ROW NAVIGATION CONTROLLER
   ========================================================================== */

import { getMissionStatus, sendMissionControl, sendMode } from './api.js';
import { showToast } from './ui.js';

let missionLoopInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    initMissionControls();
    startMissionLoop();
});

function startMissionLoop() {
    updateMissionUI();
    missionLoopInterval = setInterval(updateMissionUI, 250);
}

async function updateMissionUI() {
    try {
        const m = await getMissionStatus();
        if (!m) return;

        // 1. Mission State & Status Badges
        const stateBadge = document.getElementById('missionStateBadge');
        if (stateBadge) {
            stateBadge.textContent = `STATE: ${m.state}`;
            stateBadge.className = `badge badge-${m.state === 'COMPLETED' ? 'success' : (m.state === 'EMERGENCY_STOP' ? 'danger' : 'sim')}`;
        }

        const msgText = document.getElementById('missionStatusMsg');
        if (msgText) msgText.textContent = m.message || 'Mission Planner ready.';

        // 2. Progress Bar & Counts
        const progressBar = document.getElementById('missionProgressBar');
        if (progressBar) {
            progressBar.style.width = `${m.progress_percent}%`;
            progressBar.textContent = `${m.progress_percent.toFixed(0)}%`;
        }

        const countSpan = document.getElementById('missionHarvestCount');
        if (countSpan) {
            countSpan.textContent = `${m.completed_count} / ${m.total_count} Targets`;
        }

        const targetSpan = document.getElementById('missionCurrentTarget');
        if (targetSpan) {
            targetSpan.textContent = m.current_target_id ? m.current_target_id.toUpperCase() : 'None';
        }

        const waypointsSpan = document.getElementById('missionWaypointsCount');
        if (waypointsSpan) {
            waypointsSpan.textContent = m.planned_path ? `${m.planned_path.length} Nodes` : '0 Nodes';
        }

        // 3. Render Mission Target Queue Table
        renderMissionTargetTable(m.targets, m.current_target_id);

    } catch (err) {
        // Backend offline, fallback handles display silently
    }
}

function renderMissionTargetTable(targets, activeTargetId) {
    const tbody = document.getElementById('missionTargetsTbody');
    if (!tbody) return;

    if (!targets || targets.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-secondary);">No active mission targets queued. Select a mission type and click Start!</td></tr>`;
        return;
    }

    tbody.innerHTML = targets.map((t, idx) => {
        const isActive = t.fruit_id === activeTargetId;
        let badgeClass = 'sim';
        if (t.status === 'HARVESTED') badgeClass = 'success';
        else if (t.status === 'ACTIVE') badgeClass = 'warning';
        else if (t.status === 'SKIPPED') badgeClass = 'danger';

        return `
            <tr style="${isActive ? 'background: rgba(33, 150, 243, 0.12); font-weight: 600;' : ''}">
                <td>${idx + 1}</td>
                <td><strong>${t.fruit_id}</strong></td>
                <td>${t.label}</td>
                <td>X: ${t.field_x} cm, Y: ${t.field_y} cm</td>
                <td><span class="badge badge-${badgeClass}">${t.status}</span></td>
            </tr>
        `;
    }).join('');
}

function initMissionControls() {
    const btnStart = document.getElementById('btnStartMission');
    const btnPause = document.getElementById('btnPauseMission');
    const btnResume = document.getElementById('btnResumeMission');
    const btnStop = document.getElementById('btnStopMission');
    const btnReset = document.getElementById('btnResetMission');
    const missionSelect = document.getElementById('missionTypeSelect');
    const modeToggle = document.getElementById('btnToggleAutoMode');

    if (btnStart) {
        btnStart.addEventListener('click', async () => {
            const mType = missionSelect ? missionSelect.value : 'HARVEST_ALL';
            try {
                const res = await sendMissionControl('START', mType);
                showToast(`🚀 Harvesting Mission Started (${mType})`, 'success');
                updateMissionUI();
            } catch (err) {
                showToast(`Mission start failed: ${err.message}`, 'danger');
            }
        });
    }

    if (btnPause) {
        btnPause.addEventListener('click', async () => {
            try {
                await sendMissionControl('PAUSE');
                showToast('⏸ Mission Paused', 'warning');
                updateMissionUI();
            } catch (err) {
                showToast(err.message, 'danger');
            }
        });
    }

    if (btnResume) {
        btnResume.addEventListener('click', async () => {
            try {
                await sendMissionControl('RESUME');
                showToast('▶ Mission Resumed', 'info');
                updateMissionUI();
            } catch (err) {
                showToast(err.message, 'danger');
            }
        });
    }

    if (btnStop) {
        btnStop.addEventListener('click', async () => {
            try {
                await sendMissionControl('STOP');
                showToast('⏹ Mission Stopped', 'danger');
                updateMissionUI();
            } catch (err) {
                showToast(err.message, 'danger');
            }
        });
    }

    if (btnReset) {
        btnReset.addEventListener('click', async () => {
            const mType = missionSelect ? missionSelect.value : 'HARVEST_ALL';
            try {
                await sendMissionControl('RESET', mType);
                showToast(`🔄 Mission & Target Queue Reset (${mType})`, 'info');
                updateMissionUI();
            } catch (err) {
                showToast(err.message, 'danger');
            }
        });
    }

    if (missionSelect) {
        missionSelect.addEventListener('change', async (e) => {
            const mType = e.target.value;
            try {
                await sendMissionControl('RESET', mType);
                showToast(`Selected Mission Plan: ${mType}`, 'info');
                updateMissionUI();
            } catch (err) {}
        });
    }

    if (modeToggle) {
        let isAuto = true;
        modeToggle.addEventListener('click', async () => {
            isAuto = !isAuto;
            const mode = isAuto ? 'AUTONOMOUS' : 'MANUAL';
            try {
                await sendMode(mode);
                modeToggle.textContent = `MODE: ${mode}`;
                showToast(`Switched control mode to ${mode}`, 'info');
            } catch (err) {
                showToast(err.message, 'danger');
            }
        });
    }
}
