const steps = {
  skill: {
    command: "git clone https://github.com/cskwork/qwen-image-local.git\ncd qwen-image-local\n$skillRoot = Join-Path $HOME '.codex\\skills'\nNew-Item -ItemType Directory -Path $skillRoot -Force | Out-Null\nif (Test-Path (Join-Path $skillRoot 'qwen-image-local')) { throw 'Skill already exists' }\nCopy-Item -Recurse skills\\qwen-image-local $skillRoot",
    note: 'Codex 스킬 폴더에 복사합니다. 기존 스킬은 덮어쓰지 않습니다. 설치 후 새 채팅을 시작하세요.'
  },
  model: {
    command: 'python skills/qwen-image-local/scripts/qwen_local.py install\npython skills/qwen-image-local/scripts/qwen_local.py doctor --verify',
    note: '저장소 폴더에서 실행하세요. 약 11GB를 다운로드하고 파일을 검증합니다. 기본 저장 위치는 %LOCALAPPDATA%\\qwen-image-local입니다.'
  },
  generate: {
    command: "python skills/qwen-image-local/scripts/qwen_local.py generate --prompt 'A natural studio portrait of an adult model, soft light' --output outputs/portrait.png",
    note: '저장소 폴더에서 실행하세요. 이미지와 실행 기록이 outputs에 저장됩니다. 같은 이름의 파일이 있으면 다른 이름을 사용하세요.'
  }
};
const tabs = [...document.querySelectorAll('[role="tab"]')];
const code = document.querySelector('#command-code');
const note = document.querySelector('#command-note');
const status = document.querySelector('#copy-status');
function select(tab) {
  tabs.forEach(item => { const active = item === tab; item.setAttribute('aria-selected', String(active)); item.tabIndex = active ? 0 : -1; });
  code.textContent = steps[tab.dataset.step].command;
  note.textContent = steps[tab.dataset.step].note;
  document.querySelector('#command-panel').setAttribute('aria-labelledby', tab.id);
  status.textContent = '';
}
tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => select(tab));
  tab.addEventListener('keydown', event => {
    let next;
    if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
    if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = tabs.length - 1;
    if (next !== undefined) { event.preventDefault(); select(tabs[next]); tabs[next].focus(); }
  });
});
document.querySelector('#copy-command').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(code.textContent);
    status.textContent = '명령어를 복사했습니다.';
  } catch {
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(code);
    selection.removeAllRanges();
    selection.addRange(range);
    status.textContent = '자동 복사가 허용되지 않았습니다. 선택된 명령어를 직접 복사하세요.';
  }
});
