/* ==========================================================================
   AGRICULTURE MANIPULATION ROBOT - 2D CANVAS SIMULATION RENDERER
   ========================================================================== */

import { 
    getSimulationWorld, startSimulation, pauseSimulation, resetSimulation, 
    setSimulationSpeed, stepSimulation, sendMove, pickFruit,
    getMissionStatus, stepMission, sendMissionControl 
} from './api.js';
import { showToast } from './ui.js';

let canvas = null;
let ctx = null;
let worldState = null;
let missionState = null;
let animationFrameId = null;

document.addEventListener('DOMContentLoaded', () => {
    initCanvas();
    initSimControls();
});

function initCanvas() {
    canvas = document.getElementById('simCanvas');
    if (!canvas) return;
    ctx = canvas.getContext('2d');

    // Fetch initial world & mission snapshots
    fetchWorld();

    // Start continuous animation loop (~60 FPS)
    startRenderLoop();
}

async function fetchWorld() {
    try {
        const data = await getSimulationWorld();
        if (data && data.field) worldState = data;

        const mData = await getMissionStatus();
        if (mData && mData.state) missionState = mData;

    } catch (err) {
        if (!worldState) worldState = createFallbackWorld();
    }
}

function createFallbackWorld() {
    return {
        field: {
            width: 700,
            height: 450,
            rows: [
                { id: "row_1", y: 100, height: 35, label: "Tomato Row 1" },
                { id: "row_2", y: 220, height: 35, label: "Apple Orchard Row 2" },
                { id: "row_3", y: 340, height: 35, label: "Citrus Lemon Row 3" }
            ]
        },
        robot: {
            operation_mode: "SIMULATION",
            control_mode: "MANUAL",
            estop_engaged: false,
            pose: { x: 80, y: 160, heading: 0 },
            arm: { theta_base: 90, theta_shoulder: 45, theta_elbow: 30, theta_wrist: 0 },
            gripper_state: "OPEN",
            sensors: { distance_cm: 85.0, soil_moisture_percent: 45.0, obstacle_warning: false },
            mission_state: "IDLE"
        },
        fruits: [
            { id: "fruit_1", label: "Ripe Red Apple", x: 180, y: 95, color: "#e53935", radius: 14, picked: false },
            { id: "fruit_2", label: "Ripe Red Apple", x: 380, y: 95, color: "#e53935", radius: 14, picked: false },
            { id: "fruit_3", label: "Yellow Lemon", x: 260, y: 215, color: "#fdd835", radius: 12, picked: false },
            { id: "fruit_4", label: "Ripe Red Apple", x: 480, y: 215, color: "#e53935", radius: 14, picked: false },
            { id: "fruit_5", label: "Yellow Lemon", x: 320, y: 335, color: "#fdd835", radius: 12, picked: false },
            { id: "fruit_6", label: "Unripe Green Fruit", x: 560, y: 335, color: "#4caf50", radius: 12, picked: false }
        ],
        obstacles: [
            { id: "obs_1", label: "Rock Obstacle A", x: 280, y: 160, radius: 22 },
            { id: "obs_2", label: "Rock Obstacle B", x: 440, y: 280, radius: 25 }
        ],
        basket: { capacity: 10, count: 0, items: [] },
        sim_status: { running: false, speed_multiplier: 1.0 }
    };
}

/* --------------------------------------------------------------------------
   Render Loop (~60 FPS)
   -------------------------------------------------------------------------- */
let lastStepTime = 0;

function startRenderLoop() {
    function render(time) {
        if (time - lastStepTime > 100) {
            lastStepTime = time;
            if (worldState && worldState.sim_status && worldState.sim_status.running) {
                if (missionState && ['NAVIGATING_ROW', 'PLANNING_PATH', 'APPROACHING_TARGET'].includes(missionState.state)) {
                    stepMission(0.1).then(mData => {
                        if (mData && mData.state) missionState = mData;
                        return fetchWorld();
                    }).catch(() => {});
                } else {
                    stepSimulation(0.1).then(data => {
                        if (data && data.field) worldState = data;
                    }).catch(() => {});
                }
            } else {
                fetchWorld();
            }
        }

        drawField();
        animationFrameId = requestAnimationFrame(render);
    }
    animationFrameId = requestAnimationFrame(render);
}

/* --------------------------------------------------------------------------
   Canvas Drawing Methods
   -------------------------------------------------------------------------- */
function drawField() {
    if (!ctx || !canvas || !worldState) return;

    const w = canvas.width;
    const h = canvas.height;

    // 1. Clear & Draw Soil Path Background
    ctx.fillStyle = '#d7ccc8'; // Light brown soil tone
    ctx.fillRect(0, 0, w, h);

    // Subtle Soil Grid Texture Lines
    ctx.strokeStyle = 'rgba(141, 110, 99, 0.2)';
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 40) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
    }
    for (let y = 0; y < h; y += 40) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
    }

    // 2. Draw Green Crop Plant Rows
    if (worldState.field && worldState.field.rows) {
        worldState.field.rows.forEach(row => {
            // Dark Soil Mound Border
            ctx.fillStyle = '#5d4037';
            ctx.fillRect(0, row.y - 6, w, row.height + 12);

            // Green Foliage Strip
            ctx.fillStyle = '#1b5e20';
            ctx.fillRect(0, row.y, w, row.height);

            // Foliage Leaf Patterns & Texture Circles
            ctx.fillStyle = '#2e7d32';
            for (let x = 15; x < w; x += 25) {
                ctx.beginPath();
                ctx.arc(x, row.y + row.height / 2, 13, 0, Math.PI * 2);
                ctx.fill();
            }
            ctx.fillStyle = '#4caf50';
            for (let x = 25; x < w; x += 35) {
                ctx.beginPath();
                ctx.arc(x, row.y + row.height / 2 - 4, 8, 0, Math.PI * 2);
                ctx.fill();
            }

            // Row Label Badge
            ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
            ctx.fillRect(10, row.y + 4, 130, row.height - 8);
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 11px sans-serif';
            ctx.textAlign = 'left';
            ctx.fillText(row.label, 16, row.y + row.height / 2 + 4);
        });
    }

    // 3. Draw Field Obstacles (Stones/Rocks)
    if (worldState.obstacles) {
        worldState.obstacles.forEach(obs => {
            ctx.save();

            // Shadow
            ctx.beginPath();
            ctx.arc(obs.x + 4, obs.y + 4, obs.radius, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(0, 0, 0, 0.25)';
            ctx.fill();

            // Rock Body
            ctx.beginPath();
            ctx.arc(obs.x, obs.y, obs.radius, 0, Math.PI * 2);
            ctx.fillStyle = '#607d8b';
            ctx.fill();
            ctx.lineWidth = 3;
            ctx.strokeStyle = '#37474f';
            ctx.stroke();

            // Rock Highlight & Label
            ctx.beginPath();
            ctx.arc(obs.x - 5, obs.y - 5, obs.radius * 0.4, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
            ctx.fill();

            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 10px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(obs.label || 'ROCK', obs.x, obs.y + 3);
            ctx.restore();
        });
    }

    // 4. Draw Planned A* Path Overlay Line & Waypoints
    if (missionState && missionState.planned_path && missionState.planned_path.length > 0) {
        drawPlannedPath(missionState.planned_path);
    }

    // 5. Draw Fruits & Detection Target Reticles
    if (worldState.fruits) {
        worldState.fruits.forEach(fruit => {
            if (fruit.picked) return; // Hide harvested fruits

            ctx.save();

            // Target Bounding Box / Detection Reticle for Ripe Fruits
            if (fruit.color === '#e53935' || fruit.color === '#fdd835') {
                ctx.strokeStyle = 'rgba(33, 150, 243, 0.7)';
                ctx.lineWidth = 1.5;
                ctx.setLineDash([3, 3]);
                ctx.strokeRect(fruit.x - fruit.radius - 4, fruit.y - fruit.radius - 4, (fruit.radius + 4) * 2, (fruit.radius + 4) * 2);
                ctx.setLineDash([]);
            }

            // Fruit Shadow
            ctx.beginPath();
            ctx.arc(fruit.x + 2, fruit.y + 2, fruit.radius, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
            ctx.fill();

            // Main Fruit Circle
            ctx.beginPath();
            ctx.arc(fruit.x, fruit.y, fruit.radius, 0, Math.PI * 2);
            ctx.fillStyle = fruit.color;
            ctx.fill();
            ctx.lineWidth = 2;
            ctx.strokeStyle = '#ffffff';
            ctx.stroke();

            // Fruit Gloss Highlight
            ctx.beginPath();
            ctx.arc(fruit.x - 3, fruit.y - 3, fruit.radius * 0.3, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
            ctx.fill();

            ctx.restore();
        });
    }

    // 6. Draw Mobile Manipulator Robot
    if (worldState.robot && worldState.robot.pose) {
        drawRobot(worldState.robot);
    }

    // 7. Draw Live Canvas Telemetry HUD Overlay
    drawHUD();
}

function drawPlannedPath(waypoints) {
    if (!ctx || !waypoints || waypoints.length < 2) return;

    ctx.save();

    // Dashed Path Line
    ctx.beginPath();
    ctx.moveTo(waypoints[0].x, waypoints[0].y);
    for (let i = 1; i < waypoints.length; i++) {
        ctx.lineTo(waypoints[i].x, waypoints[i].y);
    }
    ctx.strokeStyle = '#facc15'; // Bright yellow path line
    ctx.lineWidth = 3;
    ctx.setLineDash([6, 6]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Waypoint Node Dots
    waypoints.forEach((wp, idx) => {
        ctx.beginPath();
        ctx.arc(wp.x, wp.y, 5, 0, Math.PI * 2);
        ctx.fillStyle = idx === 0 ? '#38bdf8' : (idx === waypoints.length - 1 ? '#ef4444' : '#facc15');
        ctx.fill();
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = '#ffffff';
        ctx.stroke();
    });

    ctx.restore();
}

function drawRobot(robot) {
    const pose = robot.pose;
    const rad = (pose.heading * Math.PI) / 180;

    ctx.save();
    ctx.translate(pose.x, pose.y);
    ctx.rotate(rad);

    const cw = 42; // Chassis Width
    const cl = 54; // Chassis Length

    // --- Camera Vision FOV Cone ---
    ctx.beginPath();
    ctx.moveTo(cl / 2, 0);
    ctx.lineTo(cl / 2 + 90, -40);
    ctx.lineTo(cl / 2 + 90, 40);
    ctx.closePath();
    ctx.fillStyle = 'rgba(33, 150, 243, 0.12)';
    ctx.fill();

    // --- Ultrasonic Range Beam ---
    const dist = robot.sensors ? robot.sensors.distance_cm : 85;
    const isWarn = robot.sensors && robot.sensors.obstacle_warning;
    ctx.beginPath();
    ctx.moveTo(cl / 2, 0);
    ctx.lineTo(cl / 2 + dist, 0);
    ctx.strokeStyle = isWarn ? '#d32f2f' : '#388e3c';
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 4]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Ultrasonic Sensor Endpoint Dot
    ctx.beginPath();
    ctx.arc(cl / 2 + dist, 0, isWarn ? 6 : 4, 0, Math.PI * 2);
    ctx.fillStyle = isWarn ? '#d32f2f' : '#4caf50';
    ctx.fill();

    // --- 4 Treaded Wheels ---
    ctx.fillStyle = '#212121';
    const rw = 16, rh = 8;
    ctx.fillRect(-cl / 2 + 4, -cw / 2 - rh, rw, rh);  // Top-Left
    ctx.fillRect(cl / 2 - 20, -cw / 2 - rh, rw, rh);  // Top-Right
    ctx.fillRect(-cl / 2 + 4, cw / 2, rw, rh);         // Bottom-Left
    ctx.fillRect(cl / 2 - 20, cw / 2, rw, rh);        // Bottom-Right

    // Wheel Tread Marks
    ctx.fillStyle = '#616161';
    ctx.fillRect(-cl / 2 + 10, -cw / 2 - rh, 4, rh);
    ctx.fillRect(cl / 2 - 14, -cw / 2 - rh, 4, rh);
    ctx.fillRect(-cl / 2 + 10, cw / 2, 4, rh);
    ctx.fillRect(cl / 2 - 14, cw / 2, 4, rh);

    // --- Main Mobile Chassis ---
    ctx.fillStyle = '#2e7d32'; // Forest Green
    ctx.beginPath();
    ctx.roundRect(-cl / 2, -cw / 2, cl, cw, 8);
    ctx.fill();
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = '#1b5e20';
    ctx.stroke();

    // Chassis Top Panel Trim
    ctx.fillStyle = '#388e3c';
    ctx.fillRect(-cl / 2 + 8, -cw / 2 + 6, cl - 16, cw - 12);

    // --- Rear Onboard Collection Basket ---
    ctx.fillStyle = '#d84315';
    ctx.fillRect(-cl / 2 + 3, -cw / 2 + 8, 16, cw - 16);
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = '#ffffff';
    ctx.strokeRect(-cl / 2 + 3, -cw / 2 + 8, 16, cw - 16);

    // Basket Collected Fruit Count
    const bCount = worldState.basket ? worldState.basket.count : 0;
    if (bCount > 0) {
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 10px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(`${bCount}`, -cl / 2 + 11, 4);
    }

    // --- 4-DOF Robotic Arm Base & Articulation Link ---
    ctx.beginPath();
    ctx.arc(8, 0, 9, 0, Math.PI * 2);
    ctx.fillStyle = '#1565c0';
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#ffffff';
    ctx.stroke();

    // Servo Arm Link Pointer
    const armRad = ((robot.arm ? robot.arm.theta_base : 90) * Math.PI) / 180;
    const armLen = 24;
    const armEndX = 8 + armLen * Math.cos(armRad - Math.PI / 2);
    const armEndY = armLen * Math.sin(armRad - Math.PI / 2);

    ctx.beginPath();
    ctx.moveTo(8, 0);
    ctx.lineTo(armEndX, armEndY);
    ctx.lineWidth = 4;
    ctx.strokeStyle = '#ff9800';
    ctx.stroke();

    // Parallel Gripper Jaws
    const isClosed = robot.gripper_state === 'CLOSE';
    const jawGap = isClosed ? 3 : 8;

    ctx.save();
    ctx.translate(armEndX, armEndY);
    ctx.fillStyle = isClosed ? '#e53935' : '#f57c00';
    ctx.fillRect(0, -jawGap - 2, 8, 3);
    ctx.fillRect(0, jawGap, 8, 3);
    ctx.restore();

    // Forward Direction Arrow
    ctx.beginPath();
    ctx.moveTo(cl / 2 - 6, -5);
    ctx.lineTo(cl / 2 + 5, 0);
    ctx.lineTo(cl / 2 - 6, 5);
    ctx.fillStyle = '#ffffff';
    ctx.fill();

    ctx.restore();
}

function drawHUD() {
    if (!ctx || !worldState || !worldState.robot) return;

    const robot = worldState.robot;
    const pose = robot.pose || { x: 0, y: 0, heading: 0 };
    const sensors = robot.sensors || { distance_cm: 0, soil_moisture_percent: 0, obstacle_warning: false };
    const basket = worldState.basket || { count: 0, capacity: 10 };
    const isRunning = worldState.sim_status ? worldState.sim_status.running : false;

    // Top Left Telemetry Overlay Banner
    ctx.fillStyle = 'rgba(15, 23, 42, 0.82)';
    ctx.fillRect(10, 10, 240, 68);
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.strokeRect(10, 10, 240, 68);

    ctx.fillStyle = '#ffffff';
    ctx.font = '11px var(--font-mono, monospace)';
    ctx.textAlign = 'left';
    ctx.fillText(`POS: X=${pose.x.toFixed(1)} cm, Y=${pose.y.toFixed(1)} cm`, 18, 28);
    ctx.fillText(`HEADING: ${pose.heading.toFixed(1)}°`, 18, 45);
    ctx.fillText(`STATUS: ${robot.mission_state || 'IDLE'}`, 18, 62);

    // Top Right Sensor & Basket Banner
    ctx.fillStyle = 'rgba(15, 23, 42, 0.82)';
    ctx.fillRect(canvas.width - 230, 10, 220, 68);
    ctx.strokeRect(canvas.width - 230, 10, 220, 68);

    ctx.fillStyle = sensors.obstacle_warning ? '#ef4444' : '#4ade80';
    ctx.fillText(`ULTRASONIC: ${sensors.distance_cm.toFixed(1)} cm`, canvas.width - 220, 28);

    ctx.fillStyle = '#38bdf8';
    ctx.fillText(`SOIL MOISTURE: ${sensors.soil_moisture_percent.toFixed(1)}%`, canvas.width - 220, 45);

    ctx.fillStyle = '#facc15';
    ctx.fillText(`BASKET: ${basket.count} / ${basket.capacity} FRUITS`, canvas.width - 220, 62);
}

/* --------------------------------------------------------------------------
   Simulation UI Control Event Listeners
   -------------------------------------------------------------------------- */
function initSimControls() {
    const btnStart = document.getElementById('btnStartSim');
    const btnPause = document.getElementById('btnPauseSim');
    const btnReset = document.getElementById('btnResetSim');
    const btnHarvest = document.getElementById('btnHarvestFruit');
    const speedSlider = document.getElementById('simSpeedSlider');
    const statusPill = document.getElementById('simStatusPill');

    // Simulation Engine Controls
    if (btnStart) {
        btnStart.addEventListener('click', async () => {
            if (worldState) worldState.sim_status.running = true;
            try { 
                await startSimulation(); 
                await sendMissionControl('START');
            } catch (err) {}
            if (statusPill) {
                statusPill.innerHTML = '<span class="status-indicator-dot dot-active"></span> Engine Running';
            }
            showToast('▶ Physics Simulation & Mission Planner Started', 'info');
        });
    }

    if (btnPause) {
        btnPause.addEventListener('click', async () => {
            if (worldState) worldState.sim_status.running = false;
            try { 
                await pauseSimulation(); 
                await sendMissionControl('PAUSE');
            } catch (err) {}
            if (statusPill) {
                statusPill.innerHTML = '<span class="status-indicator-dot dot-offline"></span> Engine Paused';
            }
            showToast('⏸ Mission Paused', 'warning');
        });
    }

    if (btnReset) {
        btnReset.addEventListener('click', async () => {
            try {
                const data = await resetSimulation();
                if (data && data.world) worldState = data.world;
                const mData = await sendMissionControl('RESET');
                if (mData) missionState = mData;
            } catch (err) {
                worldState = createFallbackWorld();
            }
            if (statusPill) {
                statusPill.innerHTML = '<span class="status-indicator-dot dot-online"></span> Engine Reset';
            }
            showToast('🔄 Field & Mission Reset to Initial State', 'success');
        });
    }

    if (btnHarvest) {
        btnHarvest.addEventListener('click', async () => {
            try {
                const res = await pickFruit();
                if (res && res.world) worldState = res.world;
                const resultData = res.result || res;
                if (resultData.success) {
                    showToast(`✅ ${resultData.message}`, 'success');
                } else {
                    showToast(`⚠️ ${resultData.message}`, 'warning');
                }
            } catch (err) {
                showToast(`⚠️ Harvest command failed: ${err.message}`, 'danger');
            }
        });
    }

    if (speedSlider) {
        speedSlider.addEventListener('input', async (e) => {
            const speed = parseFloat(e.target.value);
            if (worldState) worldState.sim_status.speed_multiplier = speed;
            try { await setSimulationSpeed(speed); } catch (err) {}
        });
    }

    // Simulation Page D-Pad Drive Controls
    const btnFwd = document.getElementById('btnSimDriveForward');
    const btnRev = document.getElementById('btnSimDriveReverse');
    const btnLeft = document.getElementById('btnSimDriveLeft');
    const btnRight = document.getElementById('btnSimDriveRight');
    const btnStop = document.getElementById('btnSimDriveStop');

    const handleSimMove = async (dir) => {
        try {
            await sendMove(dir, 1.0);
            fetchWorld();
        } catch (err) {
            showToast(err.message, 'warning');
        }
    };

    if (btnFwd) btnFwd.addEventListener('click', () => handleSimMove('forward'));
    if (btnRev) btnRev.addEventListener('click', () => handleSimMove('backward'));
    if (btnLeft) btnLeft.addEventListener('click', () => handleSimMove('left'));
    if (btnRight) btnRight.addEventListener('click', () => handleSimMove('right'));
    if (btnStop) btnStop.addEventListener('click', () => handleSimMove('stop'));
}
