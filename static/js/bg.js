
(function initVantablackBackground() {
    const canvas = document.getElementById('bgCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let W, H;
    function resize() {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }
    window.addEventListener('resize', resize);
    resize();
    function draw(t) {
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, W, H);
        const time = t * 0.0001;
        const cx = W * 0.6;
        const cy = H * 0.4;
        const baseRadius = Math.max(W, H) * 0.45;
        const pulse = Math.sin(time) * 0.05 + 1;
        const outerRadius = baseRadius * 1.5 * pulse;
        const rotX = cx + Math.cos(time * 0.5) * (baseRadius * 0.2);
        const rotY = cy + Math.sin(time * 0.5) * (baseRadius * 0.2);
        const coronaGrad = ctx.createRadialGradient(rotX, rotY, baseRadius * 0.8, cx, cy, outerRadius);
        coronaGrad.addColorStop(0, 'rgba(40, 45, 80, 0.4)');
        coronaGrad.addColorStop(0.3, 'rgba(20, 25, 60, 0.15)');
        coronaGrad.addColorStop(0.7, 'rgba(10, 15, 30, 0.05)');
        coronaGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.beginPath();
        ctx.arc(cx, cy, outerRadius, 0, Math.PI * 2);
        ctx.fillStyle = coronaGrad;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(cx, cy, baseRadius, 0, Math.PI * 2);
        ctx.fillStyle = '#000000';
        ctx.shadowColor = 'rgba(0,0,0,1)';
        ctx.shadowBlur = 50;
        ctx.fill();
        ctx.shadowBlur = 0;
        Math.seedrandom ? Math.seedrandom('meta') : null;
        for (let i = 0; i < 30; i++) {
            const sx = (Math.sin(i * 123.45) * 0.5 + 0.5) * W;
            const sy = (Math.cos(i * 321.54) * 0.5 + 0.5) * H;
            const dist = Math.sqrt((sx - cx) ** 2 + (sy - cy) ** 2);
            if (dist < baseRadius) continue;
            const twinkle = Math.sin(time * 5 + i) * 0.5 + 0.5;
            const alpha = 0.05 + twinkle * 0.15;
            ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
            ctx.beginPath();
            ctx.arc(sx, sy, 0.5, 0, Math.PI * 2);
            ctx.fill();
        }
        requestAnimationFrame(draw);
    }
    requestAnimationFrame(draw);
})();
