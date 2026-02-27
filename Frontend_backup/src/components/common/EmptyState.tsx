type Props = {
  message: string;
  className?: string;
};

export default function EmptyState({ message, className = "muted" }: Props) {
  return <p className={className}>{message}</p>;
}
