import { useState } from "react";
import { Link } from "react-router-dom";
import MainLayout from "../components/layout/MainLayout";
import PageTitle from "../components/common/PageTitle";

export default function FindIdPage() {
  const [email, setEmail] = useState("");

  return (
    <MainLayout>
      <main className="container">
        <PageTitle
          title="아이디 찾기"
          description="가입 시 사용한 이메일로 아이디를 찾습니다."
          centered
        />

        <section className="section">
          <article className="card auth-card">
            <div className="form-grid">
              <label htmlFor="find-id-email">이메일</label>
              <input
                id="find-id-email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
              <button className="primary-btn" type="button">
                아이디 찾기
              </button>
            </div>
            <ul className="auth-actions">
              <li>
                <Link className="secondary-btn auth-link" to="/login">
                로그인으로 돌아가기
              </Link>
              </li>
              <li>
                <Link className="secondary-btn auth-link" to="/signup">
                회원가입
              </Link>
              </li>
            </ul>
          </article>
        </section>
      </main>
    </MainLayout>
  );
}
