export function formatRelativeTime(value: Date | null): string {
  if (!value) {
    return "Waiting for first refresh";
  }

  const deltaMs = Date.now() - value.getTime();
  const deltaSeconds = Math.max(0, Math.floor(deltaMs / 1000));

  if (deltaSeconds < 5) {
    return "Updated just now";
  }

  if (deltaSeconds < 60) {
    return `Updated ${deltaSeconds}s ago`;
  }

  const deltaMinutes = Math.floor(deltaSeconds / 60);
  if (deltaMinutes < 60) {
    return `Updated ${deltaMinutes}m ago`;
  }

  const deltaHours = Math.floor(deltaMinutes / 60);
  return `Updated ${deltaHours}h ago`;
}
