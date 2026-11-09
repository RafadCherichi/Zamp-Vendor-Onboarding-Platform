export function focusCaseQueue() {
  window.requestAnimationFrame(() => {
    document.querySelector<HTMLElement>('[data-case-queue]')?.scrollIntoView({
      block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
    });
  });
}
