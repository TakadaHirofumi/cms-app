/**
 * 画面共通ヘッダー・ナビゲーション
 */
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../utils/authUtils";
import NotificationBell from "./NotificationBell";
import "./AppHeader.css";


export default function AppHeader() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return <header className="phase4-header">
    <nav aria-label="ユーザーメニュー">
      {user ? <>
        {/* ログインしている場合、ログインユーザー名と権限を表示する */}
        <span>{user.display_name}（{user.role}）</span>
        {/* ADMIN・EDITOR権限のユーザーのみ通知リンクを表示し、押下したら通知一覧画面へ遷移する */}
        {(user.role === "ADMIN" || user.role === "EDITOR") && <NotificationBell />}
        {/* ADMIN権限のユーザーのみユーザー管理リンクを表示し、押下したらユーザー管理画面へ遷移する */}
        {user.role === "ADMIN" && <Link to="/users">ユーザー管理</Link>}
        {/* ログインしている場合、ログアウトボタンを表示し、押下したらログアウトしてログイン画面へ遷移する */}
        <Link to="/" onClick={(event) => { event.preventDefault(); logout(); navigate("/", { replace: true }); }}>ログアウト</Link>
      </> : <>
        {/* ログインしていない場合に表示する */}
        <Link to="/">ログイン</Link>
        <Link to="/register">新規ユーザー登録</Link>
      </>}
    </nav>
  </header>;
}
