(() => {
  'use strict';
  const normalize = text => String(text || '').normalize('NFKC').toLocaleLowerCase();
  const matches = (text, query) => normalize(query).trim().split(/\s+/).every(word => normalize(text).includes(word));

  const seriesForm = document.querySelector('#series-search');
  if (seriesForm) {
    const input = seriesForm.querySelector('input');
    const cards = Array.from(document.querySelectorAll('#collections .collection-card'));
    const empty = document.querySelector('#series-empty');
    const filter = () => {
      let visible = 0;
      cards.forEach(card => {
        card.hidden = !matches(card.textContent, input.value);
        if (!card.hidden) visible++;
      });
      empty.hidden = visible !== 0;
    };
    seriesForm.addEventListener('submit', event => { event.preventDefault(); filter(); });
    input.addEventListener('input', filter);
  }

  const galleryFilter = document.querySelector('#gallery-filter');
  const count = document.querySelector('[data-visible-count]');
  if (galleryFilter && count) {
    galleryFilter.addEventListener('input', () => {
      count.textContent = String(document.querySelectorAll('#image-grid .image-card:not([hidden])').length);
    });
  }
})();
