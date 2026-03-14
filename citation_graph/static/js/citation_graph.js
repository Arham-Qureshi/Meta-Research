/* ═══════════════════════════════════════════════════════════════
   citation_graph.js — Cytoscape.js Citation Network Visualiser
   Supports: Standalone (/citation-graph) & Embedded (paper_chat tab)
   Layout:  fCoSE — organic, force-directed, connected-papers style
   Colors:  Purple=center, Green=citation, Pink=reference, Blue=related
   ═══════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    /* ── State ────────────────────────────────────────────────── */
    var cy = null;
    var tooltipEl = null;
    var _cinemaMode = false;
    var _allNodes = [];            /* cached for paper list */
    var _activeListId = null;      /* currently selected list item */

    /* ── Type → Color Mapping ────────────────────────────────── */
    var TYPE_COLORS = {
        center:    '#b28cfa',
        citation:  '#4ade80',
        reference: '#f472b6',
        related:   '#60a5fa'
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
        if (type === 'related') return '🔵 Related';
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
       TYPING PLACEHOLDER ANIMATION
       ════════════════════════════════════════════════════════════ */
    var _typingPhrases = [
        'Search for "Attention Is All You Need"...',
        'Try a DOI: 10.1038/s41586-021-03819-2',
        'Explore "Graph Neural Networks"...',
        'Paste an arXiv ID: 2301.12345',
        'Search "Diffusion Models for Image Generation"...',
        'Try "Reinforcement Learning from Human Feedback"...'
    ];
    var _typingTimer = null;

    function startTypingAnimation(input) {
        if (!input) return;
        var phraseIdx = 0;
        var charIdx = 0;
        var isDeleting = false;
        var pauseMs = 80;

        function tick() {
            /* Stop when user focuses */
            if (document.activeElement === input && input.value.length > 0) {
                input.placeholder = '';
                return;
            }

            var phrase = _typingPhrases[phraseIdx];

            if (!isDeleting) {
                charIdx++;
                input.placeholder = phrase.substring(0, charIdx);
                if (charIdx === phrase.length) {
                    isDeleting = true;
                    pauseMs = 2000; /* pause before deleting */
                } else {
                    pauseMs = 55 + Math.random() * 40;
                }
            } else {
                charIdx--;
                input.placeholder = phrase.substring(0, charIdx);
                if (charIdx === 0) {
                    isDeleting = false;
                    phraseIdx = (phraseIdx + 1) % _typingPhrases.length;
                    pauseMs = 400;
                } else {
                    pauseMs = 30;
                }
            }

            _typingTimer = setTimeout(tick, pauseMs);
        }

        /* Reset animation when user leaves empty input */
        input.addEventListener('blur', function () {
            if (!input.value.trim()) {
                if (_typingTimer) clearTimeout(_typingTimer);
                charIdx = 0;
                isDeleting = false;
                tick();
            }
        });

        input.addEventListener('focus', function () {
            input.placeholder = '';
        });

        tick();
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

        /* Start typing animation */
        startTypingAnimation(searchInput);

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

                _allNodes = data.nodes;
                renderPaperList(data.nodes);
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
       LEFT PANEL — Scrollable Papers List
       ════════════════════════════════════════════════════════════ */
    function renderPaperList(nodes) {
        var listEl = document.getElementById('cgPaperList');
        if (!listEl) return;

        /* Sort: center first, then by citations desc */
        var sorted = nodes.slice().sort(function (a, b) {
            if (a.type === 'center') return -1;
            if (b.type === 'center') return 1;
            return (b.citations || 0) - (a.citations || 0);
        });

        listEl.innerHTML = '';
        sorted.forEach(function (n) {
            var item = document.createElement('div');
            item.className = 'cg-list-item' + (n.type === 'center' ? ' pinned' : '');
            item.setAttribute('data-node-id', n.id);

            var firstAuthor = (n.authors || 'Unknown').split(',')[0].trim();

            item.innerHTML =
                '<span class="cg-list-dot dot-' + esc(n.type) + '"></span>'
                + '<div class="cg-list-info">'
                + '<div class="cg-list-title">' + esc(n.label) + '</div>'
                + '<div class="cg-list-meta">'
                + '<span>' + esc(firstAuthor) + '</span>'
                + '<span>' + (n.year || '—') + '</span>'
                + '<span>📊 ' + Number(n.citations || 0).toLocaleString() + '</span>'
                + '</div></div>';

            /* Cross-highlight: list → graph */
            item.addEventListener('mouseenter', function () {
                highlightNodeById(n.id);
            });
            item.addEventListener('mouseleave', function () {
                unhighlightAll();
            });
            item.addEventListener('click', function () {
                selectNode(n.id);
            });

            listEl.appendChild(item);
        });
    }

    function highlightListItem(nodeId) {
        var listEl = document.getElementById('cgPaperList');
        if (!listEl) return;
        listEl.querySelectorAll('.cg-list-item').forEach(function (item) {
            item.classList.remove('active');
        });
        var target = listEl.querySelector('[data-node-id="' + CSS.escape(nodeId) + '"]');
        if (target) {
            target.classList.add('active');
            target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    function clearListHighlight() {
        var listEl = document.getElementById('cgPaperList');
        if (!listEl) return;
        listEl.querySelectorAll('.cg-list-item').forEach(function (item) {
            item.classList.remove('active');
        });
    }

    /* ════════════════════════════════════════════════════════════
       RIGHT PANEL — Paper Details (click-driven)
       ════════════════════════════════════════════════════════════ */
    function populateRightPanel(nodeData) {
        var el = document.getElementById('cgHoverContent');
        if (!el) return;
        var typeClass = 'cg-type-' + (nodeData.type || 'center');
        var typeLabel = nodeData.type === 'center' ? '🟣 This Paper'
            : nodeData.type === 'citation' ? '🟢 Cites This Paper'
                : nodeData.type === 'related' ? '🔵 Related Paper'
                    : '🔴 Referenced By This Paper';

        var conceptsHtml = '';
        var concepts = nodeData.concepts || [];
        if (concepts.length > 0) {
            conceptsHtml = '<div class="cg-concepts-row">'
                + concepts.map(function (c) {
                    return '<span class="cg-concept-chip">' + esc(c) + '</span>';
                }).join('')
                + '</div>';
        }

        var summary = nodeData.summary || '';
        var abstractHtml = summary
            ? '<div class="cg-detail-abstract">' + esc(summary).substring(0, 500) + (summary.length > 500 ? '...' : '') + '</div>'
            : '';

        var linkHtml = '';
        if (nodeData.doi) {
            linkHtml = '<a class="cg-detail-link" href="https://doi.org/' + esc(nodeData.doi) + '" target="_blank" rel="noopener">↗ View on DOI</a>';
        } else if (nodeData.id) {
            /* Try to provide a meaningful link */
            if (String(nodeData.id).startsWith('https://openalex.org/')) {
                linkHtml = '<a class="cg-detail-link" href="' + esc(nodeData.id) + '" target="_blank" rel="noopener">↗ View on OpenAlex</a>';
            } else {
                linkHtml = '<a class="cg-detail-link" href="https://www.semanticscholar.org/paper/' + esc(nodeData.id) + '" target="_blank" rel="noopener">↗ View on Semantic Scholar</a>';
            }
        }

        el.innerHTML =
            '<span class="cg-detail-type ' + typeClass + '">' + typeLabel + '</span>'
            + '<div class="cg-detail-title">' + esc(nodeData.fullLabel || nodeData.label || '') + '</div>'
            + '<div class="cg-detail-authors">' + esc(nodeData.authors || 'Unknown') + '</div>'
            + '<div class="cg-detail-row"><span>📅</span><span>' + (nodeData.year || '—') + '</span></div>'
            + '<div class="cg-detail-row"><span>📊</span><span>' + Number(nodeData.citations || 0).toLocaleString() + ' citations</span></div>'
            + (nodeData.doi ? '<div class="cg-detail-row"><span>🔗</span><span>' + esc(nodeData.doi) + '</span></div>' : '')
            + conceptsHtml
            + abstractHtml
            + linkHtml;
    }

    function clearRightPanel() {
        var el = document.getElementById('cgHoverContent');
        if (el) el.innerHTML = '<p class="cg-panel-empty">Click a node to see details.</p>';
    }

    /* ════════════════════════════════════════════════════════════
       GRAPH INTERACTION HELPERS
       ════════════════════════════════════════════════════════════ */
    function highlightNodeById(nodeId) {
        if (!cy) return;
        cy.elements().removeClass('faded highlighted');
        var node = cy.getElementById(nodeId);
        if (node.length === 0) return;
        var connected = node.closedNeighborhood();
        cy.elements().not(connected).addClass('faded');
        connected.addClass('highlighted');
    }

    function unhighlightAll() {
        if (!cy) return;
        cy.elements().removeClass('faded highlighted');
        cy.elements().animate({ style: { opacity: 1 } }, { duration: 150 });
    }

    function selectNode(nodeId) {
        if (!cy) return;
        var node = cy.getElementById(nodeId);
        if (node.length === 0) return;

        _activeListId = nodeId;
        highlightNodeById(nodeId);
        highlightListItem(nodeId);

        /* Find the node data from _allNodes */
        var nodeData = null;
        for (var i = 0; i < _allNodes.length; i++) {
            if (_allNodes[i].id === nodeId) {
                nodeData = _allNodes[i];
                break;
            }
        }
        if (nodeData) {
            populateRightPanel({
                id: nodeData.id,
                label: nodeData.label,
                fullLabel: nodeData.label,
                type: nodeData.type,
                year: nodeData.year,
                citations: nodeData.citations,
                authors: nodeData.authors,
                doi: nodeData.doi,
                summary: nodeData.summary || '',
                concepts: nodeData.concepts || []
            });
        } else {
            populateRightPanel(node.data());
        }

        /* Animate camera to node */
        cy.animate({
            center: { eles: node },
            duration: 400,
            easing: 'ease-out-cubic'
        });
    }

    /* ════════════════════════════════════════════════════════════
       RENDER CYTOSCAPE GRAPH
       Layout: fCoSE — organic, physics-based, connected-papers style
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
                    summary: n.summary || '',
                    concepts: n.concepts || [],
                    size: size,
                    color: typeToColor(n.type)
                }
            });
        });

        data.edges.forEach(function (e) {
            var srcNode = data.nodes.find(function (n) { return n.id === e.source; });
            var edgeType = 'citation';
            if (srcNode) {
                if (srcNode.type === 'center') {
                    /* center → reference OR center → related */
                    var tgtNode = data.nodes.find(function (n) { return n.id === e.target; });
                    edgeType = (tgtNode && tgtNode.type === 'related') ? 'related' : 'reference';
                }
            }
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

        /* Determine layout — use fcose if available, fallback to cose */
        var layoutName = (typeof cytoscape !== 'undefined' && cytoscape('layout', 'fcose')) ? 'fcose' : 'cose';

        var layoutConfig;
        if (layoutName === 'fcose') {
            layoutConfig = {
                name: 'fcose',
                animate: true,
                animationDuration: 900,
                animationEasing: 'ease-out-cubic',
                quality: 'default',
                randomize: true,
                nodeSeparation: 120,
                nodeRepulsion: function () { return 6000; },
                idealEdgeLength: function () { return 140; },
                edgeElasticity: function () { return 0.45; },
                gravity: 0.3,
                gravityRange: 3.8,
                numIter: 2500,
                padding: 50,
                fit: true,
                tile: true
            };
        } else {
            layoutConfig = {
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
            };
        }

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
                        'opacity': 0
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
                        'curve-style': 'bezier',
                        'target-arrow-shape': 'none',
                        'opacity': 0
                    }
                },
                {
                    selector: 'edge[edgeType="citation"]',
                    style: {
                        'line-color': 'rgba(74, 222, 128, 0.25)'
                    }
                },
                {
                    selector: 'edge[edgeType="reference"]',
                    style: {
                        'line-color': 'rgba(244, 114, 182, 0.25)'
                    }
                },
                {
                    selector: 'edge[edgeType="related"]',
                    style: {
                        'line-color': 'rgba(96, 165, 250, 0.25)'
                    }
                },
                { selector: 'node:selected', style: { 'border-width': 3, 'border-color': '#fbbf24' } },
                { selector: '.faded', style: { 'opacity': 0.12 } },
                { selector: '.highlighted', style: { 'opacity': 1 } }
            ],

            layout: layoutConfig,
            minZoom: 0.2, maxZoom: 3, wheelSensitivity: 0.3
        });

        /* ── Smooth fade-in after layout ─────────────────────── */
        cy.ready(function () {
            var delay = 0;
            ['center', 'citation', 'reference', 'related'].forEach(function (type) {
                var subset = cy.nodes('[type="' + type + '"]');
                setTimeout(function () {
                    subset.animate({ style: { opacity: 1 } }, { duration: 350, easing: 'ease-out' });
                }, delay);
                delay += 120;
            });
            setTimeout(function () {
                cy.edges().animate({ style: { opacity: 1 } }, { duration: 300, easing: 'ease-out' });
            }, delay);
        });

        /* ── Tooltip on hover ────────────────────────────────── */
        cy.on('mouseover', 'node', function (e) {
            var d = e.target.data();
            showTooltip(e.renderedPosition, d, container);
            /* Cross-highlight: graph → list */
            if (isStandalone) highlightListItem(d.id);
        });
        cy.on('mouseout', 'node', function () {
            hideTooltip();
            if (isStandalone && !_activeListId) clearListHighlight();
        });

        /* ── Select on tap (click) ───────────────────────────── */
        cy.on('tap', 'node', function (e) {
            var node = e.target;
            selectNode(node.id());
        });
        cy.on('tap', function (e) {
            if (e.target === cy) {
                _activeListId = null;
                cy.elements().removeClass('faded highlighted');
                cy.elements().animate({ style: { opacity: 1 } }, { duration: 200 });
                if (isStandalone) {
                    clearRightPanel();
                    clearListHighlight();
                }
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

        /* Re-layout with fcose */
        if (relayout) relayout.onclick = function () {
            if (!cy) return;
            var layoutName = (typeof cytoscape !== 'undefined' && cytoscape('layout', 'fcose')) ? 'fcose' : 'cose';
            var config;
            if (layoutName === 'fcose') {
                config = {
                    name: 'fcose',
                    animate: true, animationDuration: 600,
                    quality: 'default', randomize: true,
                    nodeSeparation: 120,
                    nodeRepulsion: function () { return 6000; },
                    idealEdgeLength: function () { return 140; },
                    gravity: 0.3, numIter: 2500, padding: 50
                };
            } else {
                config = {
                    name: 'cose',
                    animate: true, animationDuration: 600,
                    nodeRepulsion: function () { return 8000; },
                    idealEdgeLength: function () { return 120; },
                    gravity: 0.25, numIter: 300, padding: 50
                };
            }
            cy.layout(config).run();
        };

        /* Cinema Mode toggle */
        if (cinemaBtn) cinemaBtn.onclick = function () {
            var workspace = document.getElementById('cgWorkspace');
            if (!workspace) return;
            _cinemaMode = !_cinemaMode;
            workspace.classList.toggle('cinema-mode', _cinemaMode);
            cinemaBtn.classList.toggle('active', _cinemaMode);
            cinemaBtn.title = _cinemaMode ? 'Exit cinema mode' : 'Cinema mode';

            var resizeCount = 0;
            var resizeInterval = setInterval(function () {
                if (cy) cy.resize();
                resizeCount++;
                if (resizeCount >= 20) {
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
        var citCount = 0, refCount = 0, relCount = 0;
        data.nodes.forEach(function (n) {
            if (n.type === 'citation') citCount++;
            if (n.type === 'reference') refCount++;
            if (n.type === 'related') relCount++;
        });
        var pfx = isStandalone ? 'cg' : '';
        var citEl = document.getElementById(pfx + 'CitationCount') || document.getElementById('citationCount');
        var refEl = document.getElementById(pfx + 'ReferenceCount') || document.getElementById('referenceCount');
        var relEl = document.getElementById(pfx + 'RelatedCount');
        if (citEl) citEl.textContent = citCount + ' citing papers shown';
        if (refEl) refEl.textContent = refCount + ' referenced papers shown';
        if (relEl) relEl.textContent = relCount + ' related shown';
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
                _allNodes = data.nodes;
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
