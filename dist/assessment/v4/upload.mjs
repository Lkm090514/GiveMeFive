export function validatePDF(files) {
  if (files.length !== 1) throw Error('每次请选择一份 PDF / DOCX 试卷。');
  const file = files[0];
  const docx=/\.docx$/i.test(file.name),pdf=/\.pdf$/i.test(file.name),types=['','application/octet-stream',docx?'application/vnd.openxmlformats-officedocument.wordprocessingml.document':'application/pdf'];if((!pdf&&!docx)||!types.includes(file.type))throw Error('仅支持 PDF / DOCX 文件，请重新选择。');
  if (!file.size) throw Error('文件为空，请选择完整的试卷。');
  if (file.size > 50 * 1024 * 1024) throw Error('试卷不能超过 50 MiB。');
  return file;
}

export function bindPDFPicker(form) {
  const input = form.elements.file, zone = form.querySelector('[data-pdf-drop]'), note = form.querySelector('[data-file-state]');
  let selected = null;
  function choose(files) {
    try {
      selected = validatePDF(files);
      form.dataset.requestKey = '';
      note.textContent = `${selected.name} · ${(selected.size / 1024 / 1024).toFixed(1)} MiB`;
      note.dataset.error = 'false';
    } catch (error) {
      selected = null;
      input.value = '';
      note.textContent = error.message;
      note.dataset.error = 'true';
    }
  }
  input.addEventListener('change', () => { if (input.files.length) choose(input.files); });
  for (const type of ['dragenter', 'dragover']) zone.addEventListener(type, e => {
    e.preventDefault(); zone.classList.add('dragging');
  });
  zone.addEventListener('dragleave', e => { if (!zone.contains(e.relatedTarget)) zone.classList.remove('dragging'); });
  zone.addEventListener('drop', e => { e.preventDefault(); zone.classList.remove('dragging'); choose(e.dataTransfer.files); });
  return () => {
    if (!selected) throw Error('请先拖入或选择一份 PDF / DOCX 试卷。');
    return selected;
  };
}

// XHR exposes actual upload progress; the existing backend owns parsing and retry.
export function uploadPDF(body, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/v4/papers/import');
    xhr.setRequestHeader('X-GMF-Request', '1');
    xhr.timeout = 120000;
    xhr.upload.onprogress = e => { if (e.lengthComputable) onProgress(Math.round(e.loaded / e.total * 100)); };
    xhr.onload = () => {
      let data;
      try { data = JSON.parse(xhr.responseText); } catch {}
      if (xhr.status >= 200 && xhr.status < 300 && data) resolve(data);
      else reject(Error(typeof data?.detail === 'string' ? data.detail : `上传未完成（${xhr.status}），请重试。`));
    };
    xhr.onerror = () => reject(Error('上传连接中断。已选择的文件保留，可以重试。'));
    xhr.ontimeout = () => reject(Error('上传超时，请检查本地服务后重试。'));
    xhr.send(body);
  });
}
