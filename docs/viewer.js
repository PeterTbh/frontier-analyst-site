'use strict';
// Frontier Analyst viewer. Decrypts everything locally with WebCrypto.
// The passphrase is never stored, never put in a URL and never sent anywhere.

const enc = new TextEncoder();
const $ = (id) => document.getElementById(id);
const b64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
const state = { site: null, priv: null, manifest: null, current: null };

// Must match normalize_password() in scripts/fa_crypto.py
function normalizePassword(pw) {
  return pw.normalize('NFKC').trim().toLowerCase().replace(/[\s\-_]+/g, '-');
}

async function getJSON(path) {
  const r = await fetch(path, { cache: 'no-store' });
  if (!r.ok) throw new Error('fetch ' + path + ' ' + r.status);
  return r.json();
}

async function unlock(password) {
  const s = state.site;
  const base = await crypto.subtle.importKey('raw', enc.encode(normalizePassword(password)), 'PBKDF2', false, ['deriveKey']);
  const kek = await crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt: b64(s.kdf.salt), iterations: s.kdf.iterations, hash: 'SHA-256' },
    base, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
  const pkcs8 = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: b64(s.private_key.iv), additionalData: enc.encode(s.private_key.aad) },
    kek, b64(s.private_key.ct));
  state.priv = await crypto.subtle.importKey('pkcs8', pkcs8, { name: 'RSA-OAEP', hash: 'SHA-256' }, false, ['decrypt']);
}

async function openEnvelope(path) {
  const env = await getJSON(path);
  const raw = await crypto.subtle.decrypt({ name: 'RSA-OAEP' }, state.priv, b64(env.ek));
  const key = await crypto.subtle.importKey('raw', raw, 'AES-GCM', false, ['decrypt']);
  const pt = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: b64(env.iv), additionalData: enc.encode(env.type) }, key, b64(env.ct));
  return { type: env.type, bytes: new Uint8Array(pt) };
}

function esc(t) {
  return String(t).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function fmtDate(iso) {
  const d = new Date(iso + 'T12:00:00Z');
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

function show(which) {
  for (const id of ['gate', 'archive', 'reader']) $(id).hidden = id !== which;
  $('lock').hidden = which === 'gate';
}

function renderArchive() {
  const issues = [...state.manifest.issues].sort((a, b) => b.number - a.number);
  const rows = issues.map((i) => `
    <li class="row">
      <a href="#/issue/${esc(i.id)}">
        <span class="row__no">No. ${esc(i.number)}</span>
        <span class="row__date">${esc(fmtDate(i.date))}</span>
        <span class="row__title">${esc(i.title)}</span>
        <span class="row__lead">${esc(i.lead || '')}</span>
        <span class="row__go" aria-hidden="true">Read &rarr;</span>
      </a>
    </li>`).join('');
  $('archive').innerHTML = `
    <p class="label">Archive</p>
    <h1 class="archive__title">${issues.length} issue${issues.length === 1 ? '' : 's'}</h1>
    <ol class="rows">${rows || '<li class="row row--empty">No issues yet.</li>'}</ol>`;
  show('archive');
  document.title = 'Frontier Analyst';
}

async function renderIssue(id) {
  const meta = state.manifest.issues.find((i) => i.id === id);
  if (!meta) return renderArchive();
  state.current = meta;
  show('reader');
  const frame = $('issue');
  frame.srcdoc = '<p style="font:14px Inter,sans-serif;color:#6b6a66;padding:2rem">Decrypting…</p>';
  const doc = await openEnvelope(meta.html);
  frame.onload = () => {
    const h = frame.contentDocument && frame.contentDocument.documentElement.scrollHeight;
    if (h) frame.style.height = h + 40 + 'px';
  };
  frame.srcdoc = new TextDecoder().decode(doc.bytes);
  $('pdf').hidden = !meta.pdf;
  document.title = `No. ${meta.number} · Frontier Analyst`;
  window.scrollTo(0, 0);
}

async function route() {
  if (!state.priv) return show('gate');
  const m = location.hash.match(/^#\/issue\/([\w-]+)$/);
  try {
    if (m) await renderIssue(m[1]); else renderArchive();
  } catch (e) {
    console.error(e);
    $('archive').innerHTML = '<p class="gate__msg">This issue could not be decrypted.</p>';
    show('archive');
  }
}

async function onUnlock(ev) {
  ev.preventDefault();
  const pw = $('pw').value;
  $('msg').textContent = 'Checking…';
  $('go').disabled = true;
  try {
    await unlock(pw);
    const m = await openEnvelope('data/manifest.enc');
    state.manifest = JSON.parse(new TextDecoder().decode(m.bytes));
    $('msg').textContent = '';
    $('pw').value = '';
    await route();
  } catch (e) {
    state.priv = null;
    $('msg').textContent = 'That passphrase did not work.';
  } finally {
    $('go').disabled = false;
  }
}

async function onPdf() {
  const meta = state.current;
  if (!meta || !meta.pdf) return;
  const btn = $('pdf');
  btn.disabled = true;
  btn.textContent = 'Decrypting…';
  try {
    const f = await openEnvelope(meta.pdf);
    const url = URL.createObjectURL(new Blob([f.bytes], { type: 'application/pdf' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `frontier-analyst-no-${meta.number}-${meta.date}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Download PDF';
  }
}

function lock() {
  state.priv = null;
  state.manifest = null;
  $('issue').srcdoc = '';
  location.hash = '#/';
  show('gate');
}

document.addEventListener('DOMContentLoaded', async () => {
  try {
    state.site = await getJSON('site.json');
    if (state.site.display && state.site.display.motif === 'none') document.body.classList.add('no-motif');
  } catch (e) {
    $('msg').textContent = 'This site is not set up yet.';
    $('go').disabled = true;
  }
  $('unlock').addEventListener('submit', onUnlock);
  $('pdf').addEventListener('click', onPdf);
  $('lock').addEventListener('click', lock);
  window.addEventListener('hashchange', route);
  show('gate');
});
