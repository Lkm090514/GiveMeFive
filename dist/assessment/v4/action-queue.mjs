// Preserve clicks arriving while the preceding operation is committing.
export function createActionQueue(){let tail=Promise.resolve();return fn=>{const next=tail.then(fn);tail=next.catch(()=>{});return next;};}
