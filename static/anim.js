// 导言展开/折叠动画
document.querySelectorAll('.dynasty-label').forEach(label => {
    const wrapper = label.parentElement;
    const content = wrapper.querySelector('.dynasty-intro');
    if (!content) return;

    label.addEventListener('click', () => {
        const isOpen = wrapper.classList.toggle('open');

        if (isOpen) {
            content.style.maxHeight = content.scrollHeight + 'px';
            content.style.opacity = '1';
            content.addEventListener('transitionend', function cleanup() {
                content.style.maxHeight = 'none';
                content.removeEventListener('transitionend', cleanup);
            });
        } else {
            content.style.maxHeight = content.scrollHeight + 'px';
            content.getBoundingClientRect();
            content.style.maxHeight = '0';
            content.style.opacity = '0';
        }
    });
});
