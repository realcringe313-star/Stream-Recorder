#!/usr/bin/env node
/**
 * Generate Gofile's dynamic X-Website-Token (`wt`) using Gofile's public
 * /js/wt.obf.js script and an active account/guest token.
 *
 * Usage: node scripts/gofile-wt.mjs <token> <wt_obf_js_path>
 */
import fs from 'node:fs';
import vm from 'node:vm';

const [, , token, wtJsPath] = process.argv;

if (!token || !wtJsPath) {
  process.exit(2);
}

try {
  const code = fs.readFileSync(wtJsPath, 'utf8');
  if (!code || !code.includes('generateWT')) {
    process.exit(3);
  }

  // wt.obf.js expects browser globals (window, globalThis, document, navigator).
  const sandbox = {
    window: {},
    globalThis: {},
    document: { createElement: () => ({}) },
    navigator: { userAgent: 'Mozilla/5.0' },
    crypto: globalThis.crypto,
    TextEncoder,
    TextDecoder,
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(code, sandbox, { timeout: 2000 });

  if (typeof sandbox.generateWT !== 'function') {
    process.exit(4);
  }

  const wt = sandbox.generateWT(token);
  if (!wt || typeof wt !== 'string') {
    process.exit(5);
  }

  process.stdout.write(wt);
} catch {
  process.exit(1);
}
