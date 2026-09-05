(() => {
    const note = document.querySelector('[data-random-reading-note]');
    if (!note) return;

    const candidates = [...note.querySelectorAll('.note-candidate')];
    const quote = note.querySelector('[data-note-quote]');
    const source = note.querySelector('[data-note-source]');
    if (!candidates.length || !quote || !source) return;

    const storageKey = 'gift-reading-note-last';
    let lastKey = null;
    try {
        lastKey = window.localStorage.getItem(storageKey);
    } catch {
        // 隐私模式或禁用存储时仍然保留随机抽取功能。
    }

    const pool = candidates.filter((candidate) => candidate.dataset.key !== lastKey);
    const available = pool.length ? pool : candidates;
    const randomIndex = (length) => {
        if (window.crypto && typeof window.crypto.getRandomValues === 'function') {
            const values = new Uint32Array(1);
            window.crypto.getRandomValues(values);
            return values[0] % length;
        }
        return Math.floor(Math.random() * length);
    };

    const selected = available[randomIndex(available.length)];
    const selectedQuote = selected.content.querySelector('.note-candidate-quote');
    if (!selectedQuote) return;

    quote.replaceChildren(...selectedQuote.cloneNode(true).childNodes);
    source.textContent = `《${selected.dataset.title}》`;
    try {
        window.localStorage.setItem(storageKey, selected.dataset.key);
    } catch {
        // 不影响当前页面的显示。
    }
})();
