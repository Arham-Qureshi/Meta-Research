/* ═══════════════════════════════════════════════════════════════
   citation_graph.js  –  Cytoscape.js Citation Network Visualiser
   Supports: Standalone page (/citation-graph) & Embedded tab (paper_chat)
   ═══════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    var cy = null;
    var tooltipEl = null;
    var _yearRange = { min: 2000, max: 2025 };

    /* ════════════════════════════════════════════════════════════
       YEAR-BASED COLOR MAPPING
       ════════════════════════════════════════════════════════════ */
    function yearToColor(year) {
        if (!year) return 'hsl(145, 50%, 52%)';
        var t = (_yearRange.max - _yearRange.min) > 0
            ? (year - _yearRange.min) / (_yearRange.max - _yearRange.min)
            : 0.5;
        t = Math.max(0, Math.min(1, t));
        var s = 50 + t * 20;   // 50% → 70%
        var l = 70 - t * 35;   // 70% → 35%  (light→dark)
        return 'hsl(145, ' + s + '%, ' + l + '%)';
    }

    function computeYearRange(nodes) {
        var years = nodes.map(function (n) { return n.year; }).filter(Boolean);
        if (years.length === 0) return;
        _yearRange.min = Math.min.apply(null, years);
        _yearRange.max = Math.max.apply(null, years);
    }

    function logSize(citations) {
        var s = 20 + Math.log2(1 + (citations || 0)) * 4;
        return Math.min(s, 65);
    }

    /* ════════════════════════════════════════════════════════════
       STANDALONE PAGE  (/citation-graph)
       ════════════════════════════════════════════════════════════ */
    function initStandalonePage() {
        var searchInput = document.getElementById('cgSearchInput');
        var searchBtn = document.getElementById('cgSearchBtn');
        var resultsDropdown = document.getElementById('cgPaperResults');
        if (!searchInput) return;

        function doSearch() {
            var q = searchInput.value.trim();
            if (!q) return;
            resultsDropdown.innerHTML = '<div class="cg-paper-result" style="color:#888;text-align:center;">Searching...</div>';
            resultsDropdown.classList.add('active');

            fetch('/api/search?q=' + encodeURIComponent(q) + '&source=all&max=10')
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    var papers = (data.papers || []).filter(function (p) {
                        return Number(p.citations || 0) >= 10;
                    });
                    if (papers.length === 0) {
                        resultsDropdown.innerHTML = '<div class="cg-paper-result" style="color:#888;text-align:center;">No papers with 10+ citations found. Try a broader search.</div>';
                        return;
                    }
                    resultsDropdown.innerHTML = papers.map(function (p) {
                        var citCount = Number(p.citations || 0);
                        return '<div class="cg-paper-result" data-paper-id="' + esc(p.id) + '" data-paper-json=\'' + JSON.stringify(p).replace(/'/g, '&#39;') + '\'>'
                            + '<div class="cg-paper-result-title">' + esc(p.title) + '</div>'
                            + '<div class="cg-paper-result-meta">'
                            + '<span>' + esc(p.authors || 'Unknown') + '</span>'
                            + '<span>' + esc(p.published || '') + '</span>'
                            + '<span>📊 ' + citCount.toLocaleString() + ' citations</span>'
                            + '<span>📡 ' + esc(p.source_name || p.source || '') + '</span>'
                            + '</div></div>';
                    }).join('');

                    // Bind click on each result
                    resultsDropdown.querySelectorAll('.cg-paper-result[data-paper-id]').forEach(function (el) {
                        el.addEventListener('click', function () {
                            var paperId = el.getAttribute('data-paper-id');
                            var paperData = null;
                            try { paperData = JSON.parse(el.getAttribute('data-paper-json')); } catch (_) { }
                            resultsDropdown.classList.remove('active');
                            searchInput.value = paperData ? paperData.title : paperId;
                            loadGraph(paperId, paperData);
                        });
                    });
                })
                .catch(function () {
                    resultsDropdown.innerHTML = '<div class="cg-paper-result" style="color:#f87171;text-align:center;">Search failed. Try again.</div>';
                });
        }

        searchBtn.addEventListener('click', doSearch);
        searchInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') { e.preventDefault(); doSearch(); }
        });

        // Close dropdown on outside click
        document.addEventListener('click', function (e) {
            if (!e.target.closest('.cg-search-area')) {
                resultsDropdown.classList.remove('active');
            }
        });
    }

    function loadGraph(paperId, paperData) {
        var workspace = document.getElementById('cgWorkspace');
        var container = document.getElementById('cgGraphCanvas');
        var loadingEl = document.getElementById('cgGraphLoading');
        var emptyEl = document.getElementById('cgGraphEmpty');
        var sourceBadge = document.getElementById('cgSourceBadge');
        tooltipEl = document.getElementById('cgGraphTooltip');

        workspace.style.display = 'grid';
        if (loadingEl) loadingEl.style.display = 'flex';
        if (emptyEl) emptyEl.style.display = 'none';
        container.style.display = 'block';

        // Populate left panel with search-result data while graph loads
        if (paperData) populateLeftPanel(paperData, 'search');

        // Destroy previous graph
        if (cy) { cy.destroy(); cy = null; }

        fetch('/api/paper/graph?id=' + encodeURIComponent(paperId) + '&max_citations=20&max_references=20')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (loadingEl) loadingEl.style.display = 'none';

                if (data.error || !data.nodes || data.nodes.length === 0) {
                    if (emptyEl) {
                        emptyEl.style.display = 'flex';
                        var pEl = emptyEl.querySelector('p');
                        if (pEl) pEl.textContent = data.error || 'No citation data found.';
                    }
                    return;
                }

                if (sourceBadge) sourceBadge.textContent = data.source === 'openalex' ? 'OpenAlex' : 'Semantic Scholar';

                // Update left panel with richer center data
                if (data.center) populateLeftPanel(data.center, 'graph');

                renderGraph(container, data, true);
                updateStats(data, true);
                buildYearLegend(data.nodes);
            })
            .catch(function (err) {
                if (loadingEl) loadingEl.style.display = 'none';
                if (emptyEl) {
                    emptyEl.style.display = 'flex';
                    var pEl = emptyEl.querySelector('p');
                    if (pEl) pEl.textContent = 'Failed to load citation graph.';
                }
                console.error('[CitationGraph]', err);
            });
    }

    /* ════════════════════════════════════════════════════════════
       LEFT PANEL — Origin Paper Details
       ════════════════════════════════════════════════════════════ */
    function populateLeftPanel(data, source) {
        var el = document.getElementById('cgOriginContent');
        if (!el) return;

        var title = data.title || data.label || 'Unknown';
        var authors = data.authors || 'Unknown authors';
        var year = data.year || data.published || '—';
        var citations = data.citationCount || data.citations || 0;
        var doi = data.doi || '';
        var summary = data.summary || data.full_summary || '';

        el.innerHTML =
            '<div class="cg-detail-title">' + esc(title) + '</div>'
            + '<div class="cg-detail-authors">' + esc(authors) + '</div>'
            + '<div class="cg-detail-row"><span>📅</span><span>' + esc(String(year)) + '</span></div>'
            + '<div class="cg-detail-row"><span>📊</span><span>' + Number(citations).toLocaleString() + ' citations</span></div>'
            + (doi ? '<div class="cg-detail-row"><span>🔗</span><span>' + esc(doi) + '</span></div>' : '')
            + (summary ? '<div class="cg-detail-abstract">' + esc(summary).substring(0, 400) + (summary.length > 400 ? '...' : '') + '</div>' : '')
            + (doi ? '<a class="cg-detail-link" href="https://doi.org/' + esc(doi) + '" target="_blank" rel="noopener">↗ View on DOI</a>' : '');
    }

    /* ════════════════════════════════════════════════════════════
       RIGHT PANEL — Hovered Node Details
       ════════════════════════════════════════════════════════════ */
    function populateRightPanel(nodeData) {
        var el = document.getElementById('cgHoverContent');
        if (!el) return;

        var typeClass = 'cg-type-' + (nodeData.type || 'center');
        var typeLabel = nodeData.type === 'center' ? '🟣 This Paper'
            : nodeData.type === 'citation' ? '🟢 Cites This Paper'
                : '🔴 Referenced By This Paper';

        el.innerHTML =
            '<span class="cg-detail-type ' + typeClass + '">' + typeLabel + '</span>'
            + '<div class="cg-detail-title">' + esc(nodeData.fullLabel || nodeData.label || '') + '</div>'
            + '<div class="cg-detail-authors">' + esc(nodeData.authors || 'Unknown') + '</div>'
            + '<div class="cg-detail-row"><span>📅</span><span>' + (nodeData.year || '—') + '</span></div>'
            + '<div class="cg-detail-row"><span>📊</span><span>' + Number(nodeData.citations || 0).toLocaleString() + ' citations</span></div>'
            + (nodeData.doi ? '<div class="cg-detail-row"><span>🔗</span><span>' + esc(nodeData.doi) + '</span></div>' : '')
            + (nodeData.id ? '<a class="cg-detail-link" href="https://www.semanticscholar.org/paper/' + esc(nodeData.id) + '" target="_blank" rel="noopener">↗ Open in Semantic Scholar</a>' : '');
    }

    function clearRightPanel() {
        var el = document.getElementById('cgHoverContent');
        if (el) el.innerHTML = '<p class="cg-panel-empty">Hover over a node to see details.</p>';
    }

    /* ════════════════════════════════════════════════════════════
       YEAR LEGEND
       ════════════════════════════════════════════════════════════ */
    function buildYearLegend(nodes) {
        computeYearRange(nodes);
        var minEl = document.getElementById('cgYearMin');
        var maxEl = document.getElementById('cgYearMax');
        var gradEl = document.getElementById('cgYearGradient');
        if (minEl) minEl.textContent = _yearRange.min;
        if (maxEl) maxEl.textContent = _yearRange.max;
        if (gradEl) {
            gradEl.style.background = 'linear-gradient(90deg, '
                + yearToColor(_yearRange.min) + ', '
                + yearToColor(_yearRange.max) + ')';
        }
    }

    /* ════════════════════════════════════════════════════════════
       RENDER CYTOSCAPE GRAPH  (shared by standalone & embedded)
       ════════════════════════════════════════════════════════════ */
    function renderGraph(container, data, isStandalone) {
        computeYearRange(data.nodes);

        var elements = [];

        data.nodes.forEach(function (n) {
            var size = n.type === 'center' ? 55 : logSize(n.citations);
            elements.push({
                group: 'nodes',
                data: {
                    id: n.id,
                    label: truncate(n.label, 30),
                    fullLabel: n.label,
                    type: n.type,
                    year: n.year,
                    citations: n.citations,
                    authors: n.authors || '',
                    doi: n.doi || '',
                    size: size,
                    color: n.type === 'center' ? '#818cf8' : yearToColor(n.year)
                }
            });
        });

        data.edges.forEach(function (e) {
            elements.push({
                group: 'edges',
                data: { id: e.source + '->' + e.target, source: e.source, target: e.target }
            });
        });

        cy = cytoscape({
            container: container,
            elements: elements,
            style: [
                {
                    selector: 'node',
                    style: {
                        'width': 'data(size)', 'height': 'data(size)',
                        'label': 'data(label)',
                        'font-size': '7px', 'font-family': 'Inter, sans-serif', 'font-weight': 500,
                        'color': '#c0c0d0',
                        'text-valign': 'bottom', 'text-halign': 'center',
                        'text-margin-y': 6, 'text-max-width': '100px', 'text-wrap': 'ellipsis',
                        'background-color': 'data(color)',
                        'border-width': 1.5,
                        'border-color': 'rgba(255,255,255,0.08)',
                        'transition-property': 'background-color, border-color, width, height',
                        'transition-duration': '0.2s'
                    }
                },
                {
                    selector: 'node[type="center"]',
                    style: {
                        'border-width': 3, 'border-color': 'rgba(129,140,248,0.4)',
                        'font-size': '9px', 'font-weight': 700, 'color': '#e8e8f0',
                        'text-max-width': '140px'
                    }
                },
                { selector: 'node:active', style: { 'overlay-opacity': 0.08 } },
                {
                    selector: 'edge',
                    style: {
                        'width': 1.2, 'line-color': 'rgba(255,255,255,0.08)',
                        'target-arrow-color': 'rgba(255,255,255,0.15)',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier', 'arrow-scale': 0.7
                    }
                },
                { selector: 'node:selected', style: { 'border-width': 3, 'border-color': '#fbbf24' } },
                { selector: '.faded', style: { 'opacity': 0.15 } },
                { selector: '.highlighted', style: { 'opacity': 1 } }
            ],
            layout: {
                name: 'cose',
                animate: true, animationDuration: 800,
                nodeRepulsion: function () { return 6000; },
                idealEdgeLength: function () { return 100; },
                edgeElasticity: function () { return 80; },
                gravity: 0.3, numIter: 200, padding: 30
            },
            minZoom: 0.25, maxZoom: 3, wheelSensitivity: 0.3
        });

        /* Tooltip on hover */
        cy.on('mouseover', 'node', function (e) {
            var d = e.target.data();
            showTooltip(e.renderedPosition, d, container);
            if (isStandalone) populateRightPanel(d);
        });
        cy.on('mouseout', 'node', function () {
            hideTooltip();
        });

        /* Highlight neighbours on tap */
        cy.on('tap', 'node', function (e) {
            var node = e.target;
            cy.elements().removeClass('faded highlighted');
            var connected = node.closedNeighborhood();
            cy.elements().not(connected).addClass('faded');
            connected.addClass('highlighted');
            if (isStandalone) populateRightPanel(node.data());
        });
        cy.on('tap', function (e) {
            if (e.target === cy) {
                cy.elements().removeClass('faded highlighted');
                if (isStandalone) clearRightPanel();
            }
        });

        bindControls(isStandalone);
    }

    /* ════════════════════════════════════════════════════════════
       TOOLTIP
       ════════════════════════════════════════════════════════════ */
    function showTooltip(pos, data, container) {
        if (!tooltipEl) return;
        var titleEl = tooltipEl.querySelector('.graph-tooltip-title');
        var authorsEl = tooltipEl.querySelector('.graph-tooltip-authors');
        var metaEl = tooltipEl.querySelector('.graph-tooltip-meta');
        titleEl.textContent = data.fullLabel || data.label;
        authorsEl.textContent = data.authors || 'Unknown authors';
        metaEl.innerHTML = '<span>📅 ' + (data.year || '—') + '</span>'
            + '<span>📊 ' + (data.citations || 0) + ' citations</span>'
            + '<span>' + typeEmoji(data.type) + '</span>';

        var rect = container.getBoundingClientRect();
        var left = pos.x + 15;
        var top = pos.y - 10;
        if (left + 300 > rect.width) left = pos.x - 310;
        if (top + 100 > rect.height) top = pos.y - 100;
        tooltipEl.style.left = left + 'px';
        tooltipEl.style.top = top + 'px';
        tooltipEl.classList.add('visible');
    }

    function hideTooltip() {
        if (tooltipEl) tooltipEl.classList.remove('visible');
    }

    function typeEmoji(type) {
        if (type === 'center') return '🎯 This Paper';
        if (type === 'citation') return '🟢 Cites This';
        if (type === 'reference') return '🔴 Referenced';
        return '';
    }

    /* ════════════════════════════════════════════════════════════
       CONTROLS
       ════════════════════════════════════════════════════════════ */
    function bindControls(isStandalone) {
        var prefix = isStandalone ? 'cg' : 'graph';
        var zoomIn = document.getElementById(prefix + 'ZoomIn') || document.getElementById('graphZoomIn');
        var zoomOut = document.getElementById(prefix + 'ZoomOut') || document.getElementById('graphZoomOut');
        var fit = document.getElementById(prefix + 'Fit') || document.getElementById('graphFit');
        var relayout = document.getElementById(prefix + 'Relayout') || document.getElementById('graphRelayout');

        if (zoomIn) zoomIn.onclick = function () { if (cy) cy.zoom(cy.zoom() * 1.3); };
        if (zoomOut) zoomOut.onclick = function () { if (cy) cy.zoom(cy.zoom() * 0.7); };
        if (fit) fit.onclick = function () { if (cy) cy.fit(null, 30); };
        if (relayout) relayout.onclick = function () {
            if (!cy) return;
            cy.layout({
                name: 'cose', animate: true, animationDuration: 600,
                nodeRepulsion: function () { return 6000; },
                idealEdgeLength: function () { return 100; },
                gravity: 0.3, numIter: 200, padding: 30
            }).run();
        };
    }

    /* ════════════════════════════════════════════════════════════
       STATS
       ════════════════════════════════════════════════════════════ */
    function updateStats(data, isStandalone) {
        var citCount = 0, refCount = 0;
        data.nodes.forEach(function (n) {
            if (n.type === 'citation') citCount++;
            if (n.type === 'reference') refCount++;
        });
        var prefix = isStandalone ? 'cg' : '';
        var citEl = document.getElementById(prefix + 'CitationCount') || document.getElementById('citationCount');
        var refEl = document.getElementById(prefix + 'ReferenceCount') || document.getElementById('referenceCount');
        if (citEl) citEl.textContent = citCount + ' citations';
        if (refEl) refEl.textContent = refCount + ' references';
    }

    /* ════════════════════════════════════════════════════════════
       EMBEDDED MODE (paper_chat.html tab - lazy-loaded)
       ════════════════════════════════════════════════════════════ */
    window.__initCitationGraph = function () {
        if (cy) return;
        var container = document.getElementById('graphCanvas');
        var loadingEl = document.getElementById('graphLoading');
        var emptyEl = document.getElementById('graphEmpty');
        tooltipEl = document.getElementById('graphTooltip');
        if (!container) return;

        var paperId = window.__PAPER_ID__;
        if (!paperId) { showEmpty(emptyEl, loadingEl, 'No paper ID available.'); return; }

        if (loadingEl) loadingEl.style.display = 'flex';

        fetch('/api/paper/graph?id=' + encodeURIComponent(paperId))
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (loadingEl) loadingEl.style.display = 'none';
                if (data.error || !data.nodes || data.nodes.length === 0) {
                    showEmpty(emptyEl, loadingEl, data.error || 'No citation data found.');
                    return;
                }
                renderGraph(container, data, false);
                updateStats(data, false);
            })
            .catch(function (err) {
                if (loadingEl) loadingEl.style.display = 'none';
                showEmpty(emptyEl, loadingEl, 'Failed to load citation graph.');
                console.error('[CitationGraph]', err);
            });
    };

    /* ════════════════════════════════════════════════════════════
       UTILITY
       ════════════════════════════════════════════════════════════ */
    function truncate(str, len) {
        if (!str) return '';
        return str.length > len ? str.substring(0, len) + '…' : str;
    }

    function esc(str) {
        if (!str) return '';
        var d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    function showEmpty(emptyEl, loadingEl, msg) {
        if (loadingEl) loadingEl.style.display = 'none';
        if (emptyEl) {
            emptyEl.style.display = 'flex';
            var pEl = emptyEl.querySelector('p');
            if (pEl) pEl.textContent = msg;
        }
    }

    /* ════════════════════════════════════════════════════════════
       INIT — detect which mode to run
       ════════════════════════════════════════════════════════════ */
    document.addEventListener('DOMContentLoaded', function () {
        // Standalone page mode
        if (document.getElementById('cgPage')) {
            initStandalonePage();
            return;
        }

        // Embedded mode — bind tab switching
        var tabs = document.querySelectorAll('.paper-tab');
        tabs.forEach(function (tab) {
            tab.addEventListener('click', function () {
                tabs.forEach(function (t) { t.classList.remove('active'); });
                tab.classList.add('active');
                var target = tab.getAttribute('data-tab');
                document.querySelectorAll('.tab-content').forEach(function (tc) {
                    tc.classList.remove('active');
                });
                var targetEl = document.getElementById(target);
                if (targetEl) targetEl.classList.add('active');
                if (target === 'graphTab') window.__initCitationGraph();
            });
        });
    });
})();
