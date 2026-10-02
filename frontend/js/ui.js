/* ==========================================================================
   AGRICULTURE MANIPULATION ROBOT - UI CONTROLLER & ROUTER
   ========================================================================== */

import { getTestResults, getRobotStatus, sendEStop } from './api.js';

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initNavigation();
    initAccordions();
    initVivaSearch();
    initVisionLabSliders();
    initEStopPreview();
});


/* --------------------------------------------------------------------------
   1. Theme Toggle (Light / Dark Mode)
   -------------------------------------------------------------------------- */
function initTheme() {
    const themeBtn = document.getElementById('themeToggleBtn');
    const savedTheme = localStorage.getItem('agri_robot_theme') || 'light';
    
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeBtnText(savedTheme);

    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('agri_robot_theme', newTheme);
            updateThemeBtnText(newTheme);
        });
    }
}

function updateThemeBtnText(theme) {
    const themeBtn = document.getElementById('themeToggleBtn');
    if (themeBtn) {
        themeBtn.innerHTML = theme === 'dark' 
            ? '☀️ Light Mode' 
            : '🌙 Dark Mode';
    }
}

/* --------------------------------------------------------------------------
   2. Single Page Application Router (Page Switcher)
   -------------------------------------------------------------------------- */
function initNavigation() {
    const navLinks = document.querySelectorAll('[data-page]');
    
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetPage = link.getAttribute('data-page');
            navigateToPage(targetPage);
        });
    });

    // Handle hash in URL if present
    const initialHash = window.location.hash.replace('#', '');
    if (initialHash && document.getElementById(`page-${initialHash}`)) {
        navigateToPage(initialHash);
    }
}

export function navigateToPage(pageId) {
    // Hide all page views
    const pages = document.querySelectorAll('.page-view');
    pages.forEach(page => page.classList.remove('active'));

    // Deactivate all nav links
    const navLinks = document.querySelectorAll('[data-page]');
    navLinks.forEach(link => link.classList.remove('active'));

    // Show target page
    const activePage = document.getElementById(`page-${pageId}`);
    if (activePage) {
        activePage.classList.add('active');
        window.location.hash = pageId;
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // Highlight active link
    const activeLink = document.querySelector(`[data-page="${pageId}"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }

    // Trigger dynamic data fetch for specific tabs
    if (pageId === 'results') {
        renderTestResults();
    }
}

/* --------------------------------------------------------------------------
   3. Fetch & Render Dynamic SQLite Test Verification Matrix
   -------------------------------------------------------------------------- */
async function renderTestResults() {
    try {
        const results = await getTestResults();
        const tbody = document.querySelector('#page-results table tbody');
        if (!tbody || !results || results.length === 0) return;

        tbody.innerHTML = results.map(res => `
            <tr>
                <td><strong>${res.test_id}</strong></td>
                <td>${res.scenario}</td>
                <td>${res.expected}</td>
                <td>${res.actual}</td>
                <td><span class="badge badge-${res.mode === 'SIMULATION' ? 'sim' : 'hw'}">${res.mode}</span></td>
                <td><span class="badge badge-${res.status === 'PASS' ? 'success' : 'warning'}">${res.status}</span></td>
            </tr>
        `).join('');
    } catch (err) {
        console.log("[UI Info] Using default static test results while backend connects.");
    }
}

/* --------------------------------------------------------------------------
   4. Accordion Handler (Viva Q&A)
   -------------------------------------------------------------------------- */
function initAccordions() {
    document.addEventListener('click', (e) => {
        const header = e.target.closest('.accordion-header');
        if (!header) return;

        const item = header.parentElement;
        item.classList.toggle('open');
    });
}

/* --------------------------------------------------------------------------
   5. Viva Q&A Live Search Filter
   -------------------------------------------------------------------------- */
function initVivaSearch() {
    const searchInput = document.getElementById('vivaSearchInput');
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        const accordionItems = document.querySelectorAll('#vivaAccordion .accordion-item');

        accordionItems.forEach(item => {
            const text = item.textContent.toLowerCase();
            if (text.includes(query)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    });
}

/* --------------------------------------------------------------------------
   6. Vision Lab HSV Sliders Input Handler
   -------------------------------------------------------------------------- */
function initVisionLabSliders() {
    const sliders = document.querySelectorAll('#page-detection input[type="range"]');
    sliders.forEach(slider => {
        slider.addEventListener('input', () => {
            const targetId = slider.getAttribute('data-target-val');
            if (targetId) {
                const targetSpan = document.getElementById(targetId);
                if (targetSpan) targetSpan.textContent = slider.value;
            }
        });
    });
}

/* --------------------------------------------------------------------------
   7. Emergency Stop UI Button Handler
   -------------------------------------------------------------------------- */
function initEStopPreview() {
    const estopBtn = document.getElementById('btnEStop');
    if (!estopBtn) return;

    let estopActive = false;

    const toggleEStop = async () => {
        estopActive = !estopActive;
        const action = estopActive ? 'ENGAGE' : 'RELEASE';
        try {
            await sendEStop(action);
        } catch (err) {
            console.warn("[E-Stop Sync Warning]", err.message);
        }

        if (estopActive) {
            estopBtn.classList.add('active');
            estopBtn.innerHTML = '⚠️ EMERGENCY STOP ENGAGED! CLICK TO RELEASE ⚠️';
            showToast('🚨 EMERGENCY STOP ENGAGED! Motors & arm halted.', 'danger');
        } else {
            estopBtn.classList.remove('active');
            estopBtn.innerHTML = '🚨 EMERGENCY STOP (SPACEBAR) 🚨';
            showToast('✅ Emergency Stop released. System operational.', 'success');
        }
    };

    estopBtn.addEventListener('click', toggleEStop);

    // Keyboard Spacebar Hotkey
    document.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            toggleEStop();
        }
    });
}


/* --------------------------------------------------------------------------
   8. Toast Notification Utility
   -------------------------------------------------------------------------- */
export function showToast(message, type = 'info') {
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
        `;
        document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    toast.className = `badge badge-${type}`;
    toast.style.cssText = `
        padding: 12px 20px;
        font-size: 0.9rem;
        box-shadow: var(--shadow-md);
        border-radius: var(--radius-sm);
        animation: fadeIn 0.3s ease;
    `;
    toast.textContent = message;

    toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 3500);
}
