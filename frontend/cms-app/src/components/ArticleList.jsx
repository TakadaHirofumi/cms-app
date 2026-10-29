/**
 * 記事一覧画面
 */
import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import "./ArticleList.css";


// 記事一覧表の列幅の初期値
const DEFAULT_COLUMN_WIDTHS = {
  status: 300,
  title: 650,
  slug: 210,
  category: 160,
  tags: 220,
  published: 190,
  actions: 200,
};

// 記事一覧表の列幅の最小値
const MIN_COLUMN_WIDTHS = {
  status: 230,
  title: 200,
  slug: 130,
  category: 100,
  tags: 120,
  published: 150,
  actions: 150,
};

function ArticleList() {
  // APIから取得した記事一覧
  const [articles, setArticles] = useState([]);
  // カテゴリの選択肢
  const [categories, setCategories] = useState([]);
  // タグの選択肢
  const [tags, setTags] = useState([]);
  // ステータスの選択値
  const [status, setStatus] = useState("");
  // カテゴリーの選択値
  const [categoryId, setCategoryId] = useState("");
  // タグの選択値
  const [tagIds, setTagIds] = useState([]);
  // キーワード検索の入力値
  const [keywordInput, setKeywordInput] = useState("");
  // キーワード検索の反映値
  const [keyword, setKeyword] = useState("");
  // 並び替え条件
  const [sort, setSort] = useState("updated_desc");
  // 更新・削除後に記事一覧取得APIを再実行するための値
  const [reloadVersion, setReloadVersion] = useState(0);
  // 予約公開の判定用時刻（レンダリング中にDate.now()を実行しない）
  const [currentTime, setCurrentTime] = useState(null);
  // 記事一覧を取得中か確認
  const [loading, setLoading] = useState(true);
  // API処理などで発生したエラーメッセージ
  const [error, setError] = useState("");
  // ステータス変更処理中の記事ID
  const [updatingStatusId, setUpdatingStatusId] = useState(null);
  // 削除処理中の記事ID
  const [deletingId, setDeletingId] = useState(null);
  // テーブルの各列幅
  const [columnWidths, setColumnWidths] = useState(DEFAULT_COLUMN_WIDTHS);
  // リサイズ中の列幅
  const [resizing, setResizing] = useState(null);
  // 各画面への遷移
  const navigate = useNavigate();
  // 画面表示するステータス
  const statusLabels = {
    DRAFT: "下書き",
    PUBLISHED: "公開",
    ARCHIVED: "アーカイブ",
  };

  // 予約公開の判定用時刻を初期取得し、1分ごとに更新
  useEffect(() => {
    const updateCurrentTime = () => setCurrentTime(Date.now());
    updateCurrentTime();
    const timerId = setInterval(updateCurrentTime, 60000);

    return () => clearInterval(timerId);
  }, []);

  // キーワード入力後、350ms待って検索条件に反映
  useEffect(() => {
    const timerId = setTimeout(() => setKeyword(keywordInput.trim()), 350);

    return () => clearTimeout(timerId);
  }, [keywordInput]);

  // カテゴリ・タグの選択肢を取得
  useEffect(() => {
    const controller = new AbortController();
    const fetchOptions = async () => {
      try {
        const [categoryResponse, tagResponse] = await Promise.all([
          axios.get(
            "/api/categories",
            { signal: controller.signal }
          ),
          axios.get(
            "/api/tags",
            { signal: controller.signal }
          ),
        ]);
        if (controller.signal.aborted) return;
        setCategories(categoryResponse.data);
        setTags(tagResponse.data);
      } catch (err) {
        if (controller.signal.aborted) return;
        console.error(err);
        setError("カテゴリ・タグの取得に失敗しました。");
      }
    };
    fetchOptions();

    return () => controller.abort();
  }, []);

  // 初回表示・検索条件変更・更新／削除成功時に記事一覧取得
  useEffect(() => {
    const controller = new AbortController();
    const fetchArticles = async () => {
      setLoading(true);
      setError("");
      try {
        // 検索条件をFastAPIのクエリパラメータへ設定
        const params = new URLSearchParams();
        if (status) params.append("status", status);
        if (categoryId) params.append("category_id", categoryId);
        tagIds.forEach((tagId) => params.append("tag_ids", String(tagId)));
        if (keyword) params.append("keyword", keyword);
        params.append("sort", sort);

        // 記事一覧取得APIを呼び出す
        const response = await axios.get(
          `/api/articles?${params.toString()}`,
          { signal: controller.signal }
        );
        if (controller.signal.aborted) return;

        // 並び替えはFastAPI側で実行するため再ソート不要
        setArticles(response.data);
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
  }, [status, categoryId, tagIds, keyword, sort, reloadVersion]);

  // 登録・更新・削除後にGET /api/articlesを再実行
  const reloadArticles = () => {
    setReloadVersion((prev) => prev + 1);
  };

  // タグを選択／解除する
  const toggleTag = (tagId) => {
    setTagIds((prev) =>
      prev.includes(tagId)
        ? prev.filter((id) => id !== tagId)
        : [...prev, tagId]
    );
  };

  // 検索条件を初期化
  const resetFilters = () => {
    setStatus("");
    setCategoryId("");
    setTagIds([]);
    setKeywordInput("");
    setKeyword("");
    setSort("updated_desc");
    reloadArticles();
  };

  // APIの日時を画面表示用に整形
  const formatDate = (value) =>
    value ? String(value).replace("T", " ").slice(0, 16) : "—";

  // 公開日時が未来なら予約中と判定
  const isScheduled = (article) =>
    article.status === "PUBLISHED" &&
    article.published_at != null &&
    currentTime !== null &&
    Math.floor(new Date(article.published_at).getTime() / 60000) >
      Math.floor(currentTime / 60000);

  // 記事一覧表の列幅変更時の情報を保存
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

  // 新規作成ボタンから記事作成画面へ遷移
  const handleCreate = () => {
    navigate("/articles/new");
  };

  // 編集ボタンを押下した記事の記事編集画面へ遷移
  const handleEdit = (articleId) => {
    navigate(`/articles/${articleId}/edit`);
  };

  // ステータス変更後は記事一覧取得APIを再実行
  const handleStatusChange = async (
    articleId,
    newStatus
  ) => {
    const targetArticle = articles.find(
      (article) => article.id === articleId
    );
    if (!targetArticle || updatingStatusId !== null || deletingId !== null) return;
    if (targetArticle.status === newStatus) return;
    setError("");
    setUpdatingStatusId(articleId);

    try {
      // ステータス変更APIを呼び出す
      await axios.patch(
        `/api/articles/${articleId}/status`,
        { status: newStatus }
      );
      // 変更後の最新情報を再取得
      reloadArticles();
    } catch (err) {
      console.error(err);
      setError("ステータスの変更に失敗しました。");
    } finally {
      setUpdatingStatusId(null);
    }
  };

  // 確認ダイアログ表示後、OKボタン押下されたら記事を削除
  const handleDelete = async (articleId) => {
    if (updatingStatusId !== null || deletingId !== null) return;
    const confirmed = window.confirm("この記事を削除しますか？");
    if (!confirmed) return;
    setError("");
    setDeletingId(articleId);

    try {
      // 削除APIを呼び出す
      await axios.delete(
        `/api/articles/${articleId}`
      );
      // 削除後の最新一覧を再取得
      reloadArticles();
    } catch (err) {
      console.error(err);
      setError("記事の削除に失敗しました。");
    } finally {
      setDeletingId(null);
    }
  };

  // 記事一覧画面のヘッダー、記事一覧表、各種ボタン、エラー表示、記事がない場合のメッセージを表示
  return (
    <div className="article-list">
      <div className="article-list-header">
        <h1>
          記事一覧
        </h1>
        <div className="article-list-header-actions">
          <button type="button" className="management-button"
            onClick={() => navigate("/categories")}
          >
            カテゴリ管理
          </button>
          <button type="button" className="management-button"
            onClick={() => navigate("/tags")}
          >
            タグ管理
          </button>
          <button type="button" className="create-button" onClick={handleCreate}>
            新規作成
          </button>
        </div>
      </div>

      {/* ステータス、カテゴリ、タグ、キーワード検索、並び替えのフィルター */}
      <div className="article-filters">
        <label>
          ステータス
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">すべて</option>
            {Object.entries(statusLabels).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
        <label>
          カテゴリ
          <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
            <option value="">すべて</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>{category.name}</option>
            ))}
          </select>
        </label>
        <fieldset className="tag-filter">
          <legend>タグ（複数選択可）</legend>
          <div className="tag-filter-options">
            {tags.map((tag) => (
              <label key={tag.id}>
                <input type="checkbox" checked={tagIds.includes(tag.id)}
                  onChange={() => toggleTag(tag.id)}
                />
                {tag.name}
              </label>
            ))}
            {tags.length === 0 && <span>タグなし</span>}
          </div>
        </fieldset>
        <label>
          キーワード検索
          <input type="search" value={keywordInput}
            onChange={(event) => setKeywordInput(event.target.value)}
            placeholder="タイトル・本文を検索"
          />
        </label>
        <label>
          並び替え
          <select value={sort} onChange={(event) => setSort(event.target.value)}>
            <option value="updated_desc">更新日時が新しい順</option>
            <option value="published_desc">公開日時が新しい順</option>
            <option value="title_asc">タイトル昇順</option>
          </select>
        </label>
        <button type="button" className="filter-reset-button" onClick={resetFilters}>
          条件をクリア
        </button>
      </div>

      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}

      {loading ? (
        <p className="no-articles">読み込み中...</p>
      ) : articles.length === 0 ? (
        <p className="no-articles">
          該当する記事はありません
        </p>
      ) : (
        <div className="article-table-wrapper">
          <table className="article-table">
            <colgroup>
              <col style={{ width: columnWidths.status }}/>
              <col style={{ width: columnWidths.title }}/>
              <col style={{ width: columnWidths.slug }}/>
              <col style={{ width: columnWidths.category }}/>
              <col style={{ width: columnWidths.tags }}/>
              <col style={{ width: columnWidths.published }}/>
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
                  スラッグ
                  <span className="column-resizer"
                    onPointerDown={(event) =>
                      handleResizeStart(event, "slug")
                    }
                  />
                </th>
                <th scope="col">
                  カテゴリ
                  <span className="column-resizer"
                    onPointerDown={(event) =>
                      handleResizeStart(event, "category")
                    }
                  />
                </th>
                <th scope="col">
                  タグ
                  <span className="column-resizer"
                    onPointerDown={(event) =>
                      handleResizeStart(event, "tags")
                    }
                  />
                </th>
                <th scope="col">
                  公開日時
                  <span className="column-resizer"
                    onPointerDown={(event) =>
                      handleResizeStart(event, "published")
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
                    {/* ステータスの表示 */}
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
                          deletingId !== null
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
                    {/* ステータスがアーカイブの場合、2行目に表示 */}
                    {article.status === "ARCHIVED" && (
                      <span className="archived-label">
                        アーカイブ済み
                      </span>
                    )}
                    {/* ステータスが公開で公開日時が未来日の場合、2行目に表示 */}
                    {isScheduled(article) && (
                      <span className="scheduled-label">
                        予約中
                      </span>
                    )}
                  </td>
                  <td className="article-title">
                    {article.title}
                  </td>
                  {/* スラッグ、カテゴリー、タグ、公開日時を表示 */}
                  <td>{article.slug}</td>
                  <td>{article.category?.name ?? "カテゴリなし"}</td>
                  <td>{article.tags?.map((tag) => tag.name).join("、") || "—"}</td>
                  <td>{formatDate(article.published_at)}</td>
                  <td>
                    <div className="action-buttons">
                      <button type="button" className="edit-button"
                        onClick={() =>
                          handleEdit(article.id)
                        }
                        disabled={deletingId !== null || updatingStatusId !== null}
                      >
                        編集
                      </button>

                      <button type="button" className="delete-button"
                        onClick={() =>
                          handleDelete(article.id)
                        }
                        disabled={deletingId !== null || updatingStatusId !== null}
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
