/**
 * 画面遷移の管理
 */
import { BrowserRouter, Routes, Route } from "react-router-dom";
import ArticleList from "./components/ArticleList";
import ArticleForm from "./components/ArticleForm";


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ArticleList />} />
        <Route path="/articles/new" element={<ArticleForm />} />
        <Route path="/articles/:id/edit" element={<ArticleForm />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;