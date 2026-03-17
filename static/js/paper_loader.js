
(function () {
    'use strict';
    document.addEventListener('DOMContentLoaded', function () {
        loadPaperData();
    });
    function loadPaperData() {
        var paperId = window.__PAPER_ID__;
        var infoPanel = document.getElementById('paperInfoPanel');
        var loadingEl = document.getElementById('paperInfoLoading');
        var infoContent = document.getElementById('paperInfoContent');
        var detailsEl = document.getElementById('paperDetails');
        var tabsEl = document.getElementById('paperTabs');
        if (!paperId || !infoPanel) return;
        fetch('/api/search?q=' + encodeURIComponent(paperId) + '&source=all&max=5')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var paper = null;
                if (data.papers && data.papers.length > 0) {
                    paper = data.papers.find(function (p) { return p.id === paperId; }) || data.papers[0];
                }
                if (!paper) {
                    if (loadingEl) {
                        loadingEl.innerHTML =
                            '<span class="graph-empty-icon">🔭</span>' +
                            '<h3>Paper not found</h3>' +
                            '<p class="loader-text">Could not load paper with ID: ' + escapeH(paperId) + '</p>' +
                            '<a href="/" class="btn btn-primary">← Back to Search</a>';
                    }
                    return;
                }
                window.__PAPER_DATA__ = paper;
                if (loadingEl) loadingEl.style.display = 'none';
                if (tabsEl) tabsEl.style.display = 'flex';
                if (infoContent) {
                    infoContent.innerHTML =
                        '<span class="paper-info-badge">' +
                        '<span>📄</span> ' + escapeH(paper.source_name || paper.source || 'Research Paper') +
                        '</span>' +
                        '<h1 class="paper-info-title">' + escapeH(paper.title) + '</h1>' +
                        '<p class="paper-info-authors">' + escapeH(paper.authors || 'Unknown authors') + '</p>' +
                        '<p class="paper-info-date">' + (paper.published ? 'Published: ' + escapeH(paper.published) : '') + '</p>';
                }
                var categories = (paper.categories || [])
                    .map(function (c) { return '<span class="paper-info-cat-chip">' + escapeH(c) + '</span>'; })
                    .join('');
                if (detailsEl) {
                    detailsEl.innerHTML =
                        '<h4 class="paper-info-section-title">Abstract</h4>' +
                        '<p class="paper-info-abstract">' + escapeH(paper.full_summary || paper.summary || 'No abstract available.') + '</p>' +
                        (categories ? '<h4 class="paper-info-section-title">Categories</h4><div class="paper-info-categories">' + categories + '</div>' : '') +
                        '<div class="paper-info-actions">' +
                        (paper.pdf_url ? '<a href="' + escapeH(paper.pdf_url) + '" target="_blank" rel="noopener" class="btn btn-download"><span>📥</span> Download PDF</a>' : '') +
                        (paper.abstract_url ? '<a href="' + escapeH(paper.abstract_url) + '" target="_blank" rel="noopener" class="btn btn-ghost"><span>🔗</span> View Page</a>' : '') +
                        '<button id="summarizeBtn" class="btn btn-summarize"><span>📝</span> Full Summary & Use Cases</button>' +
                        '</div>';
                }
                if (typeof window.__initChatAfterLoad === 'function') {
                    window.__initChatAfterLoad();
                }
            })
            .catch(function (err) {
                console.error('Failed to fetch paper:', err);
                if (loadingEl) {
                    loadingEl.innerHTML =
                        '<span class="graph-empty-icon">⚠️</span>' +
                        '<h3>Error loading paper</h3>' +
                        '<p class="loader-text">Something went wrong. Please try again.</p>' +
                        '<a href="/" class="btn btn-primary">← Back to Search</a>';
                }
            });
    }
    function escapeH(text) {
        if (!text) return '';
        var d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    }
})();
