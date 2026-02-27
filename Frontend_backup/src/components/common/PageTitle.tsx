type Props = {
  title: string;
  description?: string;
  centered?: boolean;
  className?: string;
};

export default function PageTitle({
  title,
  description,
  centered = false,
  className,
}: Props) {
  const classes = ["page-title", centered ? "centered" : "", className ?? ""]
    .filter(Boolean)
    .join(" ");

  return (
    <section className={classes}>
      <h1>{title}</h1>
      {description ? <p>{description}</p> : null}
    </section>
  );
}
