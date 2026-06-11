// 导言展开/折叠动画
document.querySelectorAll('.dynasty-label').forEach(label => {
    const wrapper = label.parentElement;
    const content = wrapper.querySelector('.dynasty-intro');
    if (!content) return;

    // 初始折叠状态
    content.style.margin = '0';
    content.style.padding = '0 24px';

    label.addEventListener('click', () => {
        const isOpen = wrapper.classList.toggle('open');

        if (isOpen) {
            content.style.maxHeight = content.scrollHeight + 'px';
            content.style.opacity = '1';
            content.style.margin = '20px 0';
            content.style.padding = '16px 24px';
            content.addEventListener('transitionend', function cleanup() {
                content.style.maxHeight = 'none';
                content.removeEventListener('transitionend', cleanup);
            });
        } else {
            // 锁定当前状态，下一帧归零
            content.style.maxHeight = content.scrollHeight + 'px';
            content.getBoundingClientRect();
            content.style.maxHeight = '0';
            content.style.opacity = '0';
            content.style.margin = '0';
            content.style.padding = '0 24px';
        }
    });
});
