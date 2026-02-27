/* ============================================================
   Meta Research – Main JavaScript
   Search, Bookmarks, Particles, Interactions
   ============================================================ */

// ---------------------------------------------------------------------------
// Background Particles Animation
// ---------------------------------------------------------------------------
(function initParticles() {
    const container = document.getElementById('bgParticles');
    if (!container) return;

    const PARTICLE_COUNT = 35;
    for (let i = 0; i < PARTICLE_COUNT; i++) {
        const particle = document.createElement('div');
        particle.classList.add('particle');
        const size = Math.random() * 4 + 1;
        particle.style.width = size + 'px';
        particle.style.height = size + 'px';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDuration = (Math.random() * 15 + 10) + 's';
        particle.style.animationDelay = (Math.random() * 10) + 's';

        // Vary colours between indigo and cyan
        particle.style.background = Math.random() > 0.5
            ? 'rgba(99,102,241,' + (Math.random() * 0.3 + 0.1) + ')'
            : 'rgba(6,182,212,' + (Math.random() * 0.3 + 0.1) + ')';

        container.appendChild(particle);
    }
})();

// ---------------------------------------------------------------------------
// Navbar scroll effect
// ---------------------------------------------------------------------------
(function initNavbar() {
    const navbar = document.getElementById('navbar');
    if (!navbar) return;
    window.addEventListener('scroll', () => {
        navbar.classList.toggle('scrolled', window.scrollY > 30);
    });
})();

// ---------------------------------------------------------------------------
// Search Functionality
// ---------------------------------------------------------------------------
let currentSource = 'all';

(function initSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    if (!searchInput || !searchBtn) return;

    // Trigger search on button click
    searchBtn.addEventListener('click', () => performSearch());

    // Trigger search on Enter key
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    // Source filter chips
    document.querySelectorAll('.filter-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            currentSource = chip.dataset.source;
        });
    });
})();


async function performSearch() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) return;

    const resultsSection = document.getElementById('resultsSection');
    const loadingContainer = document.getElementById('loadingContainer');
    const papersGrid = document.getElementById('papersGrid');
    const noResults = document.getElementById('noResults');
    const resultsQuery = document.getElementById('resultsQuery');
    const resultsCount = document.getElementById('resultsCount');
    const featuresSection = document.getElementById('featuresSection');

    // Show results section and loading
    resultsSection.style.display = 'block';
    loadingContainer.style.display = 'flex';
    papersGrid.style.display = 'none';
    papersGrid.innerHTML = '';
    noResults.style.display = 'none';
    resultsQuery.textContent = query;
    if (featuresSection) featuresSection.style.display = 'none';

    // Smooth scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&source=${currentSource}&max=12`);
        const data = await res.json();
        loadingContainer.style.display = 'none';

        if (!data.papers || data.papers.length === 0) {
            noResults.style.display = 'flex';
            resultsCount.textContent = '0 papers';
            return;
        }

        resultsCount.textContent = `${data.papers.length} papers`;
        papersGrid.style.display = 'grid';

        // Check bookmark status if logged in
        let bookmarkedIds = new Set();
        try {
            const meRes = await fetch('/api/me');
            const meData = await meRes.json();
            if (meData.authenticated) {
                const bRes = await fetch('/api/bookmarks');
                const bData = await bRes.json();
                bData.bookmarks.forEach(b => bookmarkedIds.add(b.paper_id));
            }
        } catch (_) { /* not logged in, ignore */ }

        papersGrid.innerHTML = data.papers.map(paper => createPaperCard(paper, bookmarkedIds.has(paper.id))).join('');

    } catch (err) {
        loadingContainer.innerHTML = '<p class="error-text">Failed to fetch results. Please try again.</p>';
        console.error('Search error:', err);
    }
}


function createPaperCard(paper, isBookmarked) {
    const pubDate = paper.published || '';
    const sourceName = paper.source_name || paper.source;
    const hasPdf = paper.pdf_url && paper.pdf_url.length > 0;
    const citations = paper.citations ? `<span class="paper-date">• ${paper.citations} citations</span>` : '';

    return `
    <article class="paper-card ${isBookmarked ? 'bookmarked' : ''}" data-paper-id="${escapeAttr(paper.id)}">
        <div class="paper-source">
            <span class="source-badge">${escapeHtml(sourceName)}</span>
            <span class="paper-date">${escapeHtml(pubDate)} ${citations}</span>
        </div>
        <h3 class="paper-title">${escapeHtml(paper.title)}</h3>
        <p class="paper-authors">${escapeHtml(paper.authors || 'Unknown authors')}</p>
        <p class="paper-summary" id="summary-${escapeAttr(paper.id)}">${escapeHtml(paper.summary)}</p>
        ${paper.full_summary && paper.full_summary.length > 500
            ? `<button class="expand-btn" onclick="toggleSummary('${escapeAttr(paper.id)}', this, '${escapeAttr(paper.full_summary)}')">Show more</button>`
            : ''}
        <div class="paper-actions">
            ${hasPdf
            ? `<a href="${paper.pdf_url}" target="_blank" rel="noopener" class="btn btn-download"><span>📥</span> Download PDF</a>`
            : '<span class="no-pdf">No PDF available</span>'}
            ${paper.abstract_url
            ? `<a href="${paper.abstract_url}" target="_blank" rel="noopener" class="btn btn-ghost" style="font-size:0.8rem;"><span>🔗</span> View Page</a>`
            : ''}
            <button class="btn btn-bookmark ${isBookmarked ? 'active' : ''}" onclick="toggleBookmark(this, ${JSON.stringify(paper).replace(/"/g, '&quot;')})" title="${isBookmarked ? 'Remove bookmark' : 'Bookmark this paper'}">
                <span>${isBookmarked ? '🔖' : '🔖'}</span> ${isBookmarked ? 'Saved' : 'Bookmark'}
            </button>
        </div>
    </article>`;
}


// ---------------------------------------------------------------------------
// Bookmark toggle
// ---------------------------------------------------------------------------
async function toggleBookmark(btn, paper) {
    // Check if logged in
    try {
        const meRes = await fetch('/api/me');
        const meData = await meRes.json();
        if (!meData.authenticated) {
            alert('Please login to bookmark papers.');
            window.location.href = '/login';
            return;
        }
    } catch (_) {
        alert('Please login to bookmark papers.');
        return;
    }

    const isActive = btn.classList.contains('active');

    if (isActive) {
        // Remove bookmark - need to find the bookmark ID
        try {
            const checkRes = await fetch(`/api/bookmarks/check/${encodeURIComponent(paper.id)}`);
            const checkData = await checkRes.json();
            if (checkData.bookmarked && checkData.bookmark_id) {
                await fetch(`/api/bookmarks/${checkData.bookmark_id}`, { method: 'DELETE' });
                btn.classList.remove('active');
                btn.innerHTML = '<span>🔖</span> Bookmark';
            }
        } catch (err) {
            console.error('Failed to remove bookmark', err);
        }
    } else {
        // Add bookmark
        try {
            const res = await fetch('/api/bookmarks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    paper_id: paper.id,
                    title: paper.title,
                    authors: paper.authors,
                    summary: paper.summary,
                    pdf_url: paper.pdf_url,
                    source: paper.source
                })
            });
            if (res.ok) {
                btn.classList.add('active');
                btn.innerHTML = '<span>🔖</span> Saved';

                // Subtle animation
                btn.style.transform = 'scale(1.1)';
                setTimeout(() => btn.style.transform = '', 200);
            }
        } catch (err) {
            console.error('Failed to add bookmark', err);
        }
    }
}


// ---------------------------------------------------------------------------
// Expand / collapse summary
// ---------------------------------------------------------------------------
function toggleSummary(paperId, btn, fullSummary) {
    const summaryEl = document.getElementById('summary-' + paperId);
    if (!summaryEl) return;

    if (summaryEl.classList.contains('expanded')) {
        summaryEl.classList.remove('expanded');
        summaryEl.textContent = fullSummary.substring(0, 500) + '...';
        btn.textContent = 'Show more';
    } else {
        summaryEl.classList.add('expanded');
        summaryEl.textContent = fullSummary;
        btn.textContent = 'Show less';
    }
}


// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeAttr(text) {
    if (!text) return '';
    return text.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}


// ---------------------------------------------------------------------------
// Auto-dismiss flash messages
// ---------------------------------------------------------------------------
(function initFlash() {
    document.querySelectorAll('.flash-msg').forEach(msg => {
        setTimeout(() => {
            msg.style.animation = 'fadeOut 0.3s ease forwards';
            setTimeout(() => msg.remove(), 300);
        }, 5000);
    });
})();
