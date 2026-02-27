export default function MovieCardSample() {
  return (
    <div className="movie-card">
      <img
        className="poster"
        src="https://image.tmdb.org/t/p/w500/uDO8zWDhfWwoFdKS4fzkUJt0Rf0.jpg"
        alt="라라랜드 포스터"
      />

      <div className="movie-info">
        <h3>라라랜드</h3>
        <p className="probability">만족 확률 74%</p>
        <p className="reason">음악과 성장 서사를 좋아하셨어요</p>
        <button className="ghost-btn movie-detail-btn" type="button">
          �� ����
        </button>
      </div>
    </div>
  );
}

