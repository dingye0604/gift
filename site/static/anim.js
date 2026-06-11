// 平滑展开/折叠 <details> 元素
document.querySelectorAll('.dynasty-intro-toggle').forEach(details => {
    const content = details.querySelector('.dynasty-intro');
    if (!content) return;

    // 初始折叠动画尺寸
    content.style.overflow = 'hidden';
    content.style.maxHeight = '0';
    content.style.opacity = '0';
    content.style.transition = 'max-height 0.45s ease, opacity 0.35s ease, margin 0.45s ease';

    details.addEventListener('toggle', () => {
        if (details.open) {
            content.style.maxHeight = content.scrollHeight + 'px';
            content.style.opacity = '1';
        } else {
            content.style.maxHeight = content.scrollHeight + 'px';
            // 强制回流后归零
            requestAnimationFrame(() => {
                content.style.maxHeight = '0';
                content.style.opacity = '0';
            });
        }
    });
});

// 初始化：如果默认打开，展开到自然高度
document.querySelectorAll('.dynasty-intro-toggle[open]').forEach(details => {
    const content = details.querySelector('.dynasty-intro');
    if (content) {
        content.style.maxHeight = content.scrollHeight + 'px';
        content.style.opacity = '1';
    }
});
