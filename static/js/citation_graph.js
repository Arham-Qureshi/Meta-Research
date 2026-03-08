/* ═══════════════════════════════════════════════════════════════
   citation_graph.js  –  Cytoscape.js Citation Network Visualiser
   ═══════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    /* ── State ───────────────────────────────────────────────── */
    let cy = null;
    let tooltipEl = null;

    /* ── Initialise ─────────────────────────────────────────── */
    function initGraph() {
        const container = document.getElementById('graphCanvas');
        const loadingEl = document.getElementById('graphLoading');
        const emptyEl = document.getElementById('graphEmpty');
        tooltipEl = document.getElementById('graphTooltip');

        if (!container) return;

        var paperId = window.__PAPER_ID__;
        if (!paperId) {
            showEmpty(emptyEl, loadingEl, 'No paper ID available.');
            return;
        }

        showLoading(loadingEl, true);

        fetch('/api/paper/graph?id=' + encodeURIComponent(paperId))
            .then(function (r) { return r.json(); })
            .then(function (data) {
                showLoading(loadingEl, false);

                if (data.error || !data.nodes || data.nodes.length === 0) {
                    showEmpty(emptyEl, loadingEl, data.error || 'No citation data found for this paper.');
                    return;
                }

                renderGraph(container, data);
                updateStats(data);
            })
            .catch(function (err) {
                showLoading(loadingEl, false);
                showEmpty(emptyEl, loadingEl, 'Failed to load citation graph.');
                console.error('[CitationGraph]', err);
            });
    }

    /* ── Render Cytoscape Graph ──────────────────────────────── */
    function renderGraph(container, data) {
        var elements = [];

        /* Nodes */
        data.nodes.forEach(function (n) {
            var size = 30;
            if (n.type === 'center') size = 55;
            else if (n.citations > 100) size = 42;
            else if (n.citations > 20) size = 36;

            elements.push({
                group: 'nodes',
                data: {
                    id: n.id,
                    label: truncate(n.label, 35),
                    fullLabel: n.label,
                    type: n.type,
                    year: n.year,
                    citations: n.citations,
                    authors: n.authors || '',
                    size: size
                }
            });
        });

        /* Edges */
        data.edges.forEach(function (e) {
            elements.push({
                group: 'edges',
                data: {
                    id: e.source + '->' + e.target,
                    source: e.source,
                    target: e.target
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
                        'width': 'data(size)',
                        'height': 'data(size)',
                        'label': 'data(label)',
                        'font-size': '7px',
                        'font-family': 'Inter, sans-serif',
                        'font-weight': 500,
                        'color': '#c0c0d0',
                        'text-valign': 'bottom',
                        'text-halign': 'center',
                        'text-margin-y': 6,
                        'text-max-width': '100px',
                        'text-wrap': 'ellipsis',
                        'background-color': '#34d399',
                        'border-width': 1.5,
                        'border-color': 'rgba(255,255,255,0.08)',
                        'transition-property': 'background-color, border-color, width, height',
                        'transition-duration': '0.2s'
                    }
                },
                {
                    selector: 'node[type="center"]',
                    style: {
                        'background-color': '#818cf8',
                        'border-width': 3,
                        'border-color': 'rgba(129,140,248,0.4)',
                        'font-size': '9px',
                        'font-weight': 700,
                        'color': '#e8e8f0',
                        'text-max-width': '140px'
                    }
                },
                {
                    selector: 'node[type="citation"]',
                    style: {
                        'background-color': '#34d399'
                    }
                },
                {
                    selector: 'node[type="reference"]',
                    style: {
                        'background-color': '#f472b6'
                    }
                },
                {
                    selector: 'node:active',
                    style: {
                        'overlay-opacity': 0.08
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 1.2,
                        'line-color': 'rgba(255,255,255,0.08)',
                        'target-arrow-color': 'rgba(255,255,255,0.15)',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'arrow-scale': 0.7
                    }
                },
                {
                    selector: 'node:selected',
                    style: {
                        'border-width': 3,
                        'border-color': '#fbbf24'
                    }
                }
            ],
            layout: {
                name: 'cose',
                animate: true,
                animationDuration: 800,
                nodeRepulsion: function () { return 6000; },
                idealEdgeLength: function () { return 100; },
                edgeElasticity: function () { return 80; },
                gravity: 0.3,
                numIter: 200,
                padding: 30
            },
            minZoom: 0.25,
            maxZoom: 3,
            wheelSensitivity: 0.3
        });

        /* ── Tooltip on hover ─────────────────────────────────── */
        cy.on('mouseover', 'node', function (e) {
            var node = e.target;
            var d = node.data();
            showTooltip(e.renderedPosition, d);
        });

        cy.on('mouseout', 'node', function () {
            hideTooltip();
        });

        /* ── Highlight neighbours on tap ──────────────────────── */
        cy.on('tap', 'node', function (e) {
            var node = e.target;
            cy.elements().removeClass('faded highlighted');
            var connected = node.closedNeighborhood();
            cy.elements().not(connected).addClass('faded');
            connected.addClass('highlighted');
        });

        cy.on('tap', function (e) {
            if (e.target === cy) {
                cy.elements().removeClass('faded highlighted');
            }
        });

        /* Add dynamic styles for faded/highlighted */
        cy.style()
            .selector('.faded')
            .style({ 'opacity': 0.15 })
            .selector('.highlighted')
            .style({ 'opacity': 1 })
            .update();
    }

    /* ── Tooltip helpers ─────────────────────────────────────── */
    function showTooltip(pos, data) {
        if (!tooltipEl) return;
        var titleEl = tooltipEl.querySelector('.graph-tooltip-title');
        var authorsEl = tooltipEl.querySelector('.graph-tooltip-authors');
        var metaEl = tooltipEl.querySelector('.graph-tooltip-meta');

        titleEl.textContent = data.fullLabel || data.label;
        authorsEl.textContent = data.authors || 'Unknown authors';
        metaEl.innerHTML =
            '<span>📅 ' + (data.year || '—') + '</span>' +
            '<span>📊 ' + (data.citations || 0) + ' citations</span>' +
            '<span>' + typeLabel(data.type) + '</span>';

        var container = document.getElementById('graphContainer');
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

    function typeLabel(type) {
        if (type === 'center') return '🎯 This Paper';
        if (type === 'citation') return '🟢 Cites This';
        if (type === 'reference') return '🔴 Referenced';
        return '';
    }

    /* ── Graph Controls ──────────────────────────────────────── */
    function bindControls() {
        var zoomInBtn = document.getElementById('graphZoomIn');
        var zoomOutBtn = document.getElementById('graphZoomOut');
        var fitBtn = document.getElementById('graphFit');
        var relayoutBtn = document.getElementById('graphRelayout');

        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', function () {
                if (cy) cy.zoom(cy.zoom() * 1.3);
            });
        }
        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', function () {
                if (cy) cy.zoom(cy.zoom() * 0.7);
            });
        }
        if (fitBtn) {
            fitBtn.addEventListener('click', function () {
                if (cy) cy.fit(null, 30);
            });
        }
        if (relayoutBtn) {
            relayoutBtn.addEventListener('click', function () {
                if (!cy) return;
                cy.layout({
                    name: 'cose',
                    animate: true,
                    animationDuration: 600,
                    nodeRepulsion: function () { return 6000; },
                    idealEdgeLength: function () { return 100; },
                    gravity: 0.3,
                    numIter: 200,
                    padding: 30
                }).run();
            });
        }
    }

    /* ── Stats ───────────────────────────────────────────────── */
    function updateStats(data) {
        var citCount = 0;
        var refCount = 0;
        data.nodes.forEach(function (n) {
            if (n.type === 'citation') citCount++;
            if (n.type === 'reference') refCount++;
        });

        var citEl = document.getElementById('citationCount');
        var refEl = document.getElementById('referenceCount');
        if (citEl) citEl.textContent = citCount + ' citations';
        if (refEl) refEl.textContent = refCount + ' references';
    }

    /* ── Utility ─────────────────────────────────────────────── */
    function truncate(str, len) {
        if (!str) return '';
        return str.length > len ? str.substring(0, len) + '…' : str;
    }

    function showLoading(el, show) {
        if (el) el.style.display = show ? 'flex' : 'none';
    }

    function showEmpty(emptyEl, loadingEl, msg) {
        if (loadingEl) loadingEl.style.display = 'none';
        if (emptyEl) {
            emptyEl.style.display = 'flex';
            var pEl = emptyEl.querySelector('p');
            if (pEl) pEl.textContent = msg;
        }
    }

    /* ── Expose init for tab switching ───────────────────────── */
    window.__initCitationGraph = function () {
        if (cy) return; // already initialised
        initGraph();
        bindControls();
    };

    /* Auto-bind tab switching */
    document.addEventListener('DOMContentLoaded', function () {
        var tabs = document.querySelectorAll('.paper-tab');
        tabs.forEach(function (tab) {
            tab.addEventListener('click', function () {
                /* Toggle active tab */
                tabs.forEach(function (t) { t.classList.remove('active'); });
                tab.classList.add('active');

                /* Show/hide tab content */
                var target = tab.getAttribute('data-tab');
                document.querySelectorAll('.tab-content').forEach(function (tc) {
                    tc.classList.remove('active');
                });
                var targetEl = document.getElementById(target);
                if (targetEl) targetEl.classList.add('active');

                /* Lazy-load graph on first switch */
                if (target === 'graphTab') {
                    window.__initCitationGraph();
                }
            });
        });
    });
})();
