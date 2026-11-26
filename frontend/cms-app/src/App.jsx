/**
 * URLと表示画面を紐付けるルート定義
 */
import { BrowserRouter, Routes, Route } from "react-router-dom";
import ArticleList from "./components/ArticleList";
import ArticleForm from "./components/ArticleForm";
import ArticleDetail from "./components/ArticleDetail";
import CategoryManagement from "./components/CategoryManagement";
import TagManagement from "./components/TagManagement";
import { AuthProvider } from "./components/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import AuthPage from "./components/AuthPage";
import UserManagement from "./components/UserManagement";
import Notifications from "./components/Notifications";
import AppHeader from "./components/AppHeader";


// ログイン画面（/）と記事一覧画面（/articles）を含む各URLを画面へ割り当て
function App() {
  return (
    <AuthProvider>
    <BrowserRouter>
      <AppHeader />
      <Routes>
        {/* ログイン画面 */}
        <Route path="/" element={<AuthPage />} />
        {/* 記事一覧画面 */}
        <Route path="/articles" element={<ArticleList />} />
        {/* 記事作成画面 */}
        <Route path="/articles/new" element={<ProtectedRoute roles={["ADMIN", "EDITOR"]}><ArticleForm /></ProtectedRoute>} />
        {/* 記事編集画面 */}
        <Route path="/articles/:id/edit" element={<ProtectedRoute roles={["ADMIN", "EDITOR"]}><ArticleForm /></ProtectedRoute>} />
        {/* 記事詳細画面 */}
        <Route path="/articles/:id" element={<ArticleDetail />} />
        {/* カテゴリ管理画面 */}
        <Route path="/categories" element={<ProtectedRoute roles={["ADMIN", "EDITOR"]}><CategoryManagement /></ProtectedRoute>} />
        {/* タグ管理画面 */}
        <Route path="/tags" element={<ProtectedRoute roles={["ADMIN", "EDITOR"]}><TagManagement /></ProtectedRoute>} />
        {/* ユーザー登録画面 */}
        <Route path="/register" element={<AuthPage register />} />
        {/* ユーザー管理画面 */}
        <Route path="/users" element={<ProtectedRoute roles={["ADMIN"]}><UserManagement /></ProtectedRoute>} />
        {/* コメント通知 */}
        <Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
    </AuthProvider>
  );
}

export default App;