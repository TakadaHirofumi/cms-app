/**
 * 記事一覧画面
 */
import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import "./ArticleList.css";


const DEFAULT_COLUMN_WIDTHS = {
  status: 300,
  title: 650,
  actions: 200,
};

const MIN_COLUMN_WIDTHS = {
  status: 230,
  title: 200,
  actions: 150,
};

function ArticleList() {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatingStatusId, setUpdatingStatusId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [columnWidths, setColumnWidths] = useState(DEFAULT_COLUMN_WIDTHS);
  const [resizing, setResizing] = useState(null);
  const navigate = useNavigate();
  const statusLabels = {
    DRAFT: "下書き",
    PUBLISHED: "公開",
    ARCHIVED: "アーカイブ",
  };

  // 記事一覧取得
  useEffect(() => {
    const controller = new AbortController();
    const fetchArticles = async () => {
      try {
        // 記事一覧取得APIを呼び出す
        const response = await axios.get("/api/articles", {
          signal: controller.signal,
        });
        // 記事作成日時の降順でソート
        const sortedArticles = [...response.data].sort(
          (a, b) =>
            new Date(b.created_at) -
            new Date(a.created_at)
        );
        setArticles(sortedArticles);
      } catch (err) {
        if (controller.signal.aborted) return;
        console.error(err);
        setError("記事一覧の取得に失敗しました。");
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };
    fetchArticles();

    return () => controller.abort();
  }, []);

  // ドラッグ開始時の情報を保存
  const handleResizeStart = (event, column) => {
    if (event.button !== 0) return;
    event.preventDefault();
    setResizing({
      column,
      startX: event.clientX,
      startWidth: columnWidths[column],
    });
  };

  // ドラッグ中の列幅変更と終了時の後片付け
  useEffect(() => {
    if (!resizing) return;
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    const handlePointerMove = (event) => {
      const newWidth = Math.max(
        MIN_COLUMN_WIDTHS[resizing.column],
        resizing.startWidth + event.clientX - resizing.startX
      );
      setColumnWidths((prev) => ({
        ...prev,
        [resizing.column]: newWidth,
      }));
    };
    const stopResize = () => setResizing(null);
    document.addEventListener("pointermove", handlePointerMove);
    document.addEventListener("pointerup", stopResize);
    document.addEventListener("pointercancel", stopResize);
    
    return () => {
      document.removeEventListener("pointermove", handlePointerMove);
      document.removeEventListener("pointerup", stopResize);
      document.removeEventListener("pointercancel", stopResize);
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
    };
  }, [resizing]);

  // 新規作成
  const handleCreate = () => {
    navigate("/articles/new");
  };

  // 編集
  const handleEdit = (articleId) => {
    navigate(`/articles/${articleId}/edit`);
  };

  // ステータス変更
  const handleStatusChange = async (
    articleId,
    newStatus
  ) => {
    const targetArticle = articles.find(
      (article) => article.id === articleId
    );
    if (!targetArticle) return;
    const oldStatus = targetArticle.status;
    setError("");
    setUpdatingStatusId(articleId);

    // 先に画面表示を変更
    setArticles((prevArticles) =>
      prevArticles.map((article) =>
        article.id === articleId
          ? { ...article, status: newStatus }
          : article
      )
    );

    try {
      // ステータス変更APIを呼び出す
      const response = await axios.patch(
        `/api/articles/${articleId}/status`,
        { status: newStatus }
      );

      setArticles((prevArticles) =>
        prevArticles.map((article) =>
          article.id === articleId
            ? response.data
            : article
        )
      );
    } catch (err) {
      console.error(err);

      setArticles((prevArticles) =>
        prevArticles.map((article) =>
          article.id === articleId
            ? { ...article, status: oldStatus }
            : article
        )
      );

      setError("ステータスの変更に失敗しました。");
    } finally {
      setUpdatingStatusId(null);
    }
  };

  // 削除
  const handleDelete = async (articleId) => {
    const confirmed = window.confirm("この記事を削除しますか？");
    if (!confirmed) return;
    setError("");
    setDeletingId(articleId);

    try {
      // 削除APIを呼び出す
      await axios.delete(`/api/articles/${articleId}`);
      setArticles((prevArticles) =>
        prevArticles.filter(
          (article) => article.id !== articleId
        )
      );
    } catch (err) {
      console.error(err);
      setError("記事の削除に失敗しました。");
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return (
      <div className="article-list">
        読み込み中...
      </div>
    );
  }

  return (
    <div className="article-list">
      <div className="article-list-header">
        <h1>
          記事一覧
        </h1>
        <button type="button" className="create-button" onClick={handleCreate}>
          新規作成
        </button>
      </div>

      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}

      {articles.length === 0 ? (
        <p className="no-articles">
          記事はありません
        </p>
      ) : (
        <div className="article-table-wrapper">
          <table className="article-table">
            <colgroup>
              <col style={{ width: columnWidths.status }}/>
              <col style={{ width: columnWidths.title }}/>
              <col style={{ width: columnWidths.actions }}/>
            </colgroup>

            {/* テーブルヘッダー */}
            <thead>
              <tr>
                <th scope="col">
                  ステータス
                  <span className="column-resizer"
                    onPointerDown={(event) =>
                      handleResizeStart(event, "status")
                    }
                  />
                </th>
                <th scope="col">
                  タイトル
                  <span className="column-resizer"
                    onPointerDown={(event) =>
                      handleResizeStart(event, "title")
                    }
                  />
                </th>
                <th scope="col">
                  操作
                  <span className="column-resizer"
                    onPointerDown={(event) =>
                      handleResizeStart(event, "actions")
                    }
                  />
                </th>
              </tr>
            </thead>

            {/* テーブルボディ */}
            <tbody>
              {articles.map((article) => (
                <tr key={article.id}
                  className={
                    article.status === "ARCHIVED"
                      ? "archived-row"
                      : ""
                  }
                >
                  <td>
                    <div className="status-area">
                      <span className={`status-badge status-${article.status.toLowerCase()}`}>
                        {statusLabels[article.status]}
                      </span>
                      <select value={article.status}
                        onChange={(event) =>
                          handleStatusChange(
                            article.id,
                            event.target.value
                          )
                        }
                        disabled={
                          updatingStatusId === article.id ||
                          deletingId === article.id
                        }
                        className="status-select"
                        aria-label={`${article.title}のステータス`}
                      >
                        <option value="DRAFT">
                          下書き
                        </option>
                        <option value="PUBLISHED">
                          公開
                        </option>
                        <option value="ARCHIVED">
                          アーカイブ
                        </option>
                      </select>
                    </div>
                    {article.status === "ARCHIVED" && (
                      <span className="archived-label">
                        アーカイブ済み
                      </span>
                    )}
                  </td>
                  <td className="article-title">
                    {article.title}
                  </td>
                  <td>
                    <div className="action-buttons">
                      <button type="button" className="edit-button"
                        onClick={() =>
                          handleEdit(article.id)
                        }
                        disabled={deletingId === article.id || updatingStatusId === article.id}
                      >
                        編集
                      </button>

                      <button type="button" className="delete-button"
                        onClick={() =>
                          handleDelete(article.id)
                        }
                        disabled={deletingId === article.id || updatingStatusId === article.id}
                      >
                        削除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default ArticleList;
