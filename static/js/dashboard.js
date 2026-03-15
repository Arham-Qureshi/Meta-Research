/* ============================================================
   Dashboard — Stats, Activity Feed, Clear History
   ============================================================ */
(function () {
    document.addEventListener('DOMContentLoaded', init);

    async function init() {
        await Promise.all([loadStats(), loadActivity()]);
        bindEvents();
    }

    // ── Stats ────────────────────────────────────────────────
    async function loadStats() {
        try {
            const res = await fetch('/api/dashboard/stats');
            const data = await res.json();
            document.getElementById('statBookmarks').textContent = data.total_bookmarks;
            document.getElementById('statCollections').textContent = data.total_collections;
            document.getElementById('statSearches').textContent = data.total_searches;
            document.getElementById('statViews').textContent = data.total_views;
        } catch (err) {
            console.error('Failed to load dashboard stats', err);
        }
    }

    // ── Activity ─────────────────────────────────────────────
    async function loadActivity() {
        try {
            const res = await fetch('/api/dashboard/activity');
            const data = await res.json();
            renderSearches(data.searches || []);
            renderViews(data.views || []);
        } catch (err) {
            console.error('Failed to load activity', err);
        }
    }

    function renderSearches(searches) {
        const list = document.getElementById('searchesList');
        if (searches.length === 0) {
            list.innerHTML = '<div class="activity-empty">No searches yet. Go discover!</div>';
            return;
        }
        list.innerHTML = searches.map(s => {
            const time = timeAgo(s.searched_at);
            return `
                <a href="/?q=${encodeURIComponent(s.query)}" class="activity-item" onclick="reSearch(event, '${escapeAttr(s.query)}')">
                    <div class="activity-icon activity-icon-search">🔍</div>
                    <div class="activity-info">
                        <div class="activity-title">${escapeHtml(s.query)}</div>
                        <div class="activity-meta">${time} · ${s.result_count} results · ${s.source}</div>
                    </div>
                    <span class="activity-badge">${s.result_count}</span>
                </a>`;
        }).join('');
    }

    function renderViews(views) {
        const list = document.getElementById('viewsList');
        if (views.length === 0) {
            list.innerHTML = '<div class="activity-empty">No papers viewed yet.</div>';
            return;
        }
        list.innerHTML = views.map(v => {
            const time = timeAgo(v.viewed_at);
            const displayTitle = v.title.length > 60 ? v.title.substring(0, 60) + '...' : v.title;
            return `
                <a href="/paper/${encodeURIComponent(v.paper_id)}" class="activity-item">
                    <div class="activity-icon activity-icon-view">📄</div>
                    <div class="activity-info">
                        <div class="activity-title">${escapeHtml(displayTitle)}</div>
                        <div class="activity-meta">${time}</div>
                    </div>
                </a>`;
        }).join('');
    }

    // ── Events ───────────────────────────────────────────────
    function bindEvents() {
        document.getElementById('clearHistoryBtn').addEventListener('click', async () => {
            if (!confirm('Clear all search history?')) return;
            await fetch('/api/dashboard/history', { method: 'DELETE' });
            document.getElementById('searchesList').innerHTML =
                '<div class="activity-empty">Search history cleared.</div>';
            document.getElementById('statSearches').textContent = '0';
        });
    }

    // ── Re-search from history ───────────────────────────────
    window.reSearch = function (e, query) {
        e.preventDefault();
        window.location.href = '/';
        // Store query in sessionStorage so homepage can pick it up
        sessionStorage.setItem('reSearchQuery', query);
    };

    // ── Helpers ──────────────────────────────────────────────
    function timeAgo(isoString) {
        const diff = Date.now() - new Date(isoString).getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 1) return 'Just now';
        if (mins < 60) return `${mins}m ago`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs}h ago`;
        const days = Math.floor(hrs / 24);
        return `${days}d ago`;
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function escapeAttr(text) {
        if (!text) return '';
        return text.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }
})();
