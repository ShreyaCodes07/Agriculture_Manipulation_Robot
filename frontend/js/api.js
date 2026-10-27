/* ==========================================================================
   AGRICULTURE MANIPULATION ROBOT - REST API CLIENT HELPER
   ========================================================================== */

/* Dynamic API Base URL resolution for local dev & cloud deployment */
const API_BASE_URL = window.AGRIBOT_API_URL || (
    window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? (window.location.port === '8000' ? '' : 'http://localhost:8000')
        : window.location.origin
);

async function apiRequest(endpoint, method = 'GET', body = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    if (body !== null && body !== undefined) {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        if (!response.ok) {
            const errData = await response.json().catch(() => ({ detail: 'Network response error' }));
            throw new Error(errData.detail || `HTTP Error ${response.status}`);
        }
        return await response.json();
    } catch (err) {
        console.warn(`[API Client Warning] ${endpoint}: ${err.message}`);
        throw err;
    }
}

// Fetch Full System Telemetry Status
export async function getRobotStatus() {
    return await apiRequest('/api/status');
}

// Fetch Health Check
export async function getHealthCheck() {
    return await apiRequest('/api/health');
}

// Teleoperation Command: Move Chassis
export async function sendMove(direction, speed = 1.0) {
    return await apiRequest('/api/move', 'POST', { direction, speed });
}

// Set Arm Joint Angles
export async function sendArmAngles(theta_base, theta_shoulder, theta_elbow, theta_wrist = 0.0) {
    return await apiRequest('/api/arm', 'POST', {
        theta_base,
        theta_shoulder,
        theta_elbow,
        theta_wrist
    });
}

// Gripper Open / Close Action
export async function sendGripper(state) {
    return await apiRequest('/api/gripper', 'POST', { state });
}

// Mode Switch: MANUAL or AUTONOMOUS
export async function sendMode(mode) {
    return await apiRequest('/api/mode', 'POST', { mode });
}

// Emergency Stop Trigger
export async function sendEStop(action) {
    return await apiRequest('/api/estop', 'POST', { action });
}

// Fetch SQLite Test Verification Results
export async function getTestResults() {
    return await apiRequest('/api/results');
}

// Fetch System Mission Console Logs
export async function getMissionLogs() {
    return await apiRequest('/api/logs');
}

// --- 2D Simulation Engine APIs ---
export async function getSimulationWorld() {
    return await apiRequest('/api/simulation/world');
}

export async function startSimulation() {
    return await apiRequest('/api/simulation/start', 'POST');
}

export async function pauseSimulation() {
    return await apiRequest('/api/simulation/pause', 'POST');
}

export async function resetSimulation() {
    return await apiRequest('/api/simulation/reset', 'POST');
}

export async function setSimulationSpeed(speed) {
    return await apiRequest('/api/simulation/speed', 'POST', { speed });
}

export async function stepSimulation(dt = 0.1) {
    return await apiRequest('/api/simulation/step', 'POST', { dt });
}

export async function pickFruit() {
    return await apiRequest('/api/simulation/pick', 'POST');
}

// --- Computer Vision & Fruit Detection APIs ---
export async function getVisionDetection() {
    return await apiRequest('/api/vision/detect');
}

export async function startVisionDetection() {
    return await apiRequest('/api/vision/start', 'POST');
}

export async function stopVisionDetection() {
    return await apiRequest('/api/vision/stop', 'POST');
}

export async function selectVisionTarget(fruit_id) {
    return await apiRequest('/api/vision/select_target', 'POST', { fruit_id });
}

export async function navigateVisionTarget() {
    return await apiRequest('/api/vision/navigate', 'POST');
}

export async function updateVisionHSV(h_min = 0, s_min = 100, v_min = 100, h_max = 10, s_max = 255, v_max = 255) {
    return await apiRequest('/api/vision/hsv', 'POST', {
        h_min,
        s_min,
        v_min,
        h_max,
        s_max,
        v_max
    });
}

// --- Mission Planner & Autonomous Row Navigation APIs ---
export async function getMissionStatus() {
    return await apiRequest('/api/mission/status');
}

export async function sendMissionControl(action, mission_type = 'HARVEST_ALL') {
    return await apiRequest('/api/mission/control', 'POST', { action, mission_type });
}

export async function stepMission(dt = 0.1) {
    return await apiRequest('/api/mission/step', 'POST', { dt });
}

export async function planCustomPath(start_x, start_y, goal_x, goal_y) {
    return await apiRequest('/api/mission/plan_path', 'POST', { start_x, start_y, goal_x, goal_y });
}

// --- 4-DOF Manipulator Arm & IK APIs ---
export async function getArmStatus() {
    return await apiRequest('/api/arm/status');
}

export async function sendArmIK(x, y, z = 10.0, pitch = 0.0) {
    return await apiRequest('/api/arm/ik', 'POST', { x, y, z, pitch });
}

export async function runPickSequence(fruit_id = null) {
    return await apiRequest('/api/arm/pick_sequence', 'POST', { fruit_id });
}
