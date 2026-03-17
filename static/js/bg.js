(function initGridBackground() {
    const canvas = document.getElementById('bgCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d', { alpha: false });

    let W, H;
    let time = 0;

    let mouse = { x: -1000, y: -1000, targetX: -1000, targetY: -1000 };
    window.addEventListener('mousemove', (e) => {
        mouse.targetX = e.clientX;
        mouse.targetY = e.clientY;
    });

    function resize() {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
        if (mouse.x === -1000) {
            mouse.x = mouse.targetX = W / 2;
            mouse.y = mouse.targetY = H / 2;
        }
    }
    window.addEventListener('resize', resize);
    resize();

    const gridSizeX = 60;
    const gridSizeY = 60;
    const speedX = 10;
    const speedY = 15;
    const cards = [
        {
            x: 0.08, y: 0.15,
            size: 110,
            rotX: Math.PI / 6,
            rotY: Math.PI / 4,
            rotZ: Math.PI / 12,
            speedX: 0.005,
            speedY: 0.003,
            speedZ: 0.002,
            depth: 0.6
        },
        {
            x: 0.92, y: 0.85,
            size: 140,
            rotX: -Math.PI / 5,
            rotY: -Math.PI / 4,
            rotZ: -Math.PI / 8,
            speedX: -0.004,
            speedY: -0.006,
            speedZ: 0.003,
            depth: 0.9
        },
        {
            x: 0.9, y: 0.2,
            size: 90,
            rotX: Math.PI / 8,
            rotY: -Math.PI / 3,
            rotZ: Math.PI / 16,
            speedX: 0.006,
            speedY: -0.002,
            speedZ: -0.004,
            depth: 0.4
        }
    ];

    function drawCard(card, mouseOffsetX, mouseOffsetY) {
        ctx.save();
        const px = (card.x * W) + (mouseOffsetX * card.depth * -0.05);
        const py = (card.y * H) + (mouseOffsetY * card.depth * -0.05);

        ctx.translate(px, py);
        ctx.rotate(card.rotZ);
        ctx.scale(Math.cos(card.rotY), Math.cos(card.rotX));

        const s = card.size;
        const radius = 12;

        ctx.beginPath();
        if (ctx.roundRect) {
            ctx.roundRect(-s / 2, -s / 2, s, s, radius);
        } else {
            ctx.rect(-s / 2, -s / 2, s, s);
        }
        ctx.fillStyle = 'rgba(255, 255, 255, 0.015)';
        ctx.fill();
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = 'rgba(226, 179, 115, 0.4)';
        ctx.shadowColor = 'rgba(226, 179, 115, 0.6)';
        ctx.shadowBlur = 10;
        ctx.stroke();
        ctx.shadowBlur = 0;
        ctx.clip();
        ctx.beginPath();
        ctx.moveTo(-s, -s);
        ctx.lineTo(s, s);
        ctx.lineTo(s, s - Math.max(30, s * 0.3));
        ctx.lineTo(-s, -s - Math.max(30, s * 0.3));
        ctx.fillStyle = 'rgba(255, 255, 255, 0.04)';
        ctx.fill();
        ctx.restore();
    }

    function draw() {
        ctx.fillStyle = '#121212';
        ctx.fillRect(0, 0, W, H);
        time += 0.016;
        mouse.x += (mouse.targetX - mouse.x) * 0.08;
        mouse.y += (mouse.targetY - mouse.y) * 0.08;
        const offsetX = (time * speedX) % gridSizeX;
        const offsetY = (time * speedY) % gridSizeY;
        ctx.save();
        ctx.lineWidth = 1;
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
        ctx.beginPath();
        for (let x = -gridSizeX + offsetX; x < W + gridSizeX; x += gridSizeX) {
            ctx.moveTo(x, 0);
            ctx.lineTo(x, H);
        }
        for (let y = -gridSizeY + offsetY; y < H + gridSizeY; y += gridSizeY) {
            ctx.moveTo(0, y);
            ctx.lineTo(W, y);
        }
        ctx.stroke();
        ctx.restore();
        const mouseOffsetX = mouse.x - W / 2;
        const mouseOffsetY = mouse.y - H / 2;
        cards.forEach((card) => {
            card.rotX += card.speedX;
            card.rotY += card.speedY;
            card.rotZ += card.speedZ;
            drawCard(card, mouseOffsetX, mouseOffsetY);
        });
        requestAnimationFrame(draw);
    }
    requestAnimationFrame(draw);
})();
