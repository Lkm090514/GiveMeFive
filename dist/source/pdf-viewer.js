import {getDocument, GlobalWorkerOptions, PDFDataRangeTransport} from './pdfjs/pdf.mjs';
import {readRange} from './pdf-range.mjs';
GlobalWorkerOptions.workerSrc = new URL('./pdfjs/pdf.worker.mjs', import.meta.url).href;
const status = document.getElementById('status'), canvas = document.getElementById('page'), input = document.getElementById('page-number');
const previous = document.getElementById('previous'), next = document.getElementById('next');
let book, task, renderTask, generation = 0, loadedBytes = 0;
const controller = new AbortController(), parts = new Map();
function fail(error) {
  if (error.name === 'AbortError' || error.name === 'RenderingCancelledException') return;
  status.textContent = '这一页暂时无法打开，请检查网络后重试。';
  document.getElementById('retry').hidden = false;
}
async function loadPart(part) {
  if (!parts.has(part.path)) parts.set(part.path, (async () => {
    const response = await fetch(part.path, {signal: controller.signal});
    if (!response.ok) throw new Error('教材读取失败');
    const data = new Uint8Array(await response.arrayBuffer());
    if (data.length !== part.bytes) throw new Error('教材内容不完整');
    if (crypto.subtle) {
      const digest = await crypto.subtle.digest('SHA-256', data);
      const hash = Array.from(new Uint8Array(digest), n => n.toString(16).padStart(2, '0')).join('');
      if (hash !== part.sha256) throw new Error('教材校验失败');
    }
    loadedBytes += data.length;
    status.dataset.loadedBytes = loadedBytes;
    status.dataset.loadedParts = parts.size;
    return data;
  })());
  return parts.get(part.path);
}
async function showPage() {
  if (!book) return;
  const requested = Number(new URLSearchParams(location.hash.slice(1)).get('page')) || 1;
  const pageNumber = Math.max(1, Math.min(book.numPages, Math.trunc(requested)));
  const current = ++generation;
  renderTask?.cancel();
  input.value = pageNumber;
  previous.disabled = pageNumber === 1;
  next.disabled = pageNumber === book.numPages;
  status.textContent = `正在加载第 ${pageNumber} 页…`;
  canvas.hidden = true;
  try {
    const page = await book.getPage(pageNumber);
    if (current !== generation) return;
    const natural = page.getViewport({scale: 1});
    const scale = Math.min(document.getElementById('reader').clientWidth - 24, 1400) / natural.width;
    const viewport = page.getViewport({scale});
    const ratio = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.ceil(viewport.width * ratio);
    canvas.height = Math.ceil(viewport.height * ratio);
    canvas.style.width = `${viewport.width}px`;
    canvas.style.height = `${viewport.height}px`;
    canvas.setAttribute('aria-label', `原教材 PDF 第 ${pageNumber} 页`);
    renderTask = page.render({canvasContext: canvas.getContext('2d'), viewport, transform: [ratio, 0, 0, ratio, 0, 0]});
    await renderTask.promise;
    if (current !== generation) return;
    canvas.hidden = false;
    status.textContent = `第 ${pageNumber} / ${book.numPages} 页`;
    document.getElementById('reader').scrollTop = 0;
    document.getElementById('retry').hidden = true;
  } catch (error) { if (current === generation) fail(error); }
}
function goTo(number) { location.hash = `page=${Math.max(1, Math.min(book.numPages, number))}`; }
previous.addEventListener('click', () => goTo(Number(input.value) - 1));
next.addEventListener('click', () => goTo(Number(input.value) + 1));
document.getElementById('navigation').addEventListener('submit', event => { event.preventDefault(); if (book) goTo(Number(input.value) || 1); });
document.getElementById('retry').addEventListener('click', () => location.reload());
addEventListener('hashchange', showPage);
let resizeTimer;
addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(showPage, 200); });
addEventListener('pagehide', event => { if (!event.persisted) { controller.abort(); task?.destroy(); } });
try {
  const response = await fetch('pdf-parts.json', {signal: controller.signal});
  if (!response.ok) throw new Error('教材目录读取失败');
  const manifest = await response.json();
  class BookRange extends PDFDataRangeTransport {
    requestDataRange(begin, end) {
      readRange(manifest, begin, end, loadPart).then(bytes => this.onDataRange(begin, bytes)).catch(error => { fail(error); task?.destroy(); });
    }
    abort() { controller.abort(); }
  }
  task = getDocument({range: new BookRange(manifest.bytes, new Uint8Array(0), true), disableAutoFetch: true, disableStream: true, rangeChunkSize: 65536,
    cMapUrl: './pdfjs/cmaps/', cMapPacked: true, standardFontDataUrl: './pdfjs/standard_fonts/', wasmUrl: './pdfjs/wasm/'});
  book = await task.promise;
  input.max = book.numPages;
  document.getElementById('navigation').hidden = false;
  await showPage();
} catch (error) { fail(error); }
