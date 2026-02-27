import { useEffect } from "react";
import Header from "./Header";
import { getAccessToken } from "../../api/http";
import { removeSessionItem } from "../../utils/storage";
// import BottomNav from "./BottomNav";

export default function MainLayout({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const handleAuthChange = () => {
      if (!getAccessToken()) {
        removeSessionItem("mw_group_page_snapshot");
        window.location.href = "/";
      }
    };

    window.addEventListener("mw_auth_change", handleAuthChange);
    window.addEventListener("storage", handleAuthChange);

    return () => {
      window.removeEventListener("mw_auth_change", handleAuthChange);
      window.removeEventListener("storage", handleAuthChange);
    };
  }, []);

  return (
    <>
      <Header />
      {children}
      {/* <BottomNav /> */}
    </>
  );
}
