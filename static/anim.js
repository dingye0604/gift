// 平滑展开/折叠 <details> 导言
document.querySelectorAll('.dynasty-intro-toggle').forEach(details => {
    const summary = details.querySelector('.dynasty-label');
    const content = details.querySelector('.dynasty-intro');
    if (!summary || !content) return;

    // CSS transition 仅处理 open 方向的动画
    // close 方向由 JS 拦截，保持 content 可见直到动画完成

    summary.addEventListener('click', e => {
        e.preventDefault();

        if (details.open) {
            close(details, content);
        } else {
            open(details, content);
        }
    });
});

function open(details, content) {
    details.open = true;

    // 先归零，下一帧展开（触发 transition）
    content.style.maxHeight = '0';
    content.style.opacity = '0';

    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            content.style.maxHeight = content.scrollHeight + 'px';
            content.style.opacity = '1';
        });
    });

    content.addEventListener('transitionend', function cleanup() {
        content.style.maxHeight = 'none';
        content.removeEventListener('transitionend', cleanup);
    });
}

function close(details, content) {
    // 锁定当前高度
    content.style.maxHeight = content.scrollHeight + 'px';
    content.style.opacity = '1';

    // 强制回流后归零
    content.getBoundingClientRect();

    content.addEventListener('transitionend', function cleanup() {
        details.open = false;
        content.removeEventListener('transitionend', cleanup);
    });

    content.style.maxHeight = '0';
    content.style.opacity = '0';
}
