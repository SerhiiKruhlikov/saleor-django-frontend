// basket/static/basket/js/basket.js

const PREFIX = (window.SDF_PREFIX || 'sdf') + '_';
const BASKET_KEY = PREFIX + 'basket';
const CURRENCY = window.CURRENCY || 'UAH';

// ---------------------------------------------------------------------------
// Basket data structure
// ---------------------------------------------------------------------------
function getDefaultBasket() {
  return { items: [], unavailableItems: [], snapshots: {} };
}

export function getBasket() {
  try {
    const raw = localStorage.getItem(BASKET_KEY);
    return raw ? JSON.parse(raw) : getDefaultBasket();
  } catch {
    return getDefaultBasket();
  }
}

function saveBasket(basket) {
  localStorage.setItem(BASKET_KEY, JSON.stringify(basket));
}

export function addToBasket(slug, quantity = 1) {
  const basket = getBasket();
  const existing = basket.items.find(item => item.slug === slug);
  if (existing) {
    existing.quantity += quantity;
  } else {
    basket.items.push({ slug, quantity });
  }
  saveBasket(basket);
  updateBasketUI();
  fetchAndCacheSnapshot(slug, true);
  if (document.getElementById('basket-wrapper')) {
    refreshBasketTable();
  }
}

export function removeFromBasket(slug) {
  const basket = getBasket();
  basket.items = basket.items.filter(item => item.slug !== slug);
  saveBasket(basket);
  updateBasketUI();
  if (document.getElementById('basket-wrapper')) {
    refreshBasketTable();
  }
}

export function updateQuantity(slug, quantity) {
  const basket = getBasket();
  const item = basket.items.find(item => item.slug === slug);
  if (item) {
    item.quantity = Math.max(1, parseInt(quantity) || 1);
    saveBasket(basket);
    updateBasketUI();
  }
  if (document.getElementById('basket-wrapper')) {
    refreshBasketTable();
  }
}

export function clearBasket() {
  localStorage.removeItem(BASKET_KEY);
  updateBasketUI();
}

// ---------------------------------------------------------------------------
// Snapshot handling
// ---------------------------------------------------------------------------
function now() {
  return Date.now();
}

function getLang() {
  return window.DEFAULT_LANGUAGE || document.documentElement.lang || 'uk';
}

function getSnapshotsMap() {
  const basket = getBasket();
  return basket.snapshots || {};
}

function saveSnapshotsMap(map) {
  const basket = getBasket();
  basket.snapshots = map;
  saveBasket(basket);
}

async function fetchAndCacheSnapshot(slug, force = false) {
  console.log('fetchAndCacheSnapshot called for', slug, 'force:', force);
  const lang = getLang();
  console.log('Language:', lang);
  const url = `/api/basket/snapshots/?slugs=${encodeURIComponent(slug)}&lang=${encodeURIComponent(lang)}`;
  try {
    const res = await fetch(url);
    console.log('Fetch response status:', res.status);
    if (!res.ok) return;
    const data = await res.json();
    console.log('Received data:', data);
    const snapshots = data.snapshots || [];
    if (snapshots.length > 0) {
      const snapshot = snapshots[0];
      const map = getSnapshotsMap();
      if (!map[slug]) map[slug] = {};
      map[slug][lang] = { snapshot, ts: now() };
      saveSnapshotsMap(map);
      console.log('Snapshot saved for', slug, snapshot);
      updateBasketUI();
    }
  } catch (e) {
    console.warn("Failed to fetch basket snapshot", slug, e);
  }
}

// ---------------------------------------------------------------------------
// Header widget
// ---------------------------------------------------------------------------
export function updateBasketUI() {
  console.log('updateBasketUI called');
  const basket = getBasket();
  const count = basket.items.length;

  const badge = document.querySelector('.basket-badge');
  if (badge) {
    badge.textContent = count;
    badge.style.display = count > 0 ? '' : 'none';
  }
  const total = calculateBasketTotal(basket);
  console.log('Total to display:', total);
  const totalEl = document.querySelector('.basket-total');
  if (totalEl) {
    const total = calculateBasketTotal(basket);
    totalEl.textContent = total.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' ' + CURRENCY;
  }

  const link = document.querySelector('.basket-link');
  if (link) {
    if (count === 0) {
      link.classList.add('disabled');
      link.removeAttribute('href');
    } else {
      link.classList.remove('disabled');
      link.setAttribute('href', '/basket/');
    }
  }
}

function refreshSnapshotsForCurrentLanguage() {
  const basket = getBasket();
  const lang = getLang();
  const slugs = basket.items.map(item => item.slug);
  slugs.forEach(slug => {
    const snap = basket.snapshots?.[slug]?.[lang];
    // если снепшота нет или он старше 24 часов (можно взять константу)
    if (!snap || (now() - snap.ts) > 24 * 60 * 60 * 1000) {
      fetchAndCacheSnapshot(slug, false); // не принудительно, но загрузит, если нет
    }
  });
}

function calculateBasketTotal(basket) {
  const lang = getLang();
  console.log('Calculating total, lang:', lang, 'basket:', basket);
  let total = 0;
  basket.items.forEach(item => {
    const snap = basket.snapshots?.[item.slug]?.[lang];
    console.log('Item:', item.slug, 'snap:', snap);
    if (snap?.snapshot?.price?.amount) {
      total += snap.snapshot.price.amount * item.quantity;
    }
  });
  console.log('Total:', total);
  return total;
}

// ---------------------------------------------------------------------------
// Event handlers
// ---------------------------------------------------------------------------
function setupBasketEvents() {
  document.body.addEventListener('click', function(e) {
    const removeBtn = e.target.closest('.basket-remove');
    if (removeBtn) {
      e.preventDefault();
      const slug = removeBtn.dataset.slug;
      removeFromBasket(slug);
      refreshBasketTable();
      return;
    }

    const addBtn = e.target.closest('.add-to-basket');
    if (addBtn) {
      e.preventDefault();
      const slug = addBtn.dataset.productSlug;
      if (slug) addToBasket(slug, 1);
    }
  });

  document.body.addEventListener('change', function (e) {
    const input = e.target.closest('.basket-qty');
    if (input) {
      console.log('Change event on .basket-qty');
      const slug = input.dataset.slug;
      const qty = parseInt(input.value) || 1;
      updateQuantity(slug, qty);
    }
  });
}

// ---------------------------------------------------------------------------
// HTMX integration
// ---------------------------------------------------------------------------
document.body.addEventListener('htmx:afterSwap', function(evt) {
  if (evt.detail.target.id === 'basket-wrapper') {
    updateBasketUI();
  }
});

function refreshBasketTable() {
  const wrapper = document.getElementById('basket-wrapper');
  if (!wrapper) return;
  const basket = getBasket();
  const items = basket.items.map(item => ({ slug: item.slug, quantity: item.quantity }));
  const itemsJson = JSON.stringify(items);
  const lang = getLang();
  const url = '/api/basket/table/?lang=' + lang + '&items=' + encodeURIComponent(itemsJson);
  htmx.ajax('GET', url, {
    target: '#basket-wrapper',
    swap: 'innerHTML'
  });
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    setupBasketEvents();
    updateBasketUI();
    refreshSnapshotsForCurrentLanguage();
  });
} else {
  setupBasketEvents();
  updateBasketUI();
  refreshSnapshotsForCurrentLanguage();
}