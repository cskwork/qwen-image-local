const $ = id => document.getElementById(id);
let token = '', busy = false, connected = false, referenceReady = false;
let history = [], selected = -1, completedId = null, referenceId = null, uploading = false;
const time = seconds => `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
function error(message) { $('error').textContent = message || ''; $('error').hidden = !message; }
function updateControls() {
  $('generate').disabled = !connected || busy || uploading;
  $('generate').textContent = busy ? 'Generating…' : uploading ? 'Attaching image…' : 'Generate image →';
  $('reference-file').disabled = !referenceReady || uploading;
  $('use-reference').disabled = !referenceReady || selected < 0;
}
function setReference(id, image) {
  referenceId = id;
  $('reference-preview').hidden = !id;
  if (id) $('reference-image').src = image;
  else { $('reference-image').removeAttribute('src'); $('reference-file').value = ''; }
}
function referenceURL(id) {
  return id.startsWith('image-') ? `/images/${id.slice(6)}.png` : `/references/${id}`;
}
function showVersion(index) {
  if (index < 0 || index >= history.length) return;
  selected = index;
  const item = history[index], image = $('image');
  image.onload = () => { $('empty').hidden = true; image.hidden = false; };
  image.onerror = () => error('This saved image could not be loaded. Check that it still exists on disk.');
  image.src = item.image;
  $('download').href = item.image;
  $('download').download = `qwen-${item.id}.png`;
  $('download').hidden = false;
  $('result-info').textContent = `${item.width} × ${item.height} · ${item.steps} steps · seed ${item.seed} · ${time(item.elapsed_seconds)}`;
  $('history-position').textContent = `${index + 1} / ${history.length} · newest first`;
  $('previous').disabled = index >= history.length - 1;
  $('next').disabled = index <= 0;
  $('reuse-prompt').disabled = false;
  [...$('history').children].forEach((button, i) => button.setAttribute('aria-pressed', String(i === index)));
  updateControls();
}
async function loadHistory(selectNewest = false) {
  const response = await fetch('/api/history');
  if (!response.ok) throw new Error('Could not load saved versions.');
  const result = await response.json(), previousId = history[selected]?.id;
  history = result.images;
  $('history').replaceChildren();
  history.forEach((item, index) => {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'thumbnail';
    button.setAttribute('aria-label', `View version ${history.length - index}`);
    button.setAttribute('aria-pressed', 'false');
    const image = document.createElement('img');
    image.src = item.image; image.alt = ''; image.loading = 'lazy';
    button.append(image, document.createTextNode(`v${history.length - index}`));
    button.addEventListener('click', () => showVersion(index));
    $('history').append(button);
  });
  if (history.length) {
    const oldIndex = history.findIndex(item => item.id === previousId);
    showVersion(selectNewest || oldIndex < 0 ? 0 : oldIndex);
  }
  if (result.warnings) $('selection-note').textContent = `${result.warnings} saved records could not be read. Their files were preserved.`;
}
async function render(status) {
  token = status.token;
  connected = status.ready;
  referenceReady = status.reference_ready;
  $('model-root').textContent = status.root;
  $('connection').textContent = status.ready ? 'Local model connected' : `Model not ready: ${status.problem}`;
  $('reference-help').textContent = referenceReady ? 'PNG or JPEG · up to 8MB · max 4096px per side. Stored only on this PC.' : 'Optional vision component missing. Open “Enable reference-image attachments” below.';
  const job = status.job;
  busy = job?.state === 'running';
  updateControls();
  $('progress').hidden = !busy;
  if (!job) return;
  $('elapsed').textContent = job.elapsed_seconds !== undefined ? time(job.elapsed_seconds) : '';
  if (busy) $('activity').textContent = 'Generating on your GPU… Earlier versions stay available below.';
  if (job.state === 'done') {
    $('activity').textContent = 'Image saved. Browse versions or refine your prompt.';
    if (completedId !== job.id) {
      await loadHistory(true);
      completedId = job.id;
    }
  }
  if (job.state === 'error') { $('activity').textContent = 'Generation failed. Earlier versions are unchanged.'; error(job.error); }
}
async function poll() {
  try {
    const response = await fetch('/api/status');
    if (!response.ok) throw new Error('Could not read server status.');
    await render(await response.json());
  } catch {
    connected = false;
    updateControls();
    $('connection').textContent = 'Server disconnected. Keep the launcher open, then refresh this page.';
  } finally { setTimeout(poll, 1500); }
}
$('previous').addEventListener('click', () => showVersion(selected + 1));
$('next').addEventListener('click', () => showVersion(selected - 1));
$('reuse-prompt').addEventListener('click', () => {
  const item = history[selected];
  if (!item) return;
  $('prompt').value = item.prompt;
  $('size').value = `${item.width}x${item.height}`;
  $('steps').value = String(item.steps);
  $('seed').value = item.seed;
  setReference(item.reference_id, item.reference_id ? referenceURL(item.reference_id) : null);
  $('selection-note').textContent = 'Prompt and settings restored. Revise them, then generate a new version.';
  $('prompt').focus();
});
$('use-reference').addEventListener('click', () => {
  const item = history[selected];
  if (!item) return;
  setReference('image-' + item.id, item.image);
  $('selection-note').textContent = 'Selected image attached. Describe what to keep or change in your prompt.';
  $('prompt').focus();
});
$('remove-reference').addEventListener('click', () => setReference(null));
$('reference-file').addEventListener('change', async () => {
  const file = $('reference-file').files[0];
  if (!file) return;
  if (file.size > 8 * 1024 * 1024) { error('Choose an image smaller than 8MB.'); $('reference-file').value = ''; return; }
  uploading = true; updateControls(); error('');
  try {
    const response = await fetch('/api/reference', {method:'POST',headers:{'Content-Type':'application/octet-stream','X-Qwen-Token':token},body:file});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Attachment failed.');
    setReference(result.id, result.image);
    $('selection-note').textContent = 'Reference attached. Add your instructions, then generate.';
  } catch (failure) { error(failure.message); $('reference-file').value = ''; }
  finally { uploading = false; updateControls(); }
});
$('generate-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (busy || !connected || uploading) return;
  busy = true; updateControls(); error('');
  const [width, height] = $('size').value.split('x').map(Number);
  try {
    const response = await fetch('/api/generate', {method:'POST', headers:{'Content-Type':'application/json','X-Qwen-Token':token},
      body:JSON.stringify({prompt:$('prompt').value,width,height,steps:Number($('steps').value),seed:Number($('seed').value),reference_id:referenceId})});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Generation request failed.');
    $('activity').textContent = 'Starting the local model…';
    $('progress').hidden = false;
  } catch (failure) { busy = false; updateControls(); error(failure.message); }
});
loadHistory().catch(failure => error(failure.message));
poll();
