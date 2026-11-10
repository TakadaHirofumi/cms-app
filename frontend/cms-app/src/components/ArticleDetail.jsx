/**
 * 記事詳細・コメント一覧・コメント投稿画面
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import DOMPurify from "dompurify";
import "./ArticleDetail.css";


function ArticleDetail() {
  // 記事ID
  const { id } = useParams();
  // 記事一覧画面への遷移
  const navigate = useNavigate();
  // 記事詳細・コメント一覧・コメント投稿の状態
  const [article, setArticle] = useState(null);
  // コメント一覧
  const [comments, setComments] = useState([]);
  // 投稿者名フォームの入力値
  const [authorName, setAuthorName] = useState("");
  // コメント本文フォームの入力値
  const [body, setBody] = useState("");
  // ロード中・投稿中・エラーの状態
  const [loading, setLoading] = useState(true);
  // 投稿中の状態
  const [posting, setPosting] = useState(false);
  // APIエラー
  const [error, setError] = useState("");
  // コメント投稿フォームの入力エラー
  const [commentError, setCommentError] = useState("");

  // 記事詳細とコメント一覧を取得する
  useEffect(() => {
    const controller = new AbortController();
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const [articleResponse, commentResponse] = await Promise.all([
          // 記事詳細取得APIを呼び出す
          axios.get(
            `/api/articles/${id}`,
            { signal: controller.signal }
          ),
          // コメント一覧取得APIを呼び出す
          axios.get(
            `/api/articles/${id}/comments`,
            { signal: controller.signal }
          ),
        ]);
        if (controller.signal.aborted) return;
        setArticle(articleResponse.data);
        setComments(commentResponse.data);
      } catch (err) {
        if (controller.signal.aborted) return;
        console.error(err);
        setError("記事またはコメントの取得に失敗しました。");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };
    load();
    return () => controller.abort();
  }, [id]);

  // コメント投稿前に入力を検証し、投稿成功後に一覧を再取得する
  const handlePost = async (event) => {
    event.preventDefault();
    if (posting || article?.status !== "PUBLISHED") return;
    setCommentError("");
    if (!authorName.trim() || Array.from(authorName.trim()).length > 50) {
      setCommentError("投稿者名は50文字以内で入力してください。");
      return;
    }
    if (!body.trim() || Array.from(body.trim()).length > 1000) {
      setCommentError("コメント本文は1000文字以内で入力してください。");
      return;
    }
    setPosting(true);
    try {
      // コメント投稿APIを呼び出す
      await axios.post(
        `/api/articles/${id}/comments`,
        {
          author_name: authorName.trim(),
          body: body.trim(),
        }
      );
      // 投稿成功後にコメント一覧取得APIを呼び出す
      const response = await axios.get(
        `/api/articles/${id}/comments`
      );
      setComments(response.data);
      setBody("");
    } catch (err) {
      console.error(err);
      setCommentError(err.response?.status === 403
        ? "公開済みの記事以外にはコメントできません。"
        : "コメントの投稿に失敗しました。");
    } finally {
      setPosting(false);
    }
  };

  if (loading) return
  <main className="article-detail">
    読み込み中...
  </main>;
  
  if (error || !article) return
  <main className="article-detail"><p role="alert">{error || "記事が見つかりません。"}</p>
    <button onClick={() => navigate("/")}>
      記事一覧へ戻る
    </button>
  </main>;

  return (
    <main className="article-detail">
      <div className="article-detail-header">
        <h1>{article.title}</h1>
        <button type="button" onClick={() => navigate("/")}>記事一覧へ戻る</button>
      </div>
      <p>ステータス：{{ DRAFT: "下書き", PUBLISHED: "公開", ARCHIVED: "アーカイブ" }[article.status]}</p>
      {/* 本文HTMLは危険なタグを除去してから表示する */}
      <div className="article-detail-body"
        dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(article.body || "") }} />
      {article.status === "PUBLISHED" ? (
        <section className="article-comments">
          <h2>コメント一覧（{comments.length}件）</h2>
          {comments.length === 0 ? <p>コメントはありません。</p> : (
            <ul>{comments.map((comment) => (
              <li key={comment.id}>
                <strong>{comment.author_name}</strong>
                <time>{String(comment.created_at).replace("T", " ").slice(0, 16)}</time>
                <p>{comment.body}</p>
              </li>
            ))}</ul>
          )}
          {/* 公開済み記事にのみコメント投稿フォームを表示する */}
          <h2>
            コメントを投稿
          </h2>
          {commentError && <p className="detail-error" role="alert">{commentError}</p>}
          <form onSubmit={handlePost}>
            {/* 投稿者名の入力（必須、50文字以内） */}
            <label htmlFor="comment-author">
              投稿者名
              <span className="comment-required">
                必須
              </span>
            </label>
            <input id="comment-author" value={authorName} disabled={posting} aria-required="true"
              aria-describedby="comment-author-help"
              onChange={(event) => setAuthorName(event.target.value)} />
            <small id="comment-author-help" className="comment-help">
              50文字以内
            </small>
            {/* コメント本文の入力（必須、1000文字以内） */}
            <label htmlFor="comment-body">
              本文
              <span className="comment-required">
                必須
              </span>
            </label>
            <textarea id="comment-body" value={body} disabled={posting} aria-required="true"
              aria-describedby="comment-body-help"
              onChange={(event) => setBody(event.target.value)} rows={5} />
            <small id="comment-body-help" className="comment-help">
              1000文字以内
            </small>
            <button type="submit" disabled={posting}>{posting ? "投稿中..." : "コメントを投稿"}</button>
          </form>
        </section>
      ) : <p>下書き・アーカイブ済みの記事にはコメントを投稿できません。</p>}
    </main>
  );
}

export default ArticleDetail;
