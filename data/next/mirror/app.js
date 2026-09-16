// Local presentation state only. No network calls, storage, forms or checkout integration.
const SOURCE_BASE = 'assets/example/';
const editions = [
  'Put the agent’s reach and your instructions in a record you can use in the next conversation.',
  'Inspect a company’s deployment through a consistent record of capabilities, mandate and gaps.',
  'Bring the stated mandate and its supporting evidence into the decision you are accountable for.',
  'Examine the grant, the evidence behind each capability and the barriers actually in place.',
  'Keep a versioned record you can cite and revisit when the deployment or mandate changes.'
];
const readers = [
  ['What am I asking the agent to do?', 'Start with the mandate, then place the agent instructions where the agent reads them.', 'MANDATE.md · AGENTS.md · SKILL.md'],
  ['What am I authorising?', 'Read the mandate alongside the authorisation document and the conditions that need an owner.', 'MANDATE.md · LICENCE-TO-OPERATE.md'],
  ['What is actually in the way?', 'Inspect the grant, the delta and the barrier on each capability. Check the underlying data and its validity.', 'GRANT.md · DELTA.md · data/validity.json']
];
let selectedLevel = 1;
function selectLevel(index, updateURL = true) {
  if (!Number.isInteger(index) || index < 0 || index >= LEVELS.length) return;
  selectedLevel = index;
  const product = LEVELS[index];
  document.querySelectorAll('[data-level]').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.level) === index)));
  const values = {
    'product-code': `ABP-T${index + 1}`,
    'spec-code': `ABP-T${index + 1}`,
    'product-name': product.name,
    'product-sub': product.sub,
    'buy-name': product.name,
    'buy-price': product.price,
    'buy-delivery': product.clock,
    'spec-delivery': product.clock,
    'buy-description': product.what
  };
  Object.entries(values).forEach(([id,value]) => { document.getElementById(id).textContent = value; });
  const image = document.getElementById('product-image');
  image.src = `assets/${product.image}`;
  image.alt = `${product.name} conceptual digital-product artwork`;
  const button = document.getElementById('buy-button');
  button.textContent = `Buy ${product.name} →`;
  const claim = document.getElementById('buy-claim');
  claim.href = `https://store.sgit.ai/ledger/#claim-${product.claim}`;
  claim.textContent = product.state + ' ↗';
  const deposit = document.getElementById('deposit');
  deposit.hidden = index < 2;
  deposit.textContent = index === 2 ? '£100 now · £400 on delivery' : index === 3 ? '£300 now · £1,200 on delivery' : '';
  document.getElementById('session-stamp').hidden = index !== 3;
  ['included','excluded'].forEach(name => {
    const list = document.getElementById(name);
    list.replaceChildren(...product[name].map(value => { const li = document.createElement('li'); li.textContent = value; return li; }));
  });
  if (updateURL) {
    const url = new URL(location.href);
    url.searchParams.set('level', String(index + 1));
    history.replaceState(null, '', url);
  }
}
function selectEdition(index) {
  if (!Number.isInteger(index) || index < 0 || index >= editions.length) return;
  document.querySelectorAll('[data-edition]').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.edition) === index)));
  document.querySelector('.edition-copy').textContent = editions[index];
}
document.addEventListener('click', event => {
  const button = event.target.closest('button');
  if (!button) return;
  if (button.hasAttribute('data-file')) {
    const file = VAULT_FILES[Number(button.dataset.file)];
    const explorer = button.closest('.vault-explorer');
    explorer.querySelectorAll('[data-file]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    explorer.querySelector('.file-category').textContent = file.category;
    explorer.querySelector('.file-title').textContent = file.title;
    explorer.querySelector('.file-text').textContent = file.text;
    explorer.querySelector('.file-name').textContent = file.name;
    explorer.querySelector('.file-source').href = file.path === 'index.html' ? 'example.html#reader' : SOURCE_BASE + file.path;
    return;
  }
  if (button.hasAttribute('data-reader')) {
    const demo = button.closest('.audience-demo');
    const reader = readers[Number(button.dataset.reader)];
    demo.querySelectorAll('[data-reader]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    demo.querySelector('.reader-title').textContent = reader[0];
    demo.querySelector('.reader-copy').textContent = reader[1];
    demo.querySelector('.reader-files').textContent = reader[2];
    return;
  }
  if (button.hasAttribute('data-level')) { selectLevel(Number(button.dataset.level)); return; }
  if (button.hasAttribute('data-edition')) { selectEdition(Number(button.dataset.edition)); return; }
  if (button.hasAttribute('data-product-media')) {
    const state = button.dataset.productMedia;
    document.querySelectorAll('[data-product-media]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    document.querySelector('.product-visual').hidden = state !== 'art';
    document.querySelector('.product-contents').hidden = state !== 'contents';
    document.querySelector('.product-empty').hidden = state !== 'screen';
    return;
  }
  if (button.id === 'buy-button') {
    document.getElementById('real-offer').href = `https://store.sgit.ai/d/t${selectedLevel + 1}/`;
    document.getElementById('buy-dialog').showModal();
    return;
  }
  if (button.classList.contains('close')) button.closest('dialog').close();
});
if (document.getElementById('product-preview')) {
  const params = new URLSearchParams(location.search);
  const level = Number(params.get('level') || 2) - 1;
  selectLevel(level >= 0 && level < 4 && Number.isInteger(level) ? level : 1, false);
  const audience = Number(params.get('audience') || 0);
  selectEdition(audience >= 0 && audience < 5 && Number.isInteger(audience) ? audience : 0);
}
