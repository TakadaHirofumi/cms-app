/**
 * URLと表示画面を紐付けるルート定義
 */
import { BrowserRouter, Routes, Route } from "react-router-dom";
import ArticleList from "./components/ArticleList";
import ArticleForm from "./components/ArticleForm";
import CategoryManagement from "./components/CategoryManagement";
import TagManagement from "./components/TagManagement";


// 記事一覧、記事作成、記事編集の3つのURLをそれぞれの画面へ割り当て
function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* 記事一覧画面 */}
        <Route path="/" element={<ArticleList />} />
        {/* 記事作成画面 */}
        <Route path="/articles/new" element={<ArticleForm />} />
        {/* 記事編集画面 */}
        <Route path="/articles/:id/edit" element={<ArticleForm />} />
        {/* カテゴリ管理画面 */}
        <Route path="/categories" element={<CategoryManagement />} />
        {/* タグ管理画面 */}
        <Route path="/tags" element={<TagManagement />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;