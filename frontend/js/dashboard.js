/* ==========================================================================
   AGRICULTURE MANIPULATION ROBOT - LIVE DASHBOARD & TELEOPERATION CONTROLLER
   ========================================================================== */

import { getRobotStatus, sendMove, sendArmAngles, sendGripper, sendMode, sendEStop } from './api.js';
import { showToast } from './ui.js';

let updateInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    initTeleoperationControls();
    initKeyboardDrive();
    startTelemetryLoop();
});

/* --------------------------------------------------------------------------
   1. Telemetry Polling Loop (~5 Hz)
   -------------------------------------------------------------------------- */
function startTelemetryLoop() {
    updateTelemetry();
    updateInterval = setInterval(updateTelemetry, 250);
}

async function updateTelemetry() {
    try {
        const status = await getRobotStatus();
        if (!status) return;

        // Position & Heading
        const posSpan = document.getElementById('telemetryPos');
        if (posSpan && status.pose) {
            posSpan.textContent = `X: ${status.pose.x.toFixed(1)} cm, Y: ${status.pose.y.toFixed(1)} cm`;
        }

        const headingSpan = document.getElementById('telemetryHeading');
        if (headingSpan && status.pose) {
            headingSpan.textContent = `${status.pose.heading.toFixed(1)}°`;
        }

        // Sensors
        const distSpan = document.getElementById('telemetryDistance');
        if (distSpan && status.sensors) {
            const dist = status.sensors.distance_cm;
            if (status.sensors.obstacle_warning || dist < 30) {
                distSpan.textContent = `⚠️ ${dist.toFixed(1)} cm (HAZARD BRAKE)`;
                distSpan.style.color = 'var(--status-danger)';
            } else {
                distSpan.textContent = `${dist.toFixed(1)} cm (Clear)`;
                distSpan.style.color = 'var(--status-success)';
            }
        }

        const soilSpan = document.getElementById('telemetrySoil');
        if (soilSpan && status.sensors) {
            soilSpan.textContent = `${status.sensors.soil_moisture_percent.toFixed(1)}% (Normal)`;
        }

        // Arm Angles
        if (status.arm) {
            const b = document.getElementById('angleBase');
            const s = document.getElementById('angleShoulder');
            const e = document.getElementById('angleElbow');
            if (b) b.textContent = `${status.arm.theta_base}°`;
            if (s) s.textContent = `${status.arm.theta_shoulder}°`;
            if (e) e.textContent = `${status.arm.theta_elbow}°`;
        }

        // Gripper
        const gripSpan = document.getElementById('gripperState');
        if (gripSpan && status.gripper_state) {
            gripSpan.textContent = status.gripper_state;
            gripSpan.className = `badge badge-${status.gripper_state === 'OPEN' ? 'success' : 'warning'}`;
        }

        // Control Mode Badge
        const modeBadge = document.getElementById('controlModeBadge');
        if (modeBadge && status.control_mode) {
            modeBadge.textContent = `MODE: ${status.control_mode}`;
        }

    } catch (err) {
        // Backend offline, fallback handles display silently
    }
}

/* --------------------------------------------------------------------------
   2. Teleoperation D-Pad Click Listeners
   -------------------------------------------------------------------------- */
function initTeleoperationControls() {
    const btnFwd = document.getElementById('btnDriveForward');
    const btnRev = document.getElementById('btnDriveReverse');
    const btnLeft = document.getElementById('btnDriveLeft');
    const btnRight = document.getElementById('btnDriveRight');
    const btnStop = document.getElementById('btnDriveStop');

    if (btnFwd) btnFwd.addEventListener('click', () => handleMove('forward'));
    if (btnRev) btnRev.addEventListener('click', () => handleMove('backward'));
    if (btnLeft) btnLeft.addEventListener('click', () => handleMove('left'));
    if (btnRight) btnRight.addEventListener('click', () => handleMove('right'));
    if (btnStop) btnStop.addEventListener('click', () => handleMove('stop'));
}

async function handleMove(direction) {
    try {
        await sendMove(direction, 1.0);
        appendTerminalLog(`[COMMAND] Move: ${direction.toUpperCase()}`);
    } catch (err) {
        appendTerminalLog(`[WARN] ${err.message}`, 'warn');
        showToast(err.message, 'warning');
    }
}

/* --------------------------------------------------------------------------
   3. WASD & Arrow Keys Keyboard Driving
   -------------------------------------------------------------------------- */
function initKeyboardDrive() {
    document.addEventListener('keydown', (e) => {
        // Ignore if typing in text inputs
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        let direction = null;
        if (e.key === 'w' || e.key === 'W' || e.key === 'ArrowUp') direction = 'forward';
        else if (e.key === 's' || e.key === 'S' || e.key === 'ArrowDown') direction = 'backward';
        else if (e.key === 'a' || e.key === 'A' || e.key === 'ArrowLeft') direction = 'left';
        else if (e.key === 'd' || e.key === 'D' || e.key === 'ArrowRight') direction = 'right';
        else if (e.key === 'x' || e.key === 'X') direction = 'stop';

        if (direction) {
            e.preventDefault();
            handleMove(direction);
        }
    });
}

/* --------------------------------------------------------------------------
   4. Terminal Log Console Helper
   -------------------------------------------------------------------------- */
function appendTerminalLog(message, level = 'info') {
    const terminal = document.getElementById('dashboardTerminalLog');
    if (!terminal) return;

    const timeStr = new Date().toLocaleTimeString();
    const line = document.createElement('div');
    line.className = 'terminal-line';
    line.innerHTML = `<span class="terminal-time">[${timeStr}]</span> <span class="terminal-${level}">${message}</span>`;
    
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
}
