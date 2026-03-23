
(function () {
    'use strict';
    var trendingGrid = null;
    var trendingLoading = null;
    var newsGrid = null;
    var newsLoading = null;
    document.addEventListener('DOMContentLoaded', function () {
        trendingGrid = document.getElementById('trendingGrid');
        trendingLoading = document.getElementById('trendingLoading');
        newsGrid = document.getElementById('newsGrid');
        newsLoading = document.getElementById('newsLoading');
        loadTrending();
        loadNews();
        var refreshTrending = document.getElementById('refreshTrending');
        var refreshNews = document.getElementById('refreshNews');
        if (refreshTrending) {
            refreshTrending.addEventListener('click', function () {
                refreshTrending.classList.add('spinning');
                loadTrending(function () {
                    refreshTrending.classList.remove('spinning');
                });
            });
        }
        if (refreshNews) {
            refreshNews.addEventListener('click', function () {
                refreshNews.classList.add('spinning');
                loadNews(function () {
                    refreshNews.classList.remove('spinning');
                });
            });
        }
    });
    function loadTrending(onDone) {
        if (!trendingGrid) return;
        showSkeleton(trendingLoading, true);
        trendingGrid.innerHTML = '';
        fetch('/api/trending?max=12')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                showSkeleton(trendingLoading, false);
                var papers = data.papers || [];
                if (papers.length === 0) {
                    trendingGrid.innerHTML = emptyState('🔬', 'No trending papers right now', 'Check back later – we refresh every few hours.');
                } else {
                    renderTrendingCards(papers);
                }
                if (onDone) onDone();
            })
            .catch(function (err) {
                showSkeleton(trendingLoading, false);
                trendingGrid.innerHTML = emptyState('⚠️', 'Could not load trending papers', 'Please try again later.');
                console.error('[Discover] Trending error:', err);
                if (onDone) onDone();
            });
    }
    function loadNews(onDone) {
        if (!newsGrid) return;
        showSkeleton(newsLoading, true);
        newsGrid.innerHTML = '';
        fetch('/api/news')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                showSkeleton(newsLoading, false);
                var articles = data.articles || [];
                if (articles.length === 0) {
                    newsGrid.innerHTML = emptyState('📰', 'No news articles available', 'Add a GNEWS_API_KEY or NEWSDATA_API_KEY to your .env to enable the news feed.');
                } else {
                    renderNewsCards(articles);
                }
                if (onDone) onDone();
            })
            .catch(function (err) {
                showSkeleton(newsLoading, false);
                newsGrid.innerHTML = emptyState('⚠️', 'Could not load news', 'Please try again later.');
                console.error('[Discover] News error:', err);
                if (onDone) onDone();
            });
    }
    function renderTrendingCards(papers) {
        papers.forEach(function (paper, idx) {
            var card = document.createElement('div');
            card.className = 'trending-card';
            card.setAttribute('role', 'article');
            var cats = (paper.categories || []).slice(0, 3).map(function (c) {
                return '<span class="trending-cat-chip">' + esc(c) + '</span>';
            }).join('');
            var journal = paper.journal
                ? '<span class="trending-meta-chip meta-chip-journal" title="' + esc(paper.journal) + '">' + esc(truncate(paper.journal, 22)) + '</span>'
                : '';
            card.innerHTML =
                '<span class="trending-rank">#' + (idx + 1) + '</span>' +
                '<h3 class="trending-card-title">' + esc(paper.title) + '</h3>' +
                '<p class="trending-card-authors">' + esc(paper.authors || 'Unknown') + '</p>' +
                '<div class="trending-card-meta">' +
                '<span class="trending-meta-chip meta-chip-citations">📊 ' + formatNum(paper.citations || 0) + ' citations</span>' +
                '<span class="trending-meta-chip meta-chip-year">📅 ' + esc(paper.published || '') + '</span>' +
                journal +
                '</div>' +
                '<p class="trending-card-summary">' + esc(stripHtml(paper.summary || '')) + '</p>' +
                (cats ? '<div class="trending-card-categories">' + cats + '</div>' : '');
            card.addEventListener('click', function () {
                var pid = paper.id || '';
                if (pid) {
                    window.location.href = '/paper/' + encodeURIComponent(pid);
                } else if (paper.abstract_url) {
                    window.open(paper.abstract_url, '_blank');
                }
            });
            trendingGrid.appendChild(card);
        });
        var cards = trendingGrid.querySelectorAll('.trending-card');
        cards.forEach(function (card, i) {
            card.style.opacity = '0';
            card.style.transform = 'translateY(16px)';
            setTimeout(function () {
                card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, i * 60);
        });
    }
    function renderNewsCards(articles) {
        articles.forEach(function (article) {
            var card = document.createElement('a');
            card.className = 'news-card';
            card.href = article.url || '#';
            card.target = '_blank';
            card.rel = 'noopener noreferrer';
            var imageHtml = article.image
                ? '<img class="news-card-image" src="' + esc(article.image) + '" alt="" loading="lazy">'
                : '<div class="news-card-image-placeholder">📰</div>';
            var providerBadge = article.provider
                ? '<span class="news-card-provider">' + esc(article.provider) + '</span>'
                : '';
            card.innerHTML =
                imageHtml +
                '<div class="news-card-body">' +
                '<span class="news-card-source">' + esc(article.source_name || 'News') + '</span>' +
                '<h3 class="news-card-title">' + esc(article.title) + '</h3>' +
                '<p class="news-card-desc">' + esc(article.description || '') + '</p>' +
                '<span class="news-card-date">' + formatDate(article.published) + providerBadge + '</span>' +
                '</div>';
            newsGrid.appendChild(card);
        });
        var cards = newsGrid.querySelectorAll('.news-card');
        cards.forEach(function (card, i) {
            card.style.opacity = '0';
            card.style.transform = 'translateY(16px)';
            setTimeout(function () {
                card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, i * 60);
        });
    }
    function esc(text) {
        if (!text) return '';
        var d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    }
    function stripHtml(html) {
        if (!html) return '';
        var d = document.createElement('div');
        d.innerHTML = html;
        var text = d.textContent || d.innerText || '';
        return text.replace(/<\/?[^>]+(>|$)/g, "");
    }
    function truncate(str, len) {
        if (!str) return '';
        return str.length > len ? str.substring(0, len) + '…' : str;
    }
    function formatNum(n) {
        if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
        if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
        return String(n);
    }
    function formatDate(dateStr) {
        if (!dateStr) return '';
        try {
            var d = new Date(dateStr);
            if (isNaN(d.getTime())) return dateStr;
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        } catch (e) {
            return dateStr;
        }
    }
    function showSkeleton(el, show) {
        if (el) el.style.display = show ? 'grid' : 'none';
    }
    function emptyState(icon, title, text) {
        return '<div class="empty-state">' +
            '<span class="empty-state-icon">' + icon + '</span>' +
            '<h3>' + title + '</h3>' +
            '<p>' + text + '</p>' +
            '</div>';
    }
})();
