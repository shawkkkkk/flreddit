'use strict';

(() => {
  function narratorLabel(raw) {
    const value = String(raw || '');
    if (value.includes(':budget_fallback')) return 'LUNA · BUDGET FALLBACK';
    if (value.includes(':error_fallback')) return 'LUNA · ERROR FALLBACK';
    if (value.startsWith('openai_responses_v1:')) return 'LUNA · MODEL';
    if (value.startsWith('template_narrator_v1')) return 'TEMPLATE';
    return 'DISCLOSED NARRATOR';
  }

  function refreshLabels(root = document) {
    root.querySelectorAll('.provenance[title], .dialog-label[title]').forEach((element) => {
      element.textContent = `decision / kernel · words / ${narratorLabel(element.title)}`;
    });
  }

  const observer = new MutationObserver(() => refreshLabels());
  observer.observe(document.documentElement, { childList: true, subtree: true });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => refreshLabels(), { once: true });
  } else {
    refreshLabels();
  }
})();
