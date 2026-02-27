import MainLayout from "../components/layout/MainLayout";
import PageTitle from "../components/common/PageTitle";

export default function CommentPage() {
  return (
    <MainLayout>
      <main className="container">
        <PageTitle
          title="내 감상 기록"
          description="보고 난 뒤의 감정을 잊지 않도록 남겨보세요."
        />

        <section className="section">
          <article className="card">
            <div className="movie-tile">
              <img
                className="poster"
                src="https://image.tmdb.org/t/p/w500/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg"
                alt="매트릭스 포스터"
              />
              <div className="movie-info">
                <h3>매트릭스</h3>
                <p className="muted">현실 감각 · 철학적 질문</p>
              </div>
            </div>

            <div className="section" style={{ marginTop: 16 }}>
              <div className="form-grid">
                <label>평점</label>
                <select defaultValue="4.5">
                  <option value="0.5">0.5</option>
                  <option value="1.0">1.0</option>
                  <option value="1.5">1.5</option>
                  <option value="2.0">2.0</option>
                  <option value="2.5">2.5</option>
                  <option value="3.0">3.0</option>
                  <option value="3.5">3.5</option>
                  <option value="4.0">4.0</option>
                  <option value="4.5">4.5</option>
                  <option value="5.0">5.0</option>
                </select>
                <label>코멘트</label>
                <textarea placeholder="이 장면에서 감정이 확 올라왔어요" />
              </div>
              <button className="primary-btn" style={{ marginTop: 12 }}>
                저장
              </button>
            </div>
          </article>
        </section>
      </main>
    </MainLayout>
  );
}
