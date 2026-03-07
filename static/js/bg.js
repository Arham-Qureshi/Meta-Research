/* ============================================================
   Meta Research – Premium Vantablack Background
   Deep space nothingness with a massive, subtle celestial transition
   ============================================================ */

(function initVantablackBackground() {
    const canvas = document.getElementById('bgCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let W, H;

    /* ── Resize ──────────────────────────────────────────────── */
    function resize() {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }

    window.addEventListener('resize', resize);
    resize();

    /* ── Draw loop ──────────────────────────────────────────── */
    function draw(t) {
        // Absolute Vantablack
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, W, H);

        const time = t * 0.0001; // Extremely slow time progression

        // Massive celestial body (Eclipse/Event Horizon concept)
        // Positioned slightly off-center
        const cx = W * 0.6;
        const cy = H * 0.4;

        // Scale relative to screen size to remain imposing
        const baseRadius = Math.max(W, H) * 0.45;

        // Draw the subtle, breathing corona/halo behind the black body
        // It pulses slightly and rotates its gradient slowly
        const pulse = Math.sin(time) * 0.05 + 1;
        const outerRadius = baseRadius * 1.5 * pulse;

        // Create a rotating gradient for the corona
        const rotX = cx + Math.cos(time * 0.5) * (baseRadius * 0.2);
        const rotY = cy + Math.sin(time * 0.5) * (baseRadius * 0.2);

        const coronaGrad = ctx.createRadialGradient(rotX, rotY, baseRadius * 0.8, cx, cy, outerRadius);

        // Deep, subtle colors for a premium, non-distracting feel
        coronaGrad.addColorStop(0, 'rgba(40, 45, 80, 0.4)');     // Deep indigo edge
        coronaGrad.addColorStop(0.3, 'rgba(20, 25, 60, 0.15)');   // Fading violet
        coronaGrad.addColorStop(0.7, 'rgba(10, 15, 30, 0.05)');     // Almost black
        coronaGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');           // Fade to vantablack

        ctx.beginPath();
        ctx.arc(cx, cy, outerRadius, 0, Math.PI * 2);
        ctx.fillStyle = coronaGrad;
        ctx.fill();

        // Draw the absolute black silhouette (the "planet / singularity")
        ctx.beginPath();
        ctx.arc(cx, cy, baseRadius, 0, Math.PI * 2);
        ctx.fillStyle = '#000000';

        // A tiny inner shadow to give it boundary against the corona
        ctx.shadowColor = 'rgba(0,0,0,1)';
        ctx.shadowBlur = 50;
        ctx.fill();
        ctx.shadowBlur = 0; // reset

        // Optional: Very sparse, impossibly distant static stars 
        // that gently twinkle to establish scale
        Math.seedrandom ? Math.seedrandom('meta') : null; // consistent stars if seed math exists, else random per frame which flickers. 
        // We'll calculate deterministic pseudo-random stars based on index.
        for (let i = 0; i < 30; i++) {
            const sx = (Math.sin(i * 123.45) * 0.5 + 0.5) * W;
            const sy = (Math.cos(i * 321.54) * 0.5 + 0.5) * H;

            // Skip stars inside the black body
            const dist = Math.sqrt((sx - cx) ** 2 + (sy - cy) ** 2);
            if (dist < baseRadius) continue;

            const twinkle = Math.sin(time * 5 + i) * 0.5 + 0.5;
            const alpha = 0.05 + twinkle * 0.15; // Extremely faint

            ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
            ctx.beginPath();
            ctx.arc(sx, sy, 0.5, 0, Math.PI * 2);
            ctx.fill();
        }

        requestAnimationFrame(draw);
    }

    requestAnimationFrame(draw);
})();
