export function usesOriginalVisual(q) {
  return Boolean(q.assets?.length && (q.display_mode === 'original' || q.has_visual || q.formula_fragments?.length ||
    q.options?.some(o => /\[Visual option\b|\(cid:|\ufffd/.test(o.text))));
}
export function optionCaption(q, option) {
  return usesOriginalVisual(q) ? `选择 ${option.label}（见原题选项）` : option.text;
}
