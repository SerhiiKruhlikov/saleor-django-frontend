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
    loadBasketTable();
  }
}

export function removeFromBasket(slug) {
  const basket = getBasket();
  basket.items = basket.items.filter(item => item.slug !== slug);
  saveBasket(basket);
  updateBasketUI();
  if (document.getElementById('basket-wrapper')) {
    loadBasketTable();
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
    loadBasketTable();
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
  const lang = getLang();
  const url = `/api/basket/snapshots/?slugs=${encodeURIComponent(slug)}&lang=${encodeURIComponent(lang)}`;
  try {
    const res = await fetch(url);
    if (!res.ok) return;
    const data = await res.json();
    const snapshots = data.snapshots || [];
    if (snapshots.length > 0) {
      const snapshot = snapshots[0];
      const map = getSnapshotsMap();
      if (!map[slug]) map[slug] = {};
      map[slug][lang] = { snapshot, ts: now() };
      saveSnapshotsMap(map);
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
  const basket = getBasket();
  const count = basket.items.length;

  const badge = document.querySelector('.basket-badge');
  if (badge) {
    badge.textContent = count;
    badge.style.display = count > 0 ? '' : 'none';
  }
  const total = calculateBasketTotal(basket);
  const totalEl = document.querySelector('.basket-total');
  if (totalEl) {
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

function updateBasketTotalFromDOM() {
  let subtotal = 0;
  document.querySelectorAll('.basket-item').forEach(row => {
    const priceEl = row.querySelector('.basket-item-new-price, .basket-item-price');
    if (!priceEl) return;
    const unitPrice = parseFloat(priceEl.dataset.unitPrice) || 0;
    const qtyInput = row.querySelector('.basket-qty');
    const qty = qtyInput ? parseInt(qtyInput.value) || 1 : 1;
    subtotal += unitPrice * qty;
  });
  const subtotalEl = document.getElementById('basket-subtotal');
  if (subtotalEl) {
    subtotalEl.textContent = subtotal.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }
  const totalEl = document.getElementById('basket-total');
  if (totalEl) {
    totalEl.textContent = subtotal.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }
  const totalHeaderEl = document.querySelector('.basket-total');
  if (totalHeaderEl) {
    totalHeaderEl.textContent = subtotal.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' ' + CURRENCY;
  }
}

function refreshSnapshotsForCurrentLanguage(force = false) {
  const basket = getBasket();
  const lang = getLang();
  const allSlugs = [
    ...basket.items.map(item => item.slug),
    ...basket.unavailableItems.map(item => item.slug)
  ];
  const uniqueSlugs = [...new Set(allSlugs)];
  const promises = [];
  uniqueSlugs.forEach(slug => {
    const snap = basket.snapshots?.[slug]?.[lang];
    if (force || !snap) {
      promises.push(fetchAndCacheSnapshot(slug, true));
    }
  });
  return Promise.all(promises);
}

function calculateBasketTotal(basket) {
  const lang = getLang();
  let total = 0;
  basket.items.forEach(item => {
    const snap = basket.snapshots?.[item.slug]?.[lang];
    if (snap?.snapshot?.price?.amount) {
      total += snap.snapshot.price.amount * item.quantity;
    }
  });
  return total;
}

function syncBasketWithSnapshots() {
  const basket = getBasket();
  const lang = getLang();
  let changed = false;

  const newItems = [];
  const newUnavailable = [];
  const itemsSlugs = new Set(basket.items.map(i => i.slug));
  const unavailableSlugs = new Set(basket.unavailableItems.map(i => i.slug));

  basket.items.forEach(item => {
    const snap = basket.snapshots?.[item.slug]?.[lang]?.snapshot;
    if (snap && snap.available_for_purchase === true) {
      newItems.push(item);
    } else {
      if (!unavailableSlugs.has(item.slug)) {
        basket.unavailableItems.push(item);
        changed = true;
      }
      if (basket.snapshots && basket.snapshots[item.slug]) {
        delete basket.snapshots[item.slug][lang];
        if (Object.keys(basket.snapshots[item.slug]).length === 0) {
          delete basket.snapshots[item.slug];
        }
      }
      changed = true;
    }
  });

  basket.unavailableItems.forEach(item => {
    const snap = basket.snapshots?.[item.slug]?.[lang]?.snapshot;
    if (snap && snap.available_for_purchase === true) {
      if (!itemsSlugs.has(item.slug)) {
        newItems.push(item);
        changed = true;
      }
    } else {
      newUnavailable.push(item);
    }
  });

  basket.items = newItems;
  basket.unavailableItems = newUnavailable;

  if (changed) {
    saveBasket(basket);
    updateBasketUI();
  }
}

// ---------------------------------------------------------------------------
// HTMX integration
// ---------------------------------------------------------------------------
document.body.addEventListener('htmx:afterSwap', function(evt) {
  if (evt.detail.target.id === 'basket-wrapper') {
    updateBasketTotalFromDOM();
    const count = document.querySelectorAll('.basket-item').length;
    const badge = document.querySelector('.basket-badge');
    if (badge) {
      badge.textContent = count;
      badge.style.display = count > 0 ? '' : 'none';
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
});

function loadBasketTable() {
  const wrapper = document.getElementById('basket-wrapper');
  if (!wrapper) return;
  const basket = getBasket();
  const items = basket.items.map(item => ({ slug: item.slug, quantity: item.quantity }));
  const itemsJson = JSON.stringify(items);
  const unavailableSlugs = basket.unavailableItems.map(item => item.slug);
  const unavailableJson = JSON.stringify(unavailableSlugs);
  const lang = getLang();
  const url = '/api/basket/table/?lang=' + lang + '&items=' + encodeURIComponent(itemsJson) + '&unavailable=' + encodeURIComponent(unavailableJson);
  htmx.ajax('GET', url, {
    target: '#basket-wrapper',
    swap: 'innerHTML'
  });
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
      loadBasketTable();
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
      const slug = input.dataset.slug;
      const qty = parseInt(input.value) || 1;
      updateQuantity(slug, qty);
    }
  });
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
function initBasket() {
  setupBasketEvents();
  updateBasketUI();

  // 1. Синхронизация по локальным данным
  syncBasketWithSnapshots();

  // 2. Фоновое обновление снепшотов
  refreshSnapshotsForCurrentLanguage(true).then(() => {
    syncBasketWithSnapshots();
    // 3. Загрузка таблицы после синхронизации
    loadBasketTable();
  });

  // Если запросы затянулись, но таблица уже должна показаться,
  // можно сразу загрузить таблицу, а потом обновить.
  // Но для надёжности делаем после обновления снепшотов.
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initBasket);
} else {
  initBasket();
}