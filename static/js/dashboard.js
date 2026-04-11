
(function () {
    const POLL_INTERVAL = 15_000;
    let pollTimer = null;
    document.addEventListener('DOMContentLoaded', init);
    async function init() {
        await refreshAll();
        startPolling();
        bindEvents();
    }
    function startPolling() {
        pollTimer = setInterval(refreshAll, POLL_INTERVAL);
        const indicator = document.getElementById('liveIndicator');
        if (indicator) indicator.classList.add('visible');
    }
    async function refreshAll() {
        await Promise.all([loadStats(), loadChart(), loadActivity()]);
    }
    async function loadStats() {
        try {
            const res = await fetch('/api/dashboard/stats');
            const raw = await res.json();
            const d = raw.data || raw;
            animateStat('statBookmarks', d.total_bookmarks);
            animateStat('statCollections', d.total_collections);
            animateStat('statSearches', d.total_searches);
            animateStat('statViews', d.total_views);
            renderTopics(d.topics || []);
        } catch (err) {
            console.error('Failed to load stats', err);
        }
    }
    function animateStat(id, newValue) {
        const el = document.getElementById(id);
        if (!el) return;
        const oldValue = el.textContent;
        el.textContent = newValue;
        if (oldValue !== String(newValue) && oldValue !== '–') {
            el.classList.add('updated');
            setTimeout(() => el.classList.remove('updated'), 450);
        }
    }
    async function loadChart() {
        try {
            const res = await fetch('/api/dashboard/chart');
            const raw = await res.json();
            const d = raw.data || raw;
            renderChart(d.days || []);
        } catch (err) {
            console.error('Failed to load chart', err);
        }
    }
    function renderChart(days) {
        const barsContainer = document.getElementById('chartBars');
        const labelsContainer = document.getElementById('chartLabels');
        const totalEl = document.getElementById('chartTotal');
        if (!barsContainer || !days.length) return;
        const maxVal = Math.max(1, ...days.map(d => Math.max(d.searches, d.views)));
        let totalActivity = 0;
        barsContainer.innerHTML = days.map(d => {
            const sPct = (d.searches / maxVal) * 100;
            const vPct = (d.views / maxVal) * 100;
            totalActivity += d.searches + d.views;
            return `
                <div class="chart-bar-group">
                    <div class="chart-bar chart-bar-search" style="height: ${sPct}%">
                        <span class="chart-bar-tooltip">${d.searches} searches</span>
                    </div>
                    <div class="chart-bar chart-bar-view" style="height: ${vPct}%">
                        <span class="chart-bar-tooltip">${d.views} views</span>
                    </div>
                </div>`;
        }).join('');
        labelsContainer.innerHTML = days.map(d =>
            `<span class="chart-label">${d.label}</span>`
        ).join('');
        if (totalEl) totalEl.textContent = `${totalActivity} total`;
    }
    function renderTopics(topics) {
        const grid = document.getElementById('topicsGrid');
        if (!grid) return;
        if (topics.length === 0) {
            grid.innerHTML = '<div class="activity-empty">Search for papers to see your top topics.</div>';
            return;
        }
        const maxCount = topics[0]?.count || 1;
        grid.innerHTML = topics.map((t, i) => {
            const pct = Math.round((t.count / maxCount) * 100);
            const rankClass = i === 0 ? 'topic-rank-1' : i === 1 ? 'topic-rank-2' : i === 2 ? 'topic-rank-3' : 'topic-rank-default';
            return `
                <a href="/?q=${encodeURIComponent(t.query)}" class="topic-card" onclick="reSearch(event, '${escapeAttr(t.query)}')">
                    <div class="topic-rank ${rankClass}">${i + 1}</div>
                    <div class="topic-info">
                        <div class="topic-name">${escapeHtml(t.query)}</div>
                        <div class="topic-count">${t.count} ${t.count === 1 ? 'search' : 'searches'}</div>
                    </div>
                    <div class="topic-bar-track">
                        <div class="topic-bar-fill" style="width: ${pct}%"></div>
                    </div>
                </a>`;
        }).join('');
    }
    async function loadActivity() {
        try {
            const res = await fetch('/api/dashboard/activity');
            const raw = await res.json();
            const d = raw.data || raw;
            renderSearches(d.searches || []);
            renderViews(d.views || []);
        } catch (err) {
            console.error('Failed to load activity', err);
        }
    }
    function renderSearches(searches) {
        const list = document.getElementById('searchesList');
        if (!list) return;
        if (searches.length === 0) {
            list.innerHTML = '<div class="activity-empty">No searches yet. Go discover!</div>';
            return;
        }
        list.innerHTML = searches.map(s => `
            <a href="/?q=${encodeURIComponent(s.query)}" class="activity-item" onclick="reSearch(event, '${escapeAttr(s.query)}')">
                <div class="activity-icon activity-icon-search">🔍</div>
                <div class="activity-info">
                    <div class="activity-title">${escapeHtml(s.query)}</div>
                    <div class="activity-meta">${timeAgo(s.searched_at)} · ${s.result_count} results · ${s.source}</div>
                </div>
                <span class="activity-badge">${s.result_count}</span>
            </a>`
        ).join('');
    }
    function renderViews(views) {
        const list = document.getElementById('viewsList');
        if (!list) return;
        if (views.length === 0) {
            list.innerHTML = '<div class="activity-empty">No papers viewed yet.</div>';
            return;
        }
        list.innerHTML = views.map(v => {
            const title = v.title.length > 55 ? v.title.substring(0, 55) + '…' : v.title;
            return `
                <a href="/paper/${encodeURIComponent(v.paper_id)}" class="activity-item">
                    <div class="activity-icon activity-icon-view">📄</div>
                    <div class="activity-info">
                        <div class="activity-title">${escapeHtml(title)}</div>
                        <div class="activity-meta">${timeAgo(v.viewed_at)}</div>
                    </div>
                </a>`;
        }).join('');
    }
    function bindEvents() {
        const clearBtn = document.getElementById('clearHistoryBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', async () => {
                if (!confirm('Clear all search history?')) return;
                await fetch('/api/dashboard/history', { method: 'DELETE' });
                await refreshAll();
            });
        }
    }
    window.reSearch = function (e, query) {
        e.preventDefault();
        sessionStorage.setItem('reSearchQuery', query);
        window.location.href = '/';
    };
    function timeAgo(isoStr) {
        const diff = Date.now() - new Date(isoStr).getTime();
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
        return (text || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }
    window.addEventListener('beforeunload', () => clearInterval(pollTimer));
})();
