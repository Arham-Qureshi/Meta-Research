/* ============================================================
   Dynamic Typing Placeholder
   Cycles through example prompts with a typewriter effect
   to guide new users on what to search for.
   ============================================================ */

(function initDynamicPlaceholder() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;

    // --- Configuration ---
    const PROMPTS = [
        'Search for "deep learning"...',
        'Try "quantum computing papers"...',
        'Explore "transformer architectures"...',
        'Discover "reinforcement learning"...',
        'Look up "natural language processing"...',
        'Find "computer vision YOLO"...',
        'Search "generative adversarial networks"...',
        'Try "large language models GPT"...',
    ];

    const TYPE_SPEED = 65;   // ms per character typed
    const DELETE_SPEED = 35;   // ms per character deleted
    const PAUSE_AFTER = 2000; // ms to pause after full prompt typed
    const PAUSE_BEFORE = 400;  // ms to pause before typing a new prompt

    // --- Build the overlay element ---
    const searchBox = searchInput.closest('.search-box');
    if (!searchBox) return;

    // Make search-box position relative so we can overlay
    searchBox.style.position = 'relative';

    const overlay = document.createElement('div');
    overlay.className = 'dynamic-placeholder';
    overlay.innerHTML = '<span class="dynamic-placeholder-text"></span><span class="dynamic-placeholder-cursor"></span>';
    searchBox.appendChild(overlay);

    const textEl = overlay.querySelector('.dynamic-placeholder-text');

    // Mark input so CSS can hide stock placeholder
    searchInput.classList.add('has-dynamic-placeholder');

    // --- State ---
    let currentPrompt = 0;
    let charIndex = 0;
    let isDeleting = false;
    let timer = null;
    let isRunning = true;

    // --- Core loop ---
    function tick() {
        if (!isRunning) return;

        const prompt = PROMPTS[currentPrompt];

        if (!isDeleting) {
            // Typing forward
            charIndex++;
            textEl.textContent = prompt.substring(0, charIndex);

            if (charIndex >= prompt.length) {
                // Finished typing – pause then start deleting
                timer = setTimeout(() => {
                    isDeleting = true;
                    tick();
                }, PAUSE_AFTER);
                return;
            }
            timer = setTimeout(tick, TYPE_SPEED);
        } else {
            // Deleting backward
            charIndex--;
            textEl.textContent = prompt.substring(0, charIndex);

            if (charIndex <= 0) {
                // Finished deleting – move to next prompt
                isDeleting = false;
                currentPrompt = (currentPrompt + 1) % PROMPTS.length;
                timer = setTimeout(tick, PAUSE_BEFORE);
                return;
            }
            timer = setTimeout(tick, DELETE_SPEED);
        }
    }

    function stopAnimation() {
        isRunning = false;
        if (timer) clearTimeout(timer);
        overlay.classList.add('hidden');
    }

    function startAnimation() {
        if (searchInput.value.length > 0) return; // Don't restart if there's text
        isRunning = true;
        overlay.classList.remove('hidden');
        // Reset to beginning of current prompt
        charIndex = 0;
        textEl.textContent = '';
        tick();
    }

    // --- Events ---
    searchInput.addEventListener('focus', () => {
        stopAnimation();
    });

    searchInput.addEventListener('blur', () => {
        if (searchInput.value.trim() === '') {
            startAnimation();
        }
    });

    searchInput.addEventListener('input', () => {
        if (searchInput.value.length > 0) {
            stopAnimation();
        } else {
            startAnimation();
        }
    });

    // --- Start ---
    tick();
})();
