// Return only the bytes requested by the renderer; load matching source blocks on demand.
export async function readRange(manifest, begin, end, loadPart) {
  if (!Number.isInteger(begin) || !Number.isInteger(end) || begin < 0 || end <= begin || end > manifest.bytes) throw new RangeError('Invalid PDF byte range');
  const output = new Uint8Array(end - begin);
  let offset = 0;
  const jobs = [];
  for (const part of manifest.parts) {
    const partStart = offset, partEnd = offset + part.bytes;
    offset = partEnd;
    if (partStart >= end) break;
    if (partEnd <= begin) continue;
    jobs.push(loadPart(part).then(bytes => {
      const start = Math.max(begin, partStart), stop = Math.min(end, partEnd);
      output.set(bytes.subarray(start - partStart, stop - partStart), start - begin);
    }));
  }
  await Promise.all(jobs);
  return output;
}
