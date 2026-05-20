// This is free and unencumbered software released into the public domain.
// See the UNLICENSE file for details.

// Fetches smelt.json and dynamically adds Binary/Source smelt result columns
// to the status table. Rows with failures show a clickable log modal.

(async function () {
  const ansiUpScript = document.createElement('script');
  ansiUpScript.src = 'https://cdn.jsdelivr.net/npm/ansi_up@6/ansi_up.js';
  document.head.appendChild(ansiUpScript);

  let data;
  try {
    const resp = await fetch('smelt.json');
    if (!resp.ok) return;
    data = await resp.json();
  } catch {
    return;
  }

  const components = data.components || {};

  const modal = document.createElement('div');
  modal.id = 'log-modal';
  modal.innerHTML =
    '<div id="log-backdrop"></div>' +
    '<div id="log-box">' +
      '<div id="log-header">' +
        '<span id="log-title"></span>' +
        '<button id="log-close">×</button>' +
      '</div>' +
      '<pre id="log-content"></pre>' +
    '</div>';
  document.body.appendChild(modal);

  const style = document.createElement('style');
  style.textContent =
    '#log-modal{display:none;position:fixed;inset:0;z-index:9999;align-items:center;justify-content:center}' +
    '#log-modal.open{display:flex}' +
    '#log-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.6)}' +
    '#log-box{position:relative;z-index:1;background:#1a1a1a;border-radius:6px;max-width:90vw;width:900px;max-height:85vh;display:flex;flex-direction:column;box-shadow:0 12px 40px rgba(0,0,0,.7);overflow:hidden}' +
    '#log-header{display:flex;align-items:center;gap:.5em;padding:.5em .75em;background:#2a2a2a;border-bottom:1px solid #444}' +
    '#log-title{flex:1;font-family:monospace;font-size:.9em;color:#e0e0e0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
    '#log-close{background:none;border:none;color:#888;font-size:1.4em;line-height:1;cursor:pointer;padding:0 .15em;flex-shrink:0}' +
    '#log-close:hover{color:#fff}' +
    '#log-content{margin:0;padding:1em;overflow:auto;font-family:monospace;font-size:.82em;line-height:1.5;color:#ccc;flex:1}' +
    'td.smelt-pass{background:#2a4a2a;color:#80ff80;text-align:center}' +
    'td.smelt-fail{background:#4a2a2a;color:#ff8080;text-align:center;cursor:pointer;text-decoration:underline dotted;text-underline-offset:2px}' +
    'td.smelt-fail:hover{filter:brightness(1.3)}' +
    'td.smelt-skip{background:#3a3a2a;color:#c0c080;text-align:center}' +
    'td.smelt-none{text-align:center}';
  document.head.appendChild(style);

  const headerRow = document.querySelector('table.sortable tr:first-child');
  if (!headerRow) return;
  ['Binary', 'Source'].forEach(function (label) {
    const th = document.createElement('th');
    th.textContent = label;
    headerRow.appendChild(th);
  });

  document.querySelectorAll('table.sortable tr[data-ga]').forEach(function (row) {
    const ga = row.dataset.ga;
    const comp = components[ga];
    [['binary_test', 'binary_log'], ['source_build', 'source_log']].forEach(function (pair) {
      const field = pair[0];
      const logField = pair[1];
      const td = document.createElement('td');
      if (!comp) {
        td.className = 'smelt-none';
        td.textContent = '—';
      } else {
        const val = comp[field];
        const log = comp[logField];
        if (val === 'pass') {
          td.className = 'smelt-pass';
          td.textContent = '✓';
        } else if (val === 'fail') {
          td.className = 'smelt-fail';
          td.textContent = '✗';
          if (log) { td.dataset.log = log; }
          td.dataset.ga = ga;
          td.dataset.field = field;
        } else if (val === 'skipped') {
          td.className = 'smelt-skip';
          td.textContent = '⟳';
          td.title = comp.skipped_reason || 'skipped';
        } else {
          td.className = 'smelt-none';
          td.textContent = '—';
        }
      }
      row.appendChild(td);
    });
  });

  await new Promise(function (resolve) {
    if (window.AnsiUp) { resolve(); return; }
    ansiUpScript.onload = resolve;
    ansiUpScript.onerror = resolve;
  });

  const logModal = document.getElementById('log-modal');
  const logTitle = document.getElementById('log-title');
  const logContent = document.getElementById('log-content');
  const logClose = document.getElementById('log-close');
  const logBackdrop = document.getElementById('log-backdrop');

  function closeModal() {
    logModal.classList.remove('open');
  }

  logClose.addEventListener('click', closeModal);
  logBackdrop.addEventListener('click', closeModal);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeModal();
  });

  document.querySelectorAll('td.smelt-fail[data-log]').forEach(function (td) {
    td.addEventListener('click', function () {
      const label = td.dataset.field === 'binary_test' ? 'binary test' : 'source build';
      logTitle.textContent = td.dataset.ga + ' — ' + label;
      if (window.AnsiUp) {
        const au = new AnsiUp();
        au.use_classes = false;
        logContent.innerHTML = au.ansi_to_html(td.dataset.log);
      } else {
        logContent.textContent = td.dataset.log;
      }
      logModal.classList.add('open');
    });
  });
})();
