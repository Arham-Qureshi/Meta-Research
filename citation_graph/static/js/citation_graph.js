/* ═══════════════════════════════════════════════════════════════
   citation_graph.js — Cytoscape.js Citation Network Visualiser
   Supports: Standalone (/citation-graph) & Embedded (paper_chat tab)
   Layout:  Force-directed (cose) — organic, connected-papers style
   Colors:  Purple=center, Green=citation, Pink=reference
   ═══════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    /* ── State ────────────────────────────────────────────────── */
    var cy = null;
    var tooltipEl = null;
    var _cinemaMode = false;

    /* ── Type → Color Mapping ────────────────────────────────── */
    var TYPE_COLORS = {
        center:    '#b28cfa',   /* purple  */
        citation:  '#4ade80',   /* green   */
        reference: '#f472b6'    /* pink    */
    };

    function typeToColor(type) {
        return TYPE_COLORS[type] || TYPE_COLORS.citation;
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
        if (type === 'center') return '🟣 This Paper';
        if (type === 'citation') return '🟢 Cites This';
        if (type === 'reference') return '🩷 Referenced';
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
                    var papers = data.papers || [];
                    if (papers.length === 0) {
                        dropdown.innerHTML = '<div class="cg-paper-result" style="color:#888;text-align:center;">No papers found or rate-limited. Try a broader search or wait.</div>';
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

    /* Year legend removed — nodes are now colored by type */

    /* ════════════════════════════════════════════════════════════
       RENDER CYTOSCAPE GRAPH
       Layout: force-directed (cose) — organic, connected-papers style
       Colors: purple=center, green=citation, pink=reference
       ════════════════════════════════════════════════════════════ */
    function renderGraph(container, data, isStandalone) {
        var elements = [];

        data.nodes.forEach(function (n) {
            var size = n.type === 'center' ? 60 : logSize(n.citations);

            /* Label as 'Author, Year' like Connected Papers */
            var firstAuthor = (n.authors || 'Unknown').split(',')[0].trim();
            var nodeLabel = firstAuthor + (n.year ? ', ' + n.year : '');

            elements.push({
                group: 'nodes',
                data: {
                    id: n.id,
                    label: nodeLabel,
                    fullLabel: n.label,
                    type: n.type,
                    year: n.year,
                    citations: n.citations,
                    authors: n.authors || '',
                    doi: n.doi || '',
                    size: size,
                    color: typeToColor(n.type)
                }
            });
        });

        data.edges.forEach(function (e) {
            /* Determine edge type from the node types:
               citation nodes point TO center → edgeType = 'citation'
               center points TO reference nodes → edgeType = 'reference' */
            var srcNode = data.nodes.find(function (n) { return n.id === e.source; });
            var edgeType = (srcNode && srcNode.type === 'center') ? 'reference' : 'citation';
            elements.push({
                group: 'edges',
                data: {
                    id: e.source + '->' + e.target,
                    source: e.source,
                    target: e.target,
                    edgeType: edgeType
                }
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
                        'border-width': 3, 'border-color': 'rgba(178,140,250,0.5)',
                        'font-size': '9px', 'font-weight': 700, 'color': '#e8e8f0',
                        'text-max-width': '140px',
                        'shadow-blur': 15,
                        'shadow-color': 'rgba(178,140,250,0.35)',
                        'shadow-opacity': 1
                    }
                },
                { selector: 'node:active', style: { 'overlay-opacity': 0.08 } },
                {
                    selector: 'edge',
                    style: {
                        'width': 1.4, 'line-color': 'rgba(255,255,255,0.10)',
                        'target-arrow-color': 'rgba(255,255,255,0.18)',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier', 'arrow-scale': 0.7,
                        'opacity': 0  /* start invisible for fade-in */
                    }
                },
                /* Green-tinted edges for citation connections */
                {
                    selector: 'edge[edgeType="citation"]',
                    style: {
                        'line-color': 'rgba(74, 222, 128, 0.25)',
                        'target-arrow-color': 'rgba(74, 222, 128, 0.45)'
                    }
                },
                /* Pink-tinted edges for reference connections */
                {
                    selector: 'edge[edgeType="reference"]',
                    style: {
                        'line-color': 'rgba(244, 114, 182, 0.25)',
                        'target-arrow-color': 'rgba(244, 114, 182, 0.45)'
                    }
                },
                { selector: 'node:selected', style: { 'border-width': 3, 'border-color': '#fbbf24' } },
                { selector: '.faded', style: { 'opacity': 0.12 } },
                { selector: '.highlighted', style: { 'opacity': 1 } }
            ],

            /* ── Force-directed cose layout — organic, connected-papers look */
            layout: {
                name: 'cose',
                animate: 'end',
                animationDuration: 800,
                animationEasing: 'ease-out-cubic',
                nodeRepulsion: function () { return 8000; },
                idealEdgeLength: function () { return 120; },
                edgeElasticity: function () { return 100; },
                gravity: 0.25,
                numIter: 300,
                padding: 50,
                nestingFactor: 1.2,
                randomize: false,
                componentSpacing: 80
            },

            minZoom: 0.2, maxZoom: 3, wheelSensitivity: 0.3
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
        var cinemaBtn = document.getElementById('cgCinemaBtn');

        if (zoomIn) zoomIn.onclick = function () { if (cy) cy.zoom(cy.zoom() * 1.3); };
        if (zoomOut) zoomOut.onclick = function () { if (cy) cy.zoom(cy.zoom() * 0.7); };
        if (fit) fit.onclick = function () { if (cy) cy.fit(null, 30); };

        /* Re-layout  */
        if (relayout) relayout.onclick = function () {
            if (!cy) return;
            cy.layout({
                name: 'cose',
                animate: true, animationDuration: 600,
                nodeRepulsion: function () { return 8000; },
                idealEdgeLength: function () { return 120; },
                gravity: 0.25, numIter: 300, padding: 50
            }).run();
        };

        /* Cinema Mode toggle */
        if (cinemaBtn) cinemaBtn.onclick = function () {
            var workspace = document.getElementById('cgWorkspace');
            if (!workspace) return;
            _cinemaMode = !_cinemaMode;
            workspace.classList.toggle('cinema-mode', _cinemaMode);
            cinemaBtn.classList.toggle('active', _cinemaMode);
            cinemaBtn.title = _cinemaMode ? 'Exit cinema mode' : 'Cinema mode';

            /* Continuously resize during the 400ms CSS transition
               so the canvas tracks the grid shrinking/expanding.
               This prevents the right sidebar overflow bug. */
            var resizeCount = 0;
            var resizeInterval = setInterval(function () {
                if (cy) cy.resize();
                resizeCount++;
                if (resizeCount >= 20) {  /* 20 × 25ms = 500ms */
                    clearInterval(resizeInterval);
                    if (cy) {
                        cy.resize();
                        cy.fit(null, 30);
                    }
                }
            }, 25);
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
        if (citEl) citEl.textContent = citCount + ' citing papers shown';
        if (refEl) refEl.textContent = refCount + ' referenced papers shown';
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
