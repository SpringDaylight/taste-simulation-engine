type Props = {
  message?: string;
  className?: string;
};

export default function LoadingState({
  message = "로딩 중...",
  className = "muted",
}: Props) {
  return <p className={className}>{message}</p>;
}
