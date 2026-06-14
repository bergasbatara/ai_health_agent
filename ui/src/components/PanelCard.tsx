import type { ReactNode } from "react";

interface PanelCardProps {
  title: string;
  badge?: ReactNode;
  className?: string;
  children: ReactNode;
}

export function PanelCard({ title, badge, className, children }: PanelCardProps) {
  const panelClassName = className ? `panel ${className}` : "panel";

  return (
    <article className={panelClassName}>
      <div className="panel-header">
        <h2>{title}</h2>
        {badge ?? null}
      </div>
      {children}
    </article>
  );
}
