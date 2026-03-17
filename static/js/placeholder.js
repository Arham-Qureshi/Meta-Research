
(function initDynamicPlaceholder() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;
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
    const TYPE_SPEED = 65;
    const DELETE_SPEED = 35;
    const PAUSE_AFTER = 2000;
    const PAUSE_BEFORE = 400;
    const searchBox = searchInput.closest('.search-box');
    if (!searchBox) return;
    searchBox.style.position = 'relative';
    const overlay = document.createElement('div');
    overlay.className = 'dynamic-placeholder';
    overlay.innerHTML = '<span class="dynamic-placeholder-text"></span><span class="dynamic-placeholder-cursor"></span>';
    searchBox.appendChild(overlay);
    const textEl = overlay.querySelector('.dynamic-placeholder-text');
    searchInput.classList.add('has-dynamic-placeholder');
    let currentPrompt = 0;
    let charIndex = 0;
    let isDeleting = false;
    let timer = null;
    let isRunning = true;
    function tick() {
        if (!isRunning) return;
        const prompt = PROMPTS[currentPrompt];
        if (!isDeleting) {
            charIndex++;
            textEl.textContent = prompt.substring(0, charIndex);
            if (charIndex >= prompt.length) {
                timer = setTimeout(() => {
                    isDeleting = true;
                    tick();
                }, PAUSE_AFTER);
                return;
            }
            timer = setTimeout(tick, TYPE_SPEED);
        } else {
            charIndex--;
            textEl.textContent = prompt.substring(0, charIndex);
            if (charIndex <= 0) {
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
        if (searchInput.value.length > 0) return;
        isRunning = true;
        overlay.classList.remove('hidden');
        charIndex = 0;
        textEl.textContent = '';
        tick();
    }
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
    tick();
})();
