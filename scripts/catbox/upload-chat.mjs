import fs from 'node:fs';
import path from 'node:path';

const file = process.argv[2] || '';
const maxBytes = 200 * 1024 * 1024;
const retries = Math.max(1, Number.parseInt(process.env.CATBOX_MAX_RETRIES || '3', 10));

async function main() {
  if (!file || !fs.existsSync(file) || fs.statSync(file).size <= 0) {
    console.error('Catbox chat upload rejected: missing or empty file');
    return 1;
  }
  if (fs.statSync(file).size > maxBytes) {
    console.error('Catbox chat upload rejected: file exceeds 200 MB');
    return 1;
  }

  const bytes = fs.readFileSync(file);
  let lastError = 'empty response';
  for (let attempt = 1; attempt <= retries; attempt += 1) {
    try {
      const form = new FormData();
      form.append('reqtype', 'fileupload');
      if (process.env.CATBOX_USERHASH) form.append('userhash', process.env.CATBOX_USERHASH);
      form.append('fileToUpload', new Blob([bytes], { type: 'application/json' }), path.basename(file));
      const response = await fetch('https://catbox.moe/user/api.php', {
        method: 'POST',
        body: form,
        headers: { 'User-Agent': 'Stream-Recorder Catbox chat archiver' },
        signal: AbortSignal.timeout(300000),
      });
      const body = (await response.text()).trim();
      if (response.ok && /^https:\/\/files\.catbox\.moe\/[A-Za-z0-9._-]+$/.test(body)) {
        console.log(body);
        return 0;
      }
      lastError = `HTTP ${response.status}: ${body.slice(0, 160)}`;
    } catch (error) {
      lastError = error?.message || String(error);
    }
    console.error(`Catbox chat upload failed (${attempt}/${retries}): ${lastError}`);
    if (attempt < retries) await new Promise(resolve => setTimeout(resolve, 5000));
  }
  return 1;
}

main().then(code => { process.exitCode = code; }).catch(error => {
  console.error(error?.message || String(error));
  process.exitCode = 1;
});
