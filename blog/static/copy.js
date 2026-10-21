function copyWithSelection(text) {
  const previousFocus = document.activeElement;
  const field = document.createElement('textarea');
  field.value = text;
  field.setAttribute('readonly', '');
  field.style.position = 'fixed';
  field.style.opacity = '0';
  document.body.append(field);
  try {
    field.select();
    return document.execCommand('copy');
  } finally {
    field.remove();
    previousFocus?.focus({ preventScroll: true });
  }
}

document.querySelectorAll('[data-copy-code]').forEach((button) => {
  button.hidden = false;
  let reset;
  button.addEventListener('click', async () => {
    clearTimeout(reset);
    const text = button.closest('.code-block').querySelector('code').textContent;
    button.disabled = true;
    try {
      try {
        if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(text);
      } catch {
        if (!copyWithSelection(text)) throw new Error('Copy failed');
      }
      button.textContent = 'Copied';
    } catch {
      button.textContent = 'Copy failed';
    } finally {
      button.disabled = false;
      reset = setTimeout(() => { button.textContent = 'Copy'; }, 1800);
    }
  });
});
