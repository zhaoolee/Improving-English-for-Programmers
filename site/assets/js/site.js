(() => {
  const input = document.querySelector('[data-card-search]');
  const grid = document.querySelector('[data-card-grid]');
  if (!input || !grid) return;

  const cards = [...grid.querySelectorAll('[data-card-id]')];
  const count = document.querySelector('[data-visible-count]');
  const empty = document.querySelector('[data-empty-state]');

  const filter = () => {
    const query = input.value.trim().toLocaleLowerCase();
    let visible = 0;
    cards.forEach((card) => {
      const match = !query || card.dataset.search.includes(query);
      card.hidden = !match;
      if (match) visible += 1;
    });
    if (count) count.textContent = String(visible);
    if (empty) empty.hidden = visible !== 0;
  };

  input.addEventListener('input', filter);
  input.addEventListener('search', filter);
})();
