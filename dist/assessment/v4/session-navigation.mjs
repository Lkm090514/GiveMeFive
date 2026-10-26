// Only an authoritative submitted response for this cached exam can release it.
export function cachedExamLock(id, session) {
  return id && session?.id === id && session.mode === 'exam' && session.status === 'submitted' ? null : id;
}
