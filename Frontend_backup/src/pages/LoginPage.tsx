import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import MainLayout from "../components/layout/MainLayout";
import PageTitle from "../components/common/PageTitle";
// import googleIcon from "../assets/web_neutral_sq_na@1x.png";
// import kakaoIcon from "../assets/kakao_sq_login.png";
import { login as loginApi } from "../api/auth";
import { setAccessToken } from "../api/http";

export default function LoginPage() {
  const navigate = useNavigate();
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const getLoginErrorMessage = (error: unknown) => {
    const raw = error instanceof Error ? error.message : "";
    const lower = raw.toLowerCase();

    if (
      lower.includes("password") ||
      lower.includes("비밀번호") ||
      lower.includes("incorrect") ||
      lower.includes("invalid") ||
      lower.includes("401")
    ) {
      return "비밀번호를 확인해주세요";
    }

    if (
      lower.includes("not found") ||
      lower.includes("no such user") ||
      lower.includes("user not") ||
      lower.includes("account") ||
      lower.includes("404") ||
      lower.includes("존재") ||
      lower.includes("계정")
    ) {
      return "회원가입 후 이용해주세요";
    }

    return "로그인에 실패했습니다.";
  };

  const handleLogin = async () => {
    if (isSubmitting) return;
    setLoginError("");

    const userIdValue = userId.trim();
    if (!userIdValue || !password.trim()) {
      setLoginError("아이디와 비밀번호를 입력해주세요.");
      return;
    }

    try {
      setIsSubmitting(true);
      const authResponse = await loginApi({
        user_id: userIdValue,
        password,
      });
      setAccessToken(authResponse.access_token);
      window.dispatchEvent(new Event("mw_auth_change"));
      navigate("/");
    } catch (error) {
      setLoginError(getLoginErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  /*
  const handleKakaoLogin = async () => {
    try {
      const response = await getKakaoLoginUrl();
      // Redirect to Kakao OAuth page
      window.location.href = response.auth_url;
    } catch (error) {
      console.error('Failed to get Kakao login URL:', error);
      alert('카카오 로그인에 실패했습니다.');
    }
  };
  */

  return (
    <MainLayout>
      <main className="container">
        <PageTitle title="로그인" centered />

        <section className="section">
          <article className="card auth-card">
            <div className="form-grid">
              <label htmlFor="login-name">아이디</label>
              <input
                id="login-name"
                type="text"
                placeholder="아이디"
                value={userId}
                onChange={(event) => {
                  setUserId(event.target.value);
                  setLoginError("");
                }}
              />
              <label htmlFor="login-password">비밀번호</label>
              <input
                id="login-password"
                type="password"
                placeholder="8~20자, 영문 대/소문자·숫자·특수문자 중 2가지 이상"
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value);
                  setLoginError("");
                }}
              />
              <button
                className="primary-btn"
                type="button"
                onClick={handleLogin}
                disabled={isSubmitting}
              >
                {isSubmitting ? "로그인 중..." : "로그인"}
              </button>
              {loginError && (
                <p className="field-error-text" role="alert">
                  {loginError}
                </p>
              )}
            </div>
            <ul className="auth-actions">
              <li>
                <Link className="secondary-btn" to="/signup">회원가입</Link>
              </li>
              <li>
                <Link className="secondary-btn" to="/find-id">아이디 찾기</Link>
              </li>
              <li>
                <Link className="secondary-btn" to="/find-password">비밀번호 찾기</Link>
              </li>
            </ul>
            {/*
            <div className="social-login">
              <div className="social-login-buttons">
                <button className="social-btn" type="button" aria-label="구글로 로그인">
                  <img src={googleIcon} alt="" />
                </button>
                <button
                  className="social-btn"
                  type="button"
                  aria-label="카카오로 로그인"
                  onClick={handleKakaoLogin}
                >
                  <img src={kakaoIcon} alt="" />
                </button>
              </div>
            </div>
            */}
          </article>
        </section>
      </main>
    </MainLayout>
  );
}
