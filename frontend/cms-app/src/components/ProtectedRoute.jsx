/**
 * ログイン状態・権限を確認し、権限のない画面への遷移を制限する
 */
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../utils/authUtils";


export default function ProtectedRoute({ children, roles }) {
  // 認証情報の取得状態
  const { user, loading } = useAuth();
  // 現在の画面のURLを取得する
  const location = useLocation();
  if (loading) return <p role="status">認証情報を確認中...</p>;
  // ログインしていない場合、ログイン画面へ遷移する
  if (!user) return <Navigate to="/" replace state={{ from: location.pathname }} />;
  // ログインユーザーの権限を確認後、権限のない画面への遷移を制限しつつ、権限のある画面への遷移を許可する
  if (roles && !roles.includes(user.role)) return <Navigate to="/articles" replace />;
  return children;
}
