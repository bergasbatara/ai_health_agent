import { toStatusTone } from "../lib";

interface StatusBadgeProps {
  value: string | number | null | undefined;
  tone?: string;
  emptyLabel?: string;
}

export function StatusBadge({ value, tone, emptyLabel = "unknown" }: StatusBadgeProps) {
  if (value === null || value === undefined || value === "") {
    return <span className="badge badge-idle">{emptyLabel}</span>;
  }

  if (typeof value === "number") {
    return <span className="badge badge-idle">{value}</span>;
  }

  const badgeTone = tone ?? toStatusTone(value);
  return <span className={`badge badge-${badgeTone}`}>{value}</span>;
}
