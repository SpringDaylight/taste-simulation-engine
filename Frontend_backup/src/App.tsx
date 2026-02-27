import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import HomePage from "./pages/HomePage";
import MoviesPage from "./pages/MoviesPage";
import MovieDetailPage from "./pages/MovieDetailPage";
import GroupPage from "./pages/GroupPage";
import TasteAnalysisPage from "./pages/TasteAnalysisPage";
import ActivityPage from "./pages/ActivityPage";
import CommentPage from "./pages/CommentPage";
// import ProfilePage from "./pages/ProfilePage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import FindIdPage from "./pages/FindIdPage";
import FindPasswordPage from "./pages/FindPasswordPage";
// import KakaoCallbackPage from "./pages/KakaoCallbackPage";
import { SupportPage } from "./pages/SupportPage";
import MoviemongPage from "./pages/MoviemongPage";
import LLMRecommendPage from "./pages/LLMRecommendPage";

export default function App() {
  return (
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <Routes>
        {/* React 기준 정상 라우트 */}
        <Route path="/" element={<HomePage />} />
        <Route path="/chat" element={<Navigate to="/llm-recommend" replace />} />
        <Route path="/movies" element={<MoviesPage />} />
        <Route path="/movies/:movieId" element={<MovieDetailPage />} />
        <Route path="/group" element={<GroupPage />} />
        <Route path="/mypage" element={<ActivityPage />} />
        <Route path="/taste-analysis" element={<TasteAnalysisPage />} />
        <Route path="/log" element={<CommentPage />} />
        <Route path="/moviemong" element={<MoviemongPage />} />
        <Route path="/llm-recommend" element={<LLMRecommendPage />} />
        {/* <Route path="/profile" element={<ProfilePage />} /> */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/find-id" element={<FindIdPage />} />
        <Route path="/find-password" element={<FindPasswordPage />} />
        {/* <Route path="/auth/kakao/callback" element={<KakaoCallbackPage />} /> */}
        <Route path="/notice" element={<SupportPage />} />
        <Route path="/inquiry" element={<SupportPage />} />
        <Route path="/faq" element={<SupportPage />} />
        <Route path="/support" element={<Navigate to="/notice" replace />} />

        {/* 레거시 HTML 경로 대응 (전환기 안전장치) */}
        <Route path="/home.html" element={<Navigate to="/" replace />} />
        <Route path="/chat.html" element={<Navigate to="/llm-recommend" replace />} />
        <Route path="/movies.html" element={<Navigate to="/movies" replace />} />
        <Route
          path="/movie-detail.html"
          element={<Navigate to="/movies/1" replace />}
        />
        <Route path="/group.html" element={<Navigate to="/group" replace />} />
        <Route path="/mypage.html" element={<Navigate to="/mypage" replace />} />
        <Route
          path="/taste-analysis.html"
          element={<Navigate to="/taste-analysis" replace />}
        />
        <Route path="/log.html" element={<Navigate to="/log" replace />} />

        {/* fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
