import { useCallback, useEffect, useState, type MouseEvent } from "react";
import { Link, NavLink } from "react-router-dom";
import logoToggle from "../../assets/logo-ticket-ver2.png";
import { getAccessToken, setAccessToken } from "../../api/http";
import { logout } from "../../api/auth";
import { getCurrentUser } from "../../api/A7_profile";

export default function Header() {
  const navClass = ({ isActive }: { isActive: boolean }) =>
    isActive ? "active" : undefined;
  const handleHeaderLinkClick =
    (to: string) => (event: MouseEvent<HTMLAnchorElement | HTMLButtonElement>) => {
      if (window.location.pathname === to) {
        event.preventDefault();
        window.location.reload();
        return;
      }
      window.scrollTo({ top: 0, behavior: "smooth" });
    };

  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [nickname, setNickname] = useState("");

  const syncProfile = useCallback(async () => {
    const token = getAccessToken();
    setIsLoggedIn(Boolean(token));
    if (token) {
      try {
        const user = await getCurrentUser();
        setNickname(user.nickname || user.name || "사용자");
      } catch (err) {
        console.error("Fetch user failed in Header:", err);
      }
    } else {
      setNickname("");
    }
  }, []);

  useEffect(() => {
    syncProfile();
    const handleAuthChange = () => syncProfile();
    window.addEventListener("mw_auth_change", handleAuthChange);
    window.addEventListener("storage", handleAuthChange);

    return () => {
      window.removeEventListener("mw_auth_change", handleAuthChange);
      window.removeEventListener("storage", handleAuthChange);
    };
  }, [syncProfile]);

  const handleLogout = async () => {
    if (window.confirm("로그아웃 하시겠습니까?")) {
      try {
        await logout();
      } catch (err) {
        console.error("Logout failed:", err);
      } finally {
        setAccessToken(null);

        // LLM 추천 캐시 삭제
        localStorage.removeItem('llm_recommend_state');

        window.dispatchEvent(new Event("mw_auth_change"));
        window.location.href = "/";
      }
    }
  };

  return (
    <header className="top-bar">
      <div className="top-bar-inner">
        <Link className="brand" to="/" onClick={handleHeaderLinkClick("/")}>
          <img className="brand-logo" src={logoToggle} alt="서비스 로고" />
          <div>
            <p className="brand-title">볼래! 말래?</p>
            <p className="brand-sub">취향 기반 영화 탐색 서비스</p>
          </div>
        </Link>

        <nav className="top-nav">
          <NavLink to="/" className={navClass} end onClick={handleHeaderLinkClick("/")}>
            홈
          </NavLink>
          <NavLink
            to="/movies"
            className={navClass}
            onClick={handleHeaderLinkClick("/movies")}
          >
            영화
          </NavLink>
          <NavLink
            to="/llm-recommend"
            className={navClass}
            onClick={handleHeaderLinkClick("/llm-recommend")}
          >
            AI 추천
          </NavLink>
          <NavLink
            to="/group"
            className={navClass}
            onClick={handleHeaderLinkClick("/group")}
          >
            다함께
          </NavLink>
          {/* <NavLink
            to="/moviemong"
            className={navClass}
            onClick={handleHeaderLinkClick("/moviemong")}
          >
            무비몽
          </NavLink> */}
          <NavLink
            to="/mypage"
            className={navClass}
            onClick={handleHeaderLinkClick("/mypage")}
          >
            마이 홈
          </NavLink>
        </nav>

        <div className="top-actions">
          {isLoggedIn ? (
            <div className="profile-chip" style={{ padding: '0.4rem 0.8rem', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
              <Link
                to="/mypage"
                style={{ color: 'inherit', textDecoration: 'none' }}
                onClick={handleHeaderLinkClick("/mypage")}
              >
                {nickname}
              </Link>
              <span style={{ opacity: 0.5 }}>/</span>
              <button
                onClick={handleLogout}
                style={{ background: 'none', border: 'none', padding: 0, color: 'inherit', cursor: 'pointer', fontFamily: 'inherit', fontWeight: 600 }}
              >
                로그아웃
              </button>
            </div>
          ) : (
            <>
              <Link className="profile-chip" to="/login" onClick={handleHeaderLinkClick("/login")}>
                로그인
              </Link>
              <Link className="profile-chip" to="/signup" onClick={handleHeaderLinkClick("/signup")}>
                회원가입
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
