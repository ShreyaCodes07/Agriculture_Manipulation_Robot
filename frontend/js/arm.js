/* ==========================================================================
   AGRICULTURE MANIPULATION ROBOT - 4-DOF ARM & IK CONTROLLER
   ========================================================================== */

import { getArmStatus, sendArmAngles, sendGripper, sendArmIK, runPickSequence } from './api.js';
import { showToast } from './ui.js';

let armLoopInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    initArmControls();
    startArmLoop();
});

function startArmLoop() {
    updateArmUI();
    armLoopInterval = setInterval(updateArmUI, 250);
}

async function updateArmUI() {
    try {
        const data = await getArmStatus();
        if (!data || !data.arm) return;

        // Update Slider Display Numbers
        const arm = data.arm;
        setSpanText('armBaseVal', `${arm.theta_base.toFixed(0)}°`);
        setSpanText('armShoulderVal', `${arm.theta_shoulder.toFixed(0)}°`);
        setSpanText('armElbowVal', `${arm.theta_elbow.toFixed(0)}°`);
        setSpanText('armWristVal', `${arm.theta_wrist.toFixed(0)}°`);

        // Update End Effector 3D Cartesian Position
        if (data.end_effector_pos) {
            const pos = data.end_effector_pos;
            setSpanText('armEEPosText', `X: ${pos.x} cm, Y: ${pos.y} cm, Z: ${pos.z} cm`);
        }

        // Update Gripper State Badge
        const gripBadge = document.getElementById('armGripperBadge');
        if (gripBadge) {
            gripBadge.textContent = `GRIPPER: ${data.gripper_state || 'OPEN'}`;
            gripBadge.className = `badge badge-${data.gripper_state === 'OPEN' ? 'success' : 'warning'}`;
        }

        // Update Trajectory State Badge
        const trajBadge = document.getElementById('armTrajStateBadge');
        if (trajBadge) {
            trajBadge.textContent = `TRAJECTORY: ${data.sequence_state || 'HOME'}`;
        }

    } catch (err) {
        // Backend offline, fallback handles display silently
    }
}

function setSpanText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function initArmControls() {
    const bSlider = document.getElementById('armBaseSlider');
    const sSlider = document.getElementById('armShoulderSlider');
    const eSlider = document.getElementById('armElbowSlider');
    const wSlider = document.getElementById('armWristSlider');

    const handleSliderChange = async () => {
        const b = parseFloat(bSlider ? bSlider.value : 90);
        const s = parseFloat(sSlider ? sSlider.value : 45);
        const e = parseFloat(eSlider ? eSlider.value : 30);
        const w = parseFloat(wSlider ? wSlider.value : 0);

        try {
            await sendArmAngles(b, s, e, w);
            updateArmUI();
        } catch (err) {}
    };

    if (bSlider) bSlider.addEventListener('input', handleSliderChange);
    if (sSlider) sSlider.addEventListener('input', handleSliderChange);
    if (eSlider) eSlider.addEventListener('input', handleSliderChange);
    if (wSlider) wSlider.addEventListener('input', handleSliderChange);

    // Gripper Controls
    const btnOpenGrip = document.getElementById('btnOpenGripper');
    const btnCloseGrip = document.getElementById('btnCloseGripper');

    if (btnOpenGrip) {
        btnOpenGrip.addEventListener('click', async () => {
            try {
                await sendGripper('OPEN');
                showToast('👐 Gripper Opened', 'info');
                updateArmUI();
            } catch (err) {
                showToast(err.message, 'danger');
            }
        });
    }

    if (btnCloseGrip) {
        btnCloseGrip.addEventListener('click', async () => {
            try {
                const res = await sendGripper('CLOSE');
                showToast('✊ Gripper Closed (Harvest Triggered)', 'warning');
                updateArmUI();
            } catch (err) {
                showToast(err.message, 'danger');
            }
        });
    }

    // Inverse Kinematics (IK) Solver Controls
    const btnSolveIK = document.getElementById('btnSolveIK');
    if (btnSolveIK) {
        btnSolveIK.addEventListener('click', async () => {
            const xInput = document.getElementById('ikInputX');
            const yInput = document.getElementById('ikInputY');
            const zInput = document.getElementById('ikInputZ');

            const ikX = parseFloat(xInput ? xInput.value : 25.0);
            const ikY = parseFloat(yInput ? yInput.value : 0.0);
            const ikZ = parseFloat(zInput ? zInput.value : 10.0);

            try {
                const ikRes = await sendArmIK(ikX, ikY, ikZ);
                if (ikRes.success) {
                    showToast(`✅ ${ikRes.message}`, 'success');
                    updateArmUI();
                } else {
                    showToast(`⚠️ IK failed: ${ikRes.message}`, 'warning');
                }
            } catch (err) {
                showToast(`IK Error: ${err.message}`, 'danger');
            }
        });
    }

    // 8-Step Pick-and-Place Trajectory Sequence Button
    const btnPickSeq = document.getElementById('btnRunPickSequence');
    if (btnPickSeq) {
        btnPickSeq.addEventListener('click', async () => {
            try {
                const seqRes = await runPickSequence();
                if (seqRes.success) {
                    showToast(`🦾 Step [${seqRes.sequence_step}]: ${seqRes.message}`, 'info');
                    updateArmUI();
                } else {
                    showToast(`⚠️ ${seqRes.message}`, 'danger');
                }
            } catch (err) {
                showToast(`Pick Sequence Error: ${err.message}`, 'danger');
            }
        });
    }
}
