import type { KeyboardEventHandler, ReactNode } from "react";

type Props = {
  title: string;
  posterUrl: string;
  posterAlt?: string;
  className?: string;
  titleSlot?: ReactNode;
  children?: ReactNode;
  onClick?: () => void;
  onKeyDown?: KeyboardEventHandler<HTMLElement>;
  role?: string;
  tabIndex?: number;
};

export default function MovieTileCard({
  title,
  posterUrl,
  posterAlt,
  className,
  titleSlot,
  children,
  onClick,
  onKeyDown,
  role,
  tabIndex,
}: Props) {
  return (
    <article
      className={["card movie-tile", className ?? ""].filter(Boolean).join(" ")}
      onClick={onClick}
      onKeyDown={onKeyDown}
      role={role}
      tabIndex={tabIndex}
    >
      <img className="poster" src={posterUrl} alt={posterAlt ?? `${title} 포스터`} />
      <div className="movie-info">
        {titleSlot ?? <h3>{title}</h3>}
        {children}
      </div>
    </article>
  );
}
