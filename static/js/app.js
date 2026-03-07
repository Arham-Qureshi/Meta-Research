/* ============================================================
   Meta Research – Main JavaScript
   Search · Bookmarks · Keyboard Shortcuts · Enhanced Cards
   Real-Time Sync Filtering
   ============================================================ */

// ---------------------------------------------------------------------------
// Global State
// ---------------------------------------------------------------------------
let currentSource = 'all';
let currentType = 'all';
let currentDomain = 'all';
let currentFetchedPapers = [];
let currentBookmarkedIds = new Set();

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
// Keyboard Shortcuts:  Ctrl+K → focus search,  / → open filters (focus first)
// ---------------------------------------------------------------------------
(function initKeyboardShortcuts() {
    const input = document.getElementById('searchInput');
    if (!input) return;

    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            input.focus();
            input.select();
        }
        if (e.key === 'Escape' && document.activeElement === input) {
            input.blur();
        }
    });
})();

// ---------------------------------------------------------------------------
// Sidebar & Filtering Setup (Real-Time)
// ---------------------------------------------------------------------------
function attachRealTimeListeners() {
    // Content-type tabs
    document.querySelectorAll('.type-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.type-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentType = tab.dataset.type;
            renderPapers();
        });
    });

    // Source filter chips
    document.querySelectorAll('.source-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            document.querySelectorAll('.source-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            currentSource = chip.dataset.source;
            renderPapers();
        });
    });

    // Advanced Checkboxes
    ['filterPeerReviewed', 'filterOpenAccess', 'filterHasCode'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', renderPapers);
    });

    // Domain list
    document.querySelectorAll('.domain-item').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('.domain-item').forEach(d => d.classList.remove('active'));
            item.classList.add('active');
            currentDomain = item.dataset.domain;
            renderPapers();
        });
    });

    // Year slider
    const fromSlider = document.getElementById('yearSliderFrom');
    const toSlider = document.getElementById('yearSliderTo');

    function updateYearLabels() {
        let from = parseInt(fromSlider.value);
        let to = parseInt(toSlider.value);
        if (from > to) { fromSlider.value = to; from = to; }
        document.getElementById('yearFrom').textContent = from;
        document.getElementById('yearTo').textContent = to;

        const min = fromSlider.min;
        const max = fromSlider.max;
        const pctL = ((from - min) / (max - min)) * 100;
        const pctR = ((to - min) / (max - min)) * 100;
        fromSlider.style.setProperty('--thumb-pct', pctL + '%');
        toSlider.style.setProperty('--track-fill-left', pctL + '%');
        toSlider.style.setProperty('--track-fill-right', (100 - pctR) + '%');
    }

    if (fromSlider && toSlider) {
        fromSlider.addEventListener('input', () => { updateYearLabels(); renderPapers(); });
        toSlider.addEventListener('input', () => { updateYearLabels(); renderPapers(); });
        updateYearLabels();
    }
}
attachRealTimeListeners();


// ---------------------------------------------------------------------------
// Search init & Perform
// ---------------------------------------------------------------------------
(function initSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    if (!searchInput || !searchBtn) return;

    searchBtn.addEventListener('click', () => performSearch());
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') performSearch();
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
    const featuresSection = document.getElementById('featuresSection');

    // UI transitions
    resultsSection.classList.add('active');
    loadingContainer.classList.add('active');
    papersGrid.classList.remove('active');
    papersGrid.innerHTML = '';
    noResults.classList.remove('active');
    resultsQuery.textContent = query;
    if (featuresSection) featuresSection.classList.add('hidden');

    // Scroll main results area, not window
    const resultsMain = document.querySelector('.results-main');
    if (resultsMain) resultsMain.scrollTop = 0;

    try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&source=all&max=20`);
        const data = await res.json();
        loadingContainer.classList.remove('active');

        if (!data.papers || data.papers.length === 0) {
            noResults.classList.add('active');
            document.getElementById('resultsCount').textContent = '0 papers found';
            return;
        }

        currentFetchedPapers = data.papers;

        // Check bookmarks
        try {
            const meRes = await fetch('/api/me');
            const meData = await meRes.json();
            if (meData.authenticated) {
                const bRes = await fetch('/api/bookmarks');
                const bData = await bRes.json();
                bData.bookmarks.forEach(b => currentBookmarkedIds.add(b.paper_id));
            }
        } catch (_) { /* not logged in */ }

        renderPapers(); // Renders dynamically based on active filters

    } catch (err) {
        loadingContainer.classList.remove('active');
        loadingContainer.innerHTML = '<p class="error-text">Failed to fetch results. Please try again.</p>';
        console.error('Search error:', err);
    }
}

// ---------------------------------------------------------------------------
// Real-Time Render Papers
// ---------------------------------------------------------------------------
function renderPapers() {
    const papersGrid = document.getElementById('papersGrid');
    const noResults = document.getElementById('noResults');
    const resultsCount = document.getElementById('resultsCount');
    if (!papersGrid || currentFetchedPapers.length === 0) return;

    const peerReq = document.getElementById('filterPeerReviewed')?.checked;
    const oaReq = document.getElementById('filterOpenAccess')?.checked;
    const codeReq = document.getElementById('filterHasCode')?.checked;

    const yearFrom = parseInt(document.getElementById('yearSliderFrom')?.value || '2000');
    const yearTo = parseInt(document.getElementById('yearSliderTo')?.value || '2025');

    const filtered = currentFetchedPapers.filter(p => {
        // 1. Source check
        if (currentSource !== 'all') {
            const src = (p.source || '').toLowerCase().replace(/[^a-z]/g, '');
            const target = currentSource.toLowerCase().replace(/[^a-z]/g, '');
            if (src !== target && !(target === 'semanticscholar' && src.includes('semantic'))) return false;
        }

        // 2. Type Check (loose mock logic)
        if (currentType === 'code' && !p.abstract_url) return false;
        if (currentType === 'datasets' && !p.pdf_url) return false; // mock

        // 3. Checkboxes
        if (oaReq && (!p.pdf_url || p.pdf_url.length === 0)) return false;
        // Peer reviewed and Has code are often missing in basic search APIs, so we simulate strict checks if required
        if (codeReq && !p.abstract_url) return false;

        // 4. Domain check (mock, since we just have title/summary)
        if (currentDomain !== 'all') {
            const text = (p.title + ' ' + (p.summary || '')).toLowerCase();
            const words = currentDomain.replace('-', ' ');
            if (!text.includes(words)) return false; // basic keyword match
        }

        // 5. Year check
        let py = parseInt((p.published || '').substring(0, 4));
        if (isNaN(py)) py = yearFrom; // If unknown date, let it pass or fail? let it pass.
        if (py > 0 && (py < yearFrom || py > yearTo)) return false;

        return true;
    });

    if (filtered.length === 0) {
        papersGrid.classList.remove('active');
        noResults.classList.add('active');
        resultsCount.textContent = '0 papers match filters';
    } else {
        noResults.classList.remove('active');
        papersGrid.classList.add('active');
        resultsCount.textContent = `${filtered.length} papers found`;
        papersGrid.innerHTML = filtered
            .map(paper => createPaperCard(paper, currentBookmarkedIds.has(paper.id)))
            .join('');
    }
}

// ---------------------------------------------------------------------------
// Create Paper Card — enhanced with tags, citation count, action buttons
// ---------------------------------------------------------------------------
function createPaperCard(paper, isBookmarked) {
    const pubDate = paper.published || '';
    const sourceName = paper.source_name || paper.source || '';
    const hasPdf = paper.pdf_url && paper.pdf_url.length > 0;
    const hasAbstract = paper.abstract_url && paper.abstract_url.length > 0;

    const rawTags = paper.keywords || [];
    const tags = rawTags.slice(0, 4)
        .map(t => `<span class="paper-tag">${escapeHtml(t)}</span>`).join('');

    const citations = paper.citations
        ? `<span class="citations-badge">
               <svg class="citations-icon" viewBox="0 0 20 20" fill="currentColor">
                   <path d="M15 9H9m6 4H9m2-8H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/>
               </svg>
               ${Number(paper.citations).toLocaleString()} Citations
           </span>`
        : '';

    const sourceClass = `source-badge source-${(paper.source || 'default').toLowerCase().replace(/[^a-z]/g, '')}`;

    return `
    <article class="paper-card${isBookmarked ? ' bookmarked' : ''}" data-paper-id="${escapeAttr(paper.id)}">
        <div class="paper-top-row">
            <div class="paper-source-meta">
                <span class="${sourceClass}">${escapeHtml(sourceName)}</span>
                <span class="paper-date">${escapeHtml(pubDate)}</span>
            </div>
            <div class="paper-quick-actions">
                <button class="icon-btn bookmark-icon-btn ${isBookmarked ? 'active' : ''}"
                    onclick="toggleBookmark(this, ${JSON.stringify(paper).replace(/"/g, '&quot;')})"
                    title="${isBookmarked ? 'Remove bookmark' : 'Bookmark this paper'}">
                    <svg viewBox="0 0 24 24" fill="${isBookmarked ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
                        <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/>
                    </svg>
                </button>
            </div>
        </div>

        <h3 class="paper-title">${escapeHtml(paper.title)}</h3>
        <p class="paper-authors">${escapeHtml(paper.authors || 'Unknown authors')}</p>

        <p class="paper-summary" id="summary-${escapeAttr(paper.id)}">${escapeHtml(paper.summary)}</p>
        ${paper.full_summary && paper.full_summary.length > 500
            ? `<button class="expand-btn" onclick="toggleSummary('${escapeAttr(paper.id)}', this, '${escapeAttr(paper.full_summary)}')">Show more ↓</button>`
            : ''}

        ${tags ? `<div class="paper-tags">${tags}</div>` : ''}

        <div class="paper-footer">
            <div class="paper-actions">
                <a href="/paper/${encodeURIComponent(paper.id)}" class="btn btn-ai-summary">
                    <svg class="btn-icon" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M9.504 1.132a1 1 0 01.992 0l1.75 1a1 1 0 11-.992 1.736L10 3.152l-1.254.716a1 1 0 11-.992-1.736l1.75-1zM5.618 4.504a1 1 0 01-.372 1.364L5.016 6l.23.132a1 1 0 11-.992 1.736L4 7.723V8a1 1 0 01-2 0V6a.996.996 0 01.52-.878l1.734-.99a1 1 0 011.364.372zm8.764 0a1 1 0 011.364-.372l1.733.99A1.002 1.002 0 0118 6v2a1 1 0 11-2 0v-.277l-.254.145a1 1 0 11-.992-1.736l.23-.132-.23-.132a1 1 0 01-.372-1.364zm-7 4a1 1 0 011.364-.372L10 8.848l1.254-.716a1 1 0 11.992 1.736L11 10.58V12a1 1 0 11-2 0v-1.42l-1.246-.712a1 1 0 01-.372-1.364zM3 11a1 1 0 011 1v1.42l1.246.712a1 1 0 11-.992 1.736l-1.75-1A1 1 0 012 14v-2a1 1 0 011-1zm14 0a1 1 0 011 1v2a1 1 0 01-.504.868l-1.75 1a1 1 0 11-.992-1.736L16 13.42V12a1 1 0 011-1zm-9.618 5.504a1 1 0 011.364-.372l.254.145V16a1 1 0 112 0v.277l.254-.145a1 1 0 11.992 1.736l-1.735.992a.995.995 0 01-.992 0l-1.735-.992a1 1 0 01-.372-1.364z"/>
                    </svg>
                    AI Summary
                </a>
                ${hasPdf
            ? `<a href="${paper.pdf_url}" target="_blank" rel="noopener" class="btn btn-pdf">
                            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                                <polyline points="14,2 14,8 20,8"/>
                                <line x1="16" y1="13" x2="8" y2="13"/>
                                <line x1="16" y1="17" x2="8" y2="17"/>
                                <polyline points="10,9 9,9 8,9"/>
                            </svg>
                            PDF
                       </a>`
            : ''}
                ${hasAbstract
            ? `<a href="${paper.abstract_url}" target="_blank" rel="noopener" class="btn btn-ghost btn-sm">
                            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/>
                                <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
                            </svg>
                            View
                       </a>`
            : ''}
            </div>
            ${citations}
        </div>
    </article>`;
}

// ---------------------------------------------------------------------------
// Bookmark toggle
// ---------------------------------------------------------------------------
async function toggleBookmark(btn, paper) {
    // ... [Same logic as before]
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
        try {
            const checkRes = await fetch(`/api/bookmarks/check/${encodeURIComponent(paper.id)}`);
            const checkData = await checkRes.json();
            if (checkData.bookmarked && checkData.bookmark_id) {
                await fetch(`/api/bookmarks/${checkData.bookmark_id}`, { method: 'DELETE' });
                btn.classList.remove('active');
                btn.querySelector('svg').setAttribute('fill', 'none');
                currentBookmarkedIds.delete(paper.id);
            }
        } catch (err) {
            console.error('Failed to remove bookmark', err);
        }
    } else {
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
                btn.querySelector('svg').setAttribute('fill', 'currentColor');
                btn.animate([
                    { transform: 'scale(1)' },
                    { transform: 'scale(1.3)' },
                    { transform: 'scale(1)' }
                ], { duration: 300, easing: 'cubic-bezier(0.34,1.56,0.64,1)' });
                currentBookmarkedIds.add(paper.id);
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
        btn.textContent = 'Show more ↓';
    } else {
        summaryEl.classList.add('expanded');
        summaryEl.textContent = fullSummary;
        btn.textContent = 'Show less ↑';
    }
}

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

(function initFlash() {
    document.querySelectorAll('.flash-msg').forEach(msg => {
        setTimeout(() => {
            msg.classList.add('fade-out');
            setTimeout(() => msg.remove(), 300);
        }, 5000);
    });
})();
