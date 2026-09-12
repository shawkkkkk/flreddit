'use strict';

(() => {
  const button = document.getElementById('copy-token-ca');
  const contract = document.getElementById('token-ca');
  if (!button || !contract) return;

  const reset = () => { button.textContent = 'COPY CA'; };

  button.addEventListener('click', async () => {
    const address = contract.textContent.trim();
    try {
      await navigator.clipboard.writeText(address);
      button.textContent = 'COPIED';
      window.setTimeout(reset, 1600);
    } catch (_error) {
      const range = document.createRange();
      range.selectNodeContents(contract);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      button.textContent = 'SELECTED';
      window.setTimeout(reset, 1600);
    }
  });
})();
