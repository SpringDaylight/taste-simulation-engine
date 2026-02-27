type Props = {
  posterUrl: string;
  title: string;
  probabilityText: string;
  reason: string;
};

export default function MovieCard({
  posterUrl,
  title,
  probabilityText,
  reason,
}: Props) {
  return (
    <div className="movie-card">
      <img className="poster" src={posterUrl} alt={`${title} 포스터`} />
      <div className="movie-info">
        <h3>{title}</h3>
        <p className="probability">{probabilityText}</p>
        <p className="reason">{reason}</p>
        <button className="ghost-btn movie-detail-btn" type="button">
          상세 보기
        </button>
      </div>
    </div>
  );
}
