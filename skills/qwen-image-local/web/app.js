const $ = id => document.getElementById(id);
let token = '', busy = false, connected = false, lastImage = '';
const time = seconds => `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
function error(message) { $('error').textContent = message || ''; $('error').hidden = !message; }
function render(status) {
  token = status.token;
  connected = status.ready;
  $('model-root').textContent = status.root;
  $('connection').textContent = status.ready ? 'Local model connected' : `Model not ready: ${status.problem}`;
  const job = status.job;
  busy = job?.state === 'running';
  $('generate').disabled = !connected || busy;
  $('generate').textContent = busy ? 'Generating…' : 'Generate image →';
  $('progress').hidden = !busy;
  if (!job) return;
  $('elapsed').textContent = job.elapsed_seconds !== undefined ? time(job.elapsed_seconds) : '';
  if (busy) { $('activity').textContent = 'Generating on your GPU…'; error(''); }
  if (job.state === 'done') {
    $('activity').textContent = 'Image saved. Ready for another.';
    $('result-info').textContent = `${job.width} × ${job.height} · ${job.steps} steps · seed ${job.seed}`;
    if (lastImage !== job.image) {
      const image = $('image');
      image.onload = () => { $('empty').hidden = true; image.hidden = false; };
      image.onerror = () => error('The image could not be loaded. Refresh the page to retry.');
      image.src = job.image;
      lastImage = job.image;
    }
    $('download').href = job.image;
    $('download').hidden = false;
  }
  if (job.state === 'error') { $('activity').textContent = 'Generation failed.'; error(job.error); }
}
async function poll() {
  try {
    const response = await fetch('/api/status');
    if (!response.ok) throw new Error('Could not read server status.');
    render(await response.json());
  } catch {
    connected = false;
    $('generate').disabled = true;
    $('connection').textContent = 'Server disconnected. Keep the launcher open, then refresh this page.';
  } finally { setTimeout(poll, 1500); }
}
$('generate-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (busy || !connected) return;
  busy = true;
  $('generate').disabled = true;
  error('');
  const [width, height] = $('size').value.split('x').map(Number);
  try {
    const response = await fetch('/api/generate', {method:'POST', headers:{'Content-Type':'application/json','X-Qwen-Token':token},
      body:JSON.stringify({prompt:$('prompt').value,width,height,steps:Number($('steps').value),seed:Number($('seed').value)})});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Generation request failed.');
    $('activity').textContent = 'Starting the local model…';
    $('progress').hidden = false;
  } catch (failure) { busy = false; $('generate').disabled = !connected; error(failure.message); }
});
poll();
