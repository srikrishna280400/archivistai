// Archivist AI - Play Store Version App Logic
// Optimized for speed, smooth animations, 3 themes, ad/sub provisions

const { createApp, ref, computed, onMounted, watch } = Vue;

createApp({
    setup() {
        // State
        const articles = ref([]);
        const tags = ref([]);
        const stats = ref({ total_articles: 0, crawl_counts: {}, total_trash: 0 });
        const loading = ref(false);
        const searchQuery = ref('');
        const selectedTag = ref('');
        const sourceFilter = ref('all');
        const pageLimit = ref(window.innerWidth < 768 ? 50 : 100);
        const sharedArticleId = ref(null);

        // Theme management - 3 themes: dark, light, amber
        const themes = ['dark', 'light', 'amber'];
        const currentTheme = ref(localStorage.getItem('archivist-theme') || 'dark');

        const themeLabels = {
            'dark': 'Dark',
            'light': 'Light',
            'amber': 'Amber'
        };

        // AdMob / Monetization state (provision for integration)
        const adEnabled = ref(true);
        const isPremium = ref(false);

        // Set theme with smooth transition
        const setTheme = (theme) => {
            if (theme === currentTheme.value) return;
            currentTheme.value = theme;
            localStorage.setItem('archivist-theme', theme);
            document.documentElement.setAttribute('data-theme', theme);
        };

        // Cycle through themes
        const cycleTheme = () => {
            const currentIndex = themes.indexOf(currentTheme.value);
            const nextIndex = (currentIndex + 1) % themes.length;
            setTheme(themes[nextIndex]);
        };

        // Check premium status (placeholder for Google Play Billing integration)
        const checkPremiumStatus = async () => {
            // Provision for Google Play Billing v4
            // When Play Billing is integrated, this will:
            // 1. Query the BillingClient for subscription status
            // 2. Check if premium subscription is active
            // 3. Set isPremium.value = true
            // See: https://developer.android.com/google/play/billing integrate
            try {
                // Placeholder - return false for now
                isPremium.value = false;
            } catch (e) {
                console.log('Premium status check not implemented');
            }
        };

        // Fetch data with caching
        const fetchData = async () => {
            if (loading.value) return;
            loading.value = true;
            try {
                const cacheKey = 'archivist-data-cache';
                const cacheExpiryKey = 'archivist-cache-expiry';
                const cachedExpiry = localStorage.getItem(cacheExpiryKey);
                const now = Date.now();

                // Use cache if less than 30 seconds old
                if (cachedExpiry && now - parseInt(cachedExpiry) < 30000) {
                    const cached = localStorage.getItem(cacheKey);
                    if (cached) {
                        const data = JSON.parse(cached);
                        articles.value = data.articles || [];
                        tags.value = data.tags || [];
                        stats.value = data.stats || stats.value;
                        loading.value = false;
                        return;
                    }
                }

                const [artRes, tagsRes, statsRes] = await Promise.all([
                    fetch('/api/articles?page=0&limit=' + pageLimit.value),
                    fetch('/api/tags'),
                    fetch('/api/stats')
                ]);

                articles.value = await artRes.json();
                tags.value = await tagsRes.json();
                stats.value = await statsRes.json();

                // Cache the results
                localStorage.setItem(cacheKey, JSON.stringify({
                    articles: articles.value,
                    tags: tags.value,
                    stats: stats.value
                }));
                localStorage.setItem(cacheExpiryKey, now.toString());

            } catch (e) {
                console.error('Error loading data:', e);
            } finally {
                loading.value = false;
            }
        };

        // Refresh with forced fetch
        const refreshData = async () => {
            localStorage.removeItem('archivist-data-cache');
            await fetchData();
        };

        // Tag formatting
        const formatTag = (tag) => {
            if (!tag) return 'Untagged';
            const mappings = {
                'hp': 'Harry Potter',
                'f1': 'Formula 1',
                'startup vcs/sales': 'Startup VCs / Sales'
            };
            if (mappings[tag]) return mappings[tag];
            return tag.split('/')
                .map(w => w.split('-').map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(' '))
                .join(' / ');
        };

        // Get tag CSS class
        const getTagClass = (tag) => {
            if (!tag) return 'tag-interesting';
            const normalized = tag.toLowerCase().replace('/', '-').replace(' ', '-');
            return `tag-${normalized}`;
        };

        // Get article headline
        const getHeadline = (article) => {
            return article.crawled_h1 || article.crawled_title || article.original_title || 'Untitled';
        };

        // Update tag on backend
        const updateTag = async (article, newTag) => {
            if (isPremium.value) {
                article.assigned_tag = newTag || null;
                return;
            }
            try {
                const response = await fetch(`/api/articles/${article.id}/tag`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tag: newTag })
                });
                if (response.ok) {
                    article.assigned_tag = newTag || null;
                    const statsRes = await fetch('/api/stats');
                    stats.value = await statsRes.json();
                } else {
                    const err = await response.json();
                    alert('Error: ' + err.error);
                }
            } catch (e) {
                console.error('Error updating tag:', e);
            }
        };

        // Trashing articles
        const trashArticle = async (article) => {
            try {
                const response = await fetch(`/api/articles/${article.id}/trash`, { method: 'POST' });
                if (response.ok) {
                    article.deleted_at = new Date().toISOString();
                    const statsRes = await fetch('/api/stats');
                    stats.value = await statsRes.json();
                }
            } catch (e) {
                console.error('Error trashing article:', e);
            }
        };

        const restoreArticle = async (article) => {
            try {
                const response = await fetch(`/api/articles/${article.id}/restore`, { method: 'POST' });
                if (response.ok) {
                    article.deleted_at = null;
                    const statsRes = await fetch('/api/stats');
                    stats.value = await statsRes.json();
                }
            } catch (e) {
                console.error('Error restoring article:', e);
            }
        };

        const deleteArticlePermanently = async (article) => {
            if (!confirm('Delete this article permanently? This cannot be undone.')) return;
            try {
                const response = await fetch(`/api/articles/${article.id}/delete`, { method: 'DELETE' });
                if (response.ok) {
                    articles.value = articles.value.filter(a => a.id !== article.id);
                    const statsRes = await fetch('/api/stats');
                    stats.value = await statsRes.json();
                }
            } catch (e) {
                console.error('Error deleting article:', e);
            }
        };

        // Open article link
        const openArticle = (article) => {
            if (article && article.url) {
                window.open(article.url, '_blank', 'noopener,noreferrer');
            }
        };

        // Filtered articles computed
        const filteredArticles = computed(() => {
            return articles.value.filter(article => {
                // Trash filter
                if (sourceFilter.value === 'trash') {
                    if (!article.deleted_at) return false;
                } else {
                    if (article.deleted_at) return false;
                }

                // Source filter
                if (sourceFilter.value !== 'all' && sourceFilter.value !== 'trash') {
                    if (article.original_source !== sourceFilter.value) return false;
                }

                // Tag filter
                if (selectedTag.value) {
                    if (selectedTag.value === 'untagged') {
                        if (article.assigned_tag) return false;
                    } else if (article.assigned_tag !== selectedTag.value) {
                        return false;
                    }
                }

                // Search query
                if (searchQuery.value) {
                    const q = searchQuery.value.toLowerCase();
                    const title = article.original_title?.toLowerCase() || '';
                    const h1 = article.crawled_h1?.toLowerCase() || '';
                    const t = article.crawled_title?.toLowerCase() || '';
                    const url = article.url?.toLowerCase() || '';
                    const tag = article.assigned_tag?.toLowerCase() || '';
                    return title.includes(q) || h1.includes(q) || t.includes(q) || url.includes(q) || tag.includes(q);
                }
                return true;
            });
        });

        const paginatedArticles = computed(() => {
            return filteredArticles.value.slice(0, pageLimit.value);
        });

        const sortedTags = computed(() => {
            return [...tags.value].sort((a, b) => a.localeCompare(b));
        });

        const untaggedCount = computed(() => {
            return articles.value.filter(a => !a.assigned_tag && !a.deleted_at).length;
        });

        // Ad slot visibility for premium users
        const showAds = computed(() => adEnabled.value && !isPremium.value);

        // Handle URL parameters (for share target, ad-free links, etc.)
        const handleUrlParams = () => {
            const urlParams = new URLSearchParams(window.location.search);
            const sharedId = urlParams.get('shared');
            if (sharedId) {
                sharedArticleId.value = parseInt(sharedId);
            }
            const premium = urlParams.get('premium');
            if (premium === 'true') {
                isPremium.value = true;
                localStorage.setItem('archivist-premium', 'true');
            }
        };

        // Restore premium from localStorage
        const restorePremium = () => {
            const savedPremium = localStorage.getItem('archivist-premium');
            if (savedPremium === 'true') {
                isPremium.value = true;
            }
        };

        // Initialize
        onMounted(async () => {
            // Set theme
            document.documentElement.setAttribute('data-theme', currentTheme.value);

            // Restore premium status
            restorePremium();
            await checkPremiumStatus();

            // Fetch initial data
            await fetchData();

            // Handle URL params
            handleUrlParams();

            // Listen for theme toggle (Capacitor haptics)
            window.addEventListener('keyup', (e) => {
                if (e.key === 'T') cycleTheme();
            });
        });

        // Watch for shared article to scroll to it
        watch(sharedArticleId, (id) => {
            if (id && articles.value.length) {
                setTimeout(() => {
                    const el = document.querySelector(`[data-id="${id}"]`);
                    if (el) {
                        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        el.classList.add('ring-2', 'ring-accent', 'ring-opacity-50');
                        setTimeout(() => {
                            el.classList.remove('ring-2', 'ring-opacity-50');
                        }, 2000);
                    }
                }, 500);
            }
        });

        return {
            articles,
            tags,
            sortedTags,
            stats,
            loading,
            searchQuery,
            selectedTag,
            sourceFilter,
            pageLimit,
            paginatedArticles,
            filteredArticles,
            untaggedCount,
            currentTheme,
            themeLabels,
            setTheme,
            cycleTheme,
            checkPremiumStatus,
            fetchData,
            refreshData,
            formatTag,
            getTagClass,
            getHeadline,
            openArticle,
            updateTag,
            trashArticle,
            restoreArticle,
            deleteArticlePermanently,
            showAds,
            isPremium
        };
    }
}).mount('#vue-app');