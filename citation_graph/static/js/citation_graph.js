/* ═══════════════════════════════════════════════════════════════
   citation_graph.js — Cytoscape.js Citation Network Visualiser
   Supports: Standalone (/citation-graph) & Embedded (paper_chat tab)
   Layout:  Concentric rings — instant render, zero physics jitter
   ═══════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    /* ── State ────────────────────────────────────────────────── */
    var cy = null;
    var tooltipEl = null;
    var _yearRange = { min: 2000, max: 2025 };

    /* ── Year → Color Mapping ────────────────────────────────── */
    function yearToColor(year) {
        if (!year) return 'hsl(145, 50%, 52%)';
        var span = _yearRange.max - _yearRange.min;
        var t = span > 0 ? (year - _yearRange.min) / span : 0.5;
        t = Math.max(0, Math.min(1, t));
        return 'hsl(145, ' + (50 + t * 20) + '%, ' + (70 - t * 35) + '%)';
    }

    function computeYearRange(nodes) {
        var years = nodes.map(function (n) { return n.year; }).filter(Boolean);
        if (years.length === 0) return;
        _yearRange.min = Math.min.apply(null, years);
        _yearRange.max = Math.max.apply(null, years);
    }

    function logSize(citations) {
        return Math.min(20 + Math.log2(1 + (citations || 0)) * 4, 65);
    }

    /* ── Utility ─────────────────────────────────────────────── */
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

    function typeEmoji(type) {
        if (type === 'center') return '🎯 This Paper';
        if (type === 'citation') return '🟢 Cites This';
        if (type === 'reference') return '🔴 Referenced';
        return '';
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
       STANDALONE PAGE  (/citation-graph)
       ════════════════════════════════════════════════════════════ */
    function getSelectedSource() {
        var btn = document.querySelector('.cg-source-btn.active');
        return btn ? btn.getAttribute('data-source') : 'semantic_scholar';
    }

    function initStandalonePage() {
        var searchInput = document.getElementById('cgSearchInput');
        var searchBtn = document.getElementById('cgSearchBtn');
        var dropdown = document.getElementById('cgPaperResults');
        if (!searchInput) return;

        /* Source toggle */
        document.querySelectorAll('.cg-source-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                document.querySelectorAll('.cg-source-btn').forEach(function (b) {
                    b.classList.remove('active');
                });
                btn.classList.add('active');
                dropdown.innerHTML = '';
                dropdown.classList.remove('active');
            });
        });

        function doSearch() {
            var q = searchInput.value.trim();
            if (!q) return;
            var source = getSelectedSource();
            var label = source === 'openalex' ? 'OpenAlex' : 'Semantic Scholar';

            dropdown.innerHTML = '<div class="cg-paper-result" style="color:#888;text-align:center;">Searching ' + label + '...</div>';
            dropdown.classList.add('active');

            fetch('/api/search?q=' + encodeURIComponent(q) + '&source=' + source + '&max=15')
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    var papers = (data.papers || []).filter(function (p) {
                        return Number(p.citations || 0) >= 10;
                    });
                    if (papers.length === 0) {
                        dropdown.innerHTML = '<div class="cg-paper-result" style="color:#888;text-align:center;">No papers with 10+ citations found. Try a broader search.</div>';
                        return;
                    }
                    dropdown.innerHTML = papers.map(function (p) {
                        return '<div class="cg-paper-result" data-paper-id="' + esc(p.id) + '" data-paper-json=\'' + JSON.stringify(p).replace(/'/g, '&#39;') + '\'>'
                            + '<div class="cg-paper-result-title">' + esc(p.title) + '</div>'
                            + '<div class="cg-paper-result-meta">'
                            + '<span>' + esc(p.authors || 'Unknown') + '</span>'
                            + '<span>' + esc(p.published || '') + '</span>'
                            + '<span>📊 ' + Number(p.citations || 0).toLocaleString() + ' citations</span>'
                            + '</div></div>';
                    }).join('');

                    dropdown.querySelectorAll('.cg-paper-result[data-paper-id]').forEach(function (el) {
                        el.addEventListener('click', function () {
                            var paperId = el.getAttribute('data-paper-id');
                            var paperData = null;
                            try { paperData = JSON.parse(el.getAttribute('data-paper-json')); } catch (_) { }
                            dropdown.classList.remove('active');
                            searchInput.value = paperData ? paperData.title : paperId;
                            loadGraph(paperId, paperData);
                        });
                    });
                })
                .catch(function () {
                    dropdown.innerHTML = '<div class="cg-paper-result" style="color:#f87171;text-align:center;">Search failed. Try again.</div>';
                });
        }

        searchBtn.addEventListener('click', doSearch);
        searchInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') { e.preventDefault(); doSearch(); }
        });

        document.addEventListener('click', function (e) {
            if (!e.target.closest('.cg-search-area')) {
                dropdown.classList.remove('active');
            }
        });
    }

    /* ── Load Graph ──────────────────────────────────────────── */
    function loadGraph(paperId, paperData) {
        var workspace = document.getElementById('cgWorkspace');
        var container = document.getElementById('cgGraphCanvas');
        var loadingEl = document.getElementById('cgGraphLoading');
        var emptyEl = document.getElementById('cgGraphEmpty');
        var sourceBadge = document.getElementById('cgSourceBadge');
        var fallbackBadge = document.getElementById('cgFallbackBadge');
        tooltipEl = document.getElementById('cgGraphTooltip');

        workspace.style.display = 'grid';
        if (loadingEl) loadingEl.style.display = 'flex';
        if (emptyEl) emptyEl.style.display = 'none';
        container.style.display = 'block';

        if (paperData) populateLeftPanel(paperData, 'search');
        if (cy) { cy.destroy(); cy = null; }

        var source = getSelectedSource();
        fetch('/api/paper/graph?id=' + encodeURIComponent(paperId) + '&source=' + source + '&max_citations=20&max_references=20')
            .then(function (r) {
                if (!r.ok && r.status === 502) {
                    return r.json().then(function (d) { d._httpStatus = 502; return d; });
                }
                return r.json();
            })
            .then(function (data) {
                if (loadingEl) loadingEl.style.display = 'none';

                if (data.error || !data.nodes || data.nodes.length === 0) {
                    if (emptyEl) {
                        emptyEl.style.display = 'flex';
                        var h4 = emptyEl.querySelector('h4');
                        var p = emptyEl.querySelector('p');
                        var msg = data.error || 'No citation data found.';
                        if (msg.indexOf('429') !== -1) {
                            if (h4) h4.textContent = 'Rate Limited';
                            if (p) p.innerHTML = 'Semantic Scholar rate limit reached. <strong>Try switching to OpenAlex</strong> using the toggle above, or wait 1–2 minutes.';
                        } else {
                            if (h4) h4.textContent = 'No Citation Data';
                            if (p) p.textContent = msg;
                        }
                    }
                    return;
                }

                /* Source & fallback badges */
                if (sourceBadge) sourceBadge.textContent = data.source === 'openalex' ? 'OpenAlex' : 'Semantic Scholar';
                if (fallbackBadge) fallbackBadge.style.display = data.fallback_used ? 'inline' : 'none';

                if (data.center) populateLeftPanel(data.center, 'graph');
                renderGraph(container, data, true);
                updateStats(data, true);
                buildYearLegend(data.nodes);
            })
            .catch(function (err) {
                if (loadingEl) loadingEl.style.display = 'none';
                if (emptyEl) {
                    emptyEl.style.display = 'flex';
                    var p = emptyEl.querySelector('p');
                    if (p) p.textContent = 'Failed to load citation graph.';
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
        var cites = data.citationCount || data.citations || 0;
        var doi = data.doi || '';
        var summary = data.summary || data.full_summary || '';

        el.innerHTML =
            '<div class="cg-detail-title">' + esc(title) + '</div>'
            + '<div class="cg-detail-authors">' + esc(authors) + '</div>'
            + '<div class="cg-detail-row"><span>📅</span><span>' + esc(String(year)) + '</span></div>'
            + '<div class="cg-detail-row"><span>📊</span><span>' + Number(cites).toLocaleString() + ' citations</span></div>'
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
       RENDER CYTOSCAPE GRAPH
       Layout: concentric rings — instant, zero-physics
       Center ring = target paper
       Ring 1 = citations (papers that cite it)
       Ring 2 = references (papers it cites)
       ════════════════════════════════════════════════════════════ */
    function renderGraph(container, data, isStandalone) {
        computeYearRange(data.nodes);

        var elements = [];

        data.nodes.forEach(function (n) {
            var size = n.type === 'center' ? 55 : logSize(n.citations);

            /* Concentric level: center=3 (innermost), citation=2, reference=1 */
            var level = n.type === 'center' ? 3 : (n.type === 'citation' ? 2 : 1);

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
                    color: n.type === 'center' ? '#818cf8' : yearToColor(n.year),
                    level: level
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
                        'opacity': 0  /* start invisible for fade-in */
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
                        'curve-style': 'bezier', 'arrow-scale': 0.7,
                        'opacity': 0  /* start invisible for fade-in */
                    }
                },
                { selector: 'node:selected', style: { 'border-width': 3, 'border-color': '#fbbf24' } },
                { selector: '.faded', style: { 'opacity': 0.15 } },
                { selector: '.highlighted', style: { 'opacity': 1 } }
            ],

            /* ── Concentric layout — instant, no physics ────── */
            layout: {
                name: 'concentric',
                concentric: function (node) { return node.data('level'); },
                levelWidth: function () { return 1; },
                animate: false,
                minNodeSpacing: 40,
                padding: 40
            },

            minZoom: 0.25, maxZoom: 3, wheelSensitivity: 0.3
        });

        /* ── Smooth fade-in after layout ─────────────────────── */
        cy.ready(function () {
            /* Stagger the fade-in: center first, then citations, then references */
            var delay = 0;
            ['center', 'citation', 'reference'].forEach(function (type) {
                var subset = cy.nodes('[type="' + type + '"]');
                setTimeout(function () {
                    subset.animate({ style: { opacity: 1 } }, { duration: 350, easing: 'ease-out' });
                }, delay);
                delay += 120;
            });
            /* Fade in edges last */
            setTimeout(function () {
                cy.edges().animate({ style: { opacity: 1 } }, { duration: 300, easing: 'ease-out' });
            }, delay);
        });

        /* ── Tooltip on hover ────────────────────────────────── */
        cy.on('mouseover', 'node', function (e) {
            var d = e.target.data();
            showTooltip(e.renderedPosition, d, container);
            if (isStandalone) populateRightPanel(d);
        });
        cy.on('mouseout', 'node', function () { hideTooltip(); });

        /* ── Highlight neighbours on tap ─────────────────────── */
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
                cy.elements().animate({ style: { opacity: 1 } }, { duration: 200 });
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
        tooltipEl.querySelector('.graph-tooltip-title').textContent = data.fullLabel || data.label;
        tooltipEl.querySelector('.graph-tooltip-authors').textContent = data.authors || 'Unknown authors';
        tooltipEl.querySelector('.graph-tooltip-meta').innerHTML =
            '<span>📅 ' + (data.year || '—') + '</span>'
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

    /* ════════════════════════════════════════════════════════════
       CONTROLS
       ════════════════════════════════════════════════════════════ */
    function bindControls(isStandalone) {
        var pfx = isStandalone ? 'cg' : 'graph';

        var zoomIn = document.getElementById(pfx + 'ZoomIn') || document.getElementById('graphZoomIn');
        var zoomOut = document.getElementById(pfx + 'ZoomOut') || document.getElementById('graphZoomOut');
        var fit = document.getElementById(pfx + 'Fit') || document.getElementById('graphFit');
        var relayout = document.getElementById(pfx + 'Relayout') || document.getElementById('graphRelayout');

        if (zoomIn) zoomIn.onclick = function () { if (cy) cy.zoom(cy.zoom() * 1.3); };
        if (zoomOut) zoomOut.onclick = function () { if (cy) cy.zoom(cy.zoom() * 0.7); };
        if (fit) fit.onclick = function () { if (cy) cy.fit(null, 30); };

        /* Re-layout: use cose (physics) on-demand — user explicitly asked */
        if (relayout) relayout.onclick = function () {
            if (!cy) return;
            cy.layout({
                name: 'cose',
                animate: true, animationDuration: 600,
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
        var pfx = isStandalone ? 'cg' : '';
        var citEl = document.getElementById(pfx + 'CitationCount') || document.getElementById('citationCount');
        var refEl = document.getElementById(pfx + 'ReferenceCount') || document.getElementById('referenceCount');
        if (citEl) citEl.textContent = citCount + ' citations';
        if (refEl) refEl.textContent = refCount + ' references';
    }

    /* ════════════════════════════════════════════════════════════
       EMBEDDED MODE (paper_chat.html tab — lazy-loaded)
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
       INIT — detect mode
       ════════════════════════════════════════════════════════════ */
    document.addEventListener('DOMContentLoaded', function () {
        /* Standalone page */
        if (document.getElementById('cgPage')) {
            initStandalonePage();
            return;
        }

        /* Embedded (paper_chat.html) — bind tab switching */
        document.querySelectorAll('.paper-tab').forEach(function (tab) {
            tab.addEventListener('click', function () {
                document.querySelectorAll('.paper-tab').forEach(function (t) { t.classList.remove('active'); });
                tab.classList.add('active');
                var target = tab.getAttribute('data-tab');
                document.querySelectorAll('.tab-content').forEach(function (tc) { tc.classList.remove('active'); });
                var targetEl = document.getElementById(target);
                if (targetEl) targetEl.classList.add('active');
                if (target === 'graphTab') window.__initCitationGraph();
            });
        });
    });
})();
