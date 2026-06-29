// compare/static/compare/js/compare.js

const PREFIX = (window.SDF_PREFIX || 'sdf') + '_';
const COMPARE_KEY = PREFIX + "compare_products";
const SNAPSHOTS_KEY = PREFIX + "compare_snapshots";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function now() {
  return Date.now();
}

function getLang() {
  return window.DEFAULT_LANGUAGE || document.documentElement.lang || 'uk';
}

// ---------------------------------------------------------------------------
// compare_products – list of slugs
// ---------------------------------------------------------------------------
export function getCompareList() {
  try {
    const raw = localStorage.getItem(COMPARE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveCompareList(list) {
  localStorage.setItem(COMPARE_KEY, JSON.stringify(list));
}

export function addToCompare(slug) {
  const list = getCompareList();
  if (!list.includes(slug)) {
    list.push(slug);
    saveCompareList(list);
    updateAllUI(list);
    // Always fetch snapshot when user explicitly adds a product
    fetchAndCacheSnapshot(slug, true);
  }
}

export function removeFromCompare(slug) {
  let list = getCompareList();
  list = list.filter(item => item !== slug);
  saveCompareList(list);
  updateAllUI(list);

  // Remove only the snapshot for the current language
  const snapshots = getSnapshotsMap();
  const lang = getLang();
  if (snapshots[slug]) {
    delete snapshots[slug][lang];
    if (Object.keys(snapshots[slug]).length === 0) {
      delete snapshots[slug];
    }
    saveSnapshotsMap(snapshots);
  }

  // Refresh the compare table if it is currently visible
  refreshCompareTable();
}

// ---------------------------------------------------------------------------
// compare_snapshots – cached snapshot data grouped by language
// Structure: { [slug]: { [lang]: { snapshot, ts } } }
// ---------------------------------------------------------------------------
function getSnapshotsMap() {
  try {
    const raw = localStorage.getItem(SNAPSHOTS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveSnapshotsMap(map) {
  localStorage.setItem(SNAPSHOTS_KEY, JSON.stringify(map));
}

function hasSnapshotForLang(slug, lang) {
  const map = getSnapshotsMap();
  const entry = map[slug];
  if (!entry || !entry[lang]) return false;
  // Consider the snapshot fresh for 24 hours
  const maxAge = 24 * 60 * 60 * 1000;
  return (now() - entry[lang].ts) < maxAge;
}

async function fetchAndCacheSnapshot(slug, force = false) {
  const lang = getLang();
  // Skip if we already have a fresh snapshot for this language, unless forced
  if (!force && hasSnapshotForLang(slug, lang)) {
    return;
  }
  const url = `/api/compare/product/${encodeURIComponent(slug)}/?lang=${encodeURIComponent(lang)}`;
  try {
    const res = await fetch(url);
    if (!res.ok) return;
    const snapshot = await res.json();
    const map = getSnapshotsMap();
    if (!map[slug]) {
      map[slug] = {};
    }
    map[slug][lang] = { snapshot, ts: now() };
    saveSnapshotsMap(map);
  } catch (e) {
    console.warn("Failed to fetch compare snapshot", slug, e);
  }
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------
function updateAllUI(list) {
  updateBadge(list.length);
  refreshAllCompareButtons(list);
}

function updateBadge(count) {
  const badge = document.querySelector('.menu__badge');
  if (badge) {
    badge.textContent = count;
  }
  const link = document.querySelector('.compare-header a');
  if (link) {
    const prefix = getLangPrefix();
    link.href = prefix + 'compare/';
  }
}

function getLangPrefix() {
  const langs = (window.SUPPORTED_LANGUAGES || ['ru', 'en']).join('|');
  const regex = new RegExp(`^/(${langs})/`);
  const match = window.location.pathname.match(regex);
  return match ? '/' + match[1] + '/' : '/';
}

function refreshAllCompareButtons(list) {
  const buttons = document.querySelectorAll('.list__item-actions-compare');
  const addLabel = window.LABEL_COMPARE_ADD || 'Compare';
  const removeLabel = window.LABEL_COMPARE_REMOVE || 'In comparison';

  buttons.forEach(btn => {
    const slug = btn.dataset.productSlug;
    if (!slug) return;
    const isActive = list.includes(slug);
    btn.classList.toggle('is-active', isActive);
    const label = btn.querySelector('.list__item-actions-label');
    if (label) {
      label.textContent = isActive ? removeLabel : addLabel;
    }
  });
}

// ---------------------------------------------------------------------------
// Compare page specific
// ---------------------------------------------------------------------------
function initComparePage() {
  const wrapper = document.getElementById('compare-wrapper');
  if (!wrapper) return;
  const slugsInput = document.getElementById('compare-slugs-input');
  if (slugsInput) {
    slugsInput.value = getCompareList().join(',');
  }
  refreshCompareTable();
}

function refreshCompareTable() {
  const wrapper = document.getElementById('compare-wrapper');
  if (!wrapper) return;
  const slugsInput = document.getElementById('compare-slugs-input');
  if (slugsInput) {
    slugsInput.value = getCompareList().join(',');
  }
  const lang = getLang();
  htmx.ajax('GET', '/api/compare/table/?slugs=' + getCompareList().join(',') + '&lang=' + encodeURIComponent(lang), {
    target: '#compare-wrapper',
    swap: 'innerHTML'
  });
}

// ---------------------------------------------------------------------------
// Click handlers
// ---------------------------------------------------------------------------
function setupCompareButtons() {
  document.body.addEventListener('click', function(e) {
    // "Compare" buttons in product cards
    const btn = e.target.closest('.list__item-actions-compare');
    if (btn) {
      e.preventDefault();
      e.stopPropagation();
      const slug = btn.dataset.productSlug;
      if (!slug) return;
      const list = getCompareList();
      if (list.includes(slug)) {
        removeFromCompare(slug);
      } else {
        addToCompare(slug);
      }
      return;
    }

    // "Remove" buttons on the compare page
    const removeBtn = e.target.closest('.compare-remove');
    if (removeBtn) {
      e.preventDefault();
      const slug = removeBtn.dataset.removeSlug;
      if (slug) {
        removeFromCompare(slug);
      }
    }
  });
}

// ---------------------------------------------------------------------------
// HTMX integration – refresh buttons after every swap
// ---------------------------------------------------------------------------
document.body.addEventListener('htmx:afterSettle', function() {
  refreshAllCompareButtons(getCompareList());
});

// After the comparison table is loaded, cache snapshots for the current language
document.body.addEventListener('htmx:afterSwap', function(evt) {
  if (evt.detail.target.id === 'compare-wrapper') {
    const slugs = getCompareList();
    slugs.forEach(slug => {
      fetchAndCacheSnapshot(slug);
    });
  }
});

// ---------------------------------------------------------------------------
// Cross-tab synchronisation
// ---------------------------------------------------------------------------
window.addEventListener('storage', function(e) {
  if (e.key === COMPARE_KEY) {
    const list = getCompareList();
    updateAllUI(list);
  }
});

// ---------------------------------------------------------------------------
// Initialisation
// ---------------------------------------------------------------------------
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    setupCompareButtons();
    updateAllUI(getCompareList());
    initComparePage();
  });
} else {
  setupCompareButtons();
  updateAllUI(getCompareList());
  initComparePage();
}