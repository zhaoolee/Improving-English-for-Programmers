(() => {
  'use strict';

  const $ = (selector) => document.querySelector(selector);
  const normalize = (text) => String(text || '').normalize('NFKC').toLocaleLowerCase();
  const matches = (text, query) => normalize(query).trim().split(/\s+/).every((word) => normalize(text).includes(word));

  const sidebar = $('#sidebar');
  const menu = $('#menu-button');
  const backdrop = $('#nav-backdrop');
  const main = $('.site-main');
  const mobile = matchMedia('(max-width: 800px)');

  function closeMenu() {
    sidebar.classList.remove('is-open');
    menu.setAttribute('aria-expanded', 'false');
    backdrop.hidden = true;
    sidebar.inert = mobile.matches;
    main.inert = false;
    document.body.style.overflow = '';
  }

  closeMenu();
  mobile.addEventListener('change', closeMenu);
  menu.addEventListener('click', () => {
    if (menu.getAttribute('aria-expanded') === 'true') return closeMenu();
    sidebar.classList.add('is-open');
    sidebar.inert = false;
    menu.setAttribute('aria-expanded', 'true');
    backdrop.hidden = false;
    main.inert = true;
    document.body.style.overflow = 'hidden';
  });
  backdrop.addEventListener('click', closeMenu);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') {
      closeMenu();
      menu.focus();
    }
  });

  $('#category-filter').addEventListener('input', (event) => {
    let found = 0;
    document.querySelectorAll('[data-category-label]').forEach((item) => {
      item.hidden = !matches(item.dataset.categoryLabel, event.target.value);
      if (!item.hidden) found += 1;
    });
    $('#no-categories').hidden = found !== 0;
  });

  const seriesInput = $('[data-series-search]');
  if (seriesInput) {
    const filterSeries = () => {
      let found = 0;
      document.querySelectorAll('[data-series-card]').forEach((card) => {
        card.hidden = !matches(card.dataset.search, seriesInput.value);
        if (!card.hidden) found += 1;
      });
      $('[data-series-empty]').hidden = found !== 0;
    };
    seriesInput.addEventListener('input', filterSeries);
    $('#series-search').addEventListener('submit', (event) => {
      event.preventDefault();
      filterSeries();
    });
  }

  const cardInput = $('[data-card-search]');
  const cardGrid = $('[data-card-grid]');
  if (cardInput && cardGrid) {
    const cards = [...cardGrid.querySelectorAll('[data-card-id]')];
    const count = $('[data-visible-count]');
    const empty = $('[data-empty-state]');
    const filterCards = () => {
      let visible = 0;
      cards.forEach((card) => {
        card.hidden = !matches(card.dataset.search, cardInput.value);
        if (!card.hidden) visible += 1;
      });
      count.textContent = String(visible);
      empty.hidden = visible !== 0;
    };
    cardInput.addEventListener('input', filterCards);
    cardInput.addEventListener('search', filterCards);
  }

  const preview = $('#preview');
  let previewItems = [];
  let previewIndex = 0;

  function showPreview(index) {
    previewIndex = (index + previewItems.length) % previewItems.length;
    const item = previewItems[previewIndex];
    $('#preview-title').textContent = item.dataset.name;
    $('#preview-title').title = item.dataset.name;
    $('#preview-image').src = item.dataset.src;
    $('#preview-image').alt = item.dataset.name;
    $('#preview-download').href = item.dataset.src;
    $('#preview-download').download = item.dataset.filename;
    $('#preview-original').href = item.dataset.src;
    $('#preview-position').textContent = `${previewIndex + 1} / ${previewItems.length}`;
    $('#preview-prev').disabled = $('#preview-next').disabled = previewItems.length < 2;
  }

  document.addEventListener('click', (event) => {
    const link = event.target.closest('[data-preview]');
    if (!link || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    previewItems = [...document.querySelectorAll('[data-preview]')].filter((item) => !item.closest('[hidden]'));
    showPreview(previewItems.indexOf(link));
    preview.showModal();
  });
  $('#preview-close').addEventListener('click', () => preview.close());
  $('#preview-prev').addEventListener('click', () => showPreview(previewIndex - 1));
  $('#preview-next').addEventListener('click', () => showPreview(previewIndex + 1));
  preview.addEventListener('close', () => $('#preview-image').removeAttribute('src'));
  preview.addEventListener('click', (event) => {
    if (event.target !== preview) return;
    const bounds = preview.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) preview.close();
  });
  preview.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowLeft') showPreview(previewIndex - 1);
    if (event.key === 'ArrowRight') showPreview(previewIndex + 1);
  });
})();
