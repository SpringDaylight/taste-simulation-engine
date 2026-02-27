import type { ReactNode } from "react";

type Props = {
  title?: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
  children?: ReactNode;
};

export default function SectionHeader({
  title,
  description,
  actions,
  className,
  children,
}: Props) {
  const classes = ["section-header", className ?? ""].filter(Boolean).join(" ");

  if (children) {
    return <div className={classes}>{children}</div>;
  }

  return (
    <div className={classes}>
      {title ? <h2>{title}</h2> : null}
      {description ? <p>{description}</p> : null}
      {actions ?? null}
    </div>
  );
}
