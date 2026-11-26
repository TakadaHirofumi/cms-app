/**
 * 記事作成・編集画面
 */
import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate, useParams } from "react-router-dom";
import { generateSlug, validateArticle } from "../utils/articleValidation";
import "./ArticleForm.css";
import RichTextEditor from "./RichTextEditor";
import RevisionHistory from "./RevisionHistory";
import { useAuth, canEditArticle } from "../utils/authUtils";


// URLに記事IDがある場合は記事編集画面、ない場合は記事作成画面に切り替え
function ArticleForm() {
  // ログインユーザーの権限と記事作成者を確認
  const { user } = useAuth();
  // 記事の編集権限がない場合は操作を許可しない
  const [permissionDenied, setPermissionDenied] = useState(false);
  // 記事ID
  const { id } = useParams();
  // 記事一覧画面への遷移
  const navigate = useNavigate();
  // 記事IDが存在する場合は編集、存在しない場合は新規作成
  const isEdit = Boolean(id);
  // 記事タイトル
  const [title, setTitle] = useState("");
  // 記事本文
  const [body, setBody] = useState("");
  // スラッグ・ステータス・公開日時・カテゴリ・タグ
  const [slug, setSlug] = useState("");
  // ステータス
  const [status, setStatus] = useState("DRAFT");
  // 公開日時
  const [publishedAt, setPublishedAt] = useState("");
  // カテゴリID
  const [categoryId, setCategoryId] = useState("");
  // タグ名
  const [tagNames, setTagNames] = useState([]);
  // カテゴリ
  const [categories, setCategories] = useState([]);
  // タグ
  const [tags, setTags] = useState([]);
  // タグの入力値
  const [tagInput, setTagInput] = useState("");
  // タグのエラー
  const [tagError, setTagError] = useState("");
  // タグの追加
  const [addingTag, setAddingTag] = useState(false);
  // 編集対象記事の取得状態
  const [loading, setLoading] = useState(true);
  // 記事の保存状態
  const [saving, setSaving] = useState(false);
  // 入力エラー
  const [validationErrors, setValidationErrors] = useState({
    title: "",
    slug: "",
  });
  // APIエラー
  const [error, setError] = useState("");
  // 記事の変更履歴の表示状態
  const [showRevisions, setShowRevisions] = useState(false);
  // 復元成功後、フォームに復元結果を反映するための値
  const [restoreVersion, setRestoreVersion] = useState(0);

  // カテゴリ・タグ一覧と編集対象の記事を取得し、入力欄へ反映
  useEffect(() => {
    const controller = new AbortController();
    const fetchArticle = async () => {
      setLoading(true);
      try {
        const requests = [
          // カテゴリ取得APIを呼び出す
          axios.get(
            "/api/categories",
            { signal: controller.signal }
          ),
          // タグ取得APIを呼び出す
          axios.get(
            "/api/tags",
            { signal: controller.signal }
          ),
        ];
        // 編集時のみ既存値取得APIを呼び出す
        if (isEdit) {
          requests.push(
            axios.get(
              `/api/articles/${id}`,
              { signal: controller.signal }
            )
          );
        }
        const [categoryResponse, tagResponse, articleResponse] = await Promise.all(requests);
        if (controller.signal.aborted) return;
        setCategories(categoryResponse.data);
        setTags(tagResponse.data);

        if (articleResponse) {
          const article = articleResponse.data;
          if (!canEditArticle(user, article)) {
            setPermissionDenied(true);
            return;
          }
          setPermissionDenied(false);
          setTitle(article.title ?? "");
          setBody(article.body ?? "");
          setSlug(article.slug ?? "");
          setStatus(article.status ?? "DRAFT");
          setPublishedAt(article.published_at ? String(article.published_at).slice(0, 16) : "");
          setCategoryId(article.category_id == null ? "" : String(article.category_id));
          setTagNames((article.tags ?? []).map((tag) => tag.name));
        }
      } catch (err) {
        if (controller.signal.aborted) return;
        console.error(err);
        setError("記事・カテゴリ・タグ情報の取得に失敗しました。");
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };
    fetchArticle();

    return () => controller.abort();
  }, [id, isEdit, restoreVersion, user]);

  // 記事タイトルの入力値を更新し、直前の記事タイトル入力エラーをクリア
  const handleTitleChange = (event) => {
    setTitle(event.target.value);
    setValidationErrors((prev) => ({
      ...prev,
      title: "",
    }));
  };

  // スラッグ入力値を更新し、入力エラーをクリア
  const handleSlugChange = (event) => {
    setSlug(event.target.value);
    setValidationErrors((prev) => ({
      ...prev,
      slug: "",
    }));
  };

  // 登録済みタグを選択・解除
  const toggleTag = (name) => {
    setTagNames((prev) =>
      prev.includes(name)
        ? prev.filter((tag) => tag !== name)
        : [...prev, name]
    );
  };

  // タグ追加ボタン押下時にDBへ即時登録する
  const addTag = async () => {
    if (addingTag || saving) return;
    const name = tagInput.trim();
    setTagError("");
    if (!name) {
      setTagError("タグ名を入力してください。");
      return;
    }
    if (Array.from(name).length > 30) {
      setTagError("タグ名は30文字以内で入力してください。");
      return;
    }
    setAddingTag(true);
    try {
      // タグ追加APIを呼び出す
      const response = await axios.post(
        "/api/tags",
        {
          name
        }
      );
      const savedTag = response.data;
      setTags((prev) => prev.some((tag) => tag.id === savedTag.id)
        ? prev : [...prev, savedTag]);
      setTagNames((prev) => prev.includes(savedTag.name)
        ? prev : [...prev, savedTag.name]);
      setTagInput("");
    } catch (err) {
      console.error(err);
      setTagError(err.response?.status === 409
        ? "タグ名が既に登録されています。再読み込みして確認してください。"
        : "タグの登録に失敗しました。");
    } finally {
      setAddingTag(false);
    }
  };

  // FastAPIのエラーメッセージを取得
  const getApiError = (err) => {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((item) => item.msg).join(" / ");
    return "記事の保存に失敗しました。";
  };

  // 保存前に共通入力チェックを実行し、作成ならPOST、編集ならPUTで保存
  const handleSubmit = async (event) => {
    event.preventDefault();
    if (saving || addingTag) return;
    setError("");

    // 共通入力チェック
    const errors = validateArticle({
      title,
      slug,
      body,
    });

    setValidationErrors(errors);

    // エラーがある場合は保存しない
    if (Object.values(errors).some(Boolean)) {
      return;
    }

    setSaving(true);

    try {
      const requestData = {
        title: title.trim(),
        slug: slug.trim(),
        body,
        // 公開日時はタイムゾーンなしの日本時間で送信
        status,
        published_at: status === "PUBLISHED" && publishedAt
          ? `${publishedAt}:00`
          : null,
        category_id: categoryId === "" ? null : Number(categoryId),
        tag_names: tagNames,
      };

      if (isEdit) {
        // 記事更新APIを呼び出す
        await axios.put(
          `/api/articles/${id}`,
          requestData
        );
      } else {
        // 記事作成APIを呼び出す
        await axios.post(
          "/api/articles",
          requestData
        );
      }

      // 保存成功後、記事一覧画面へ戻る
      navigate("/articles");
    } catch (err) {
      console.error(err);
      setError(getApiError(err));
    } finally {
      setSaving(false);
    }
  };

  // 復元後に編集内容を再取得し、履歴を閉じる
  const handleRestored = () => {
    setShowRevisions(false);
    setRestoreVersion((prev) => prev + 1);
    setError("");
  };

  // キャンセルボタン押下時、保存せず記事一覧画面へ遷移
  const handleCancel = () => {
    navigate("/articles");
  };

  // 編集対象の取得中はフォームの代わりに読込中メッセージを表示
  if (loading) {
    return (
      <div className="article-form-container">
        読み込み中...
      </div>
    );
  }

  // 編集対象記事が自分の所有でない場合は操作を許可しない
  if (permissionDenied) return (
    <main className="article-form-container">
      <p role="alert">この記事を編集する権限がありません。</p>
      <button type="button" onClick={() => navigate("/articles")}>記事一覧へ戻る</button>
    </main>
  );

  // 記事作成／編集画面の入力欄、保存ボタン、キャンセルボタン、検証エラー、APIエラーを表示
  return (
    <div className="article-form-container">
      <h1>
        {isEdit ? "記事編集" : "記事作成"}
      </h1>

      {/* 共通入力エラー */}
      {validationErrors.title && (
        <div id="title-error" className="title-error-message" role="alert">
          {validationErrors.title}
        </div>
      )}

      {/* スラッグ入力エラー */}
      {validationErrors.slug && (
        <div id="slug-error" className="title-error-message" role="alert">
          {validationErrors.slug}
        </div>
      )}

      {/* APIエラー */}
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      <form className="article-form" onSubmit={handleSubmit} noValidate>
        {/* タイトルの入力 */}
        <div className="form-group">
          <label htmlFor="title">
            タイトル
            <span className="required">
              必須
            </span>
          </label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={handleTitleChange}
            disabled={saving}
            aria-required="true"
            aria-invalid={Boolean(validationErrors.title)}
            aria-describedby={
              validationErrors.title
                ? "title-error"
                : undefined
            }
          />
          <small>
            200文字以内
          </small>
        </div>

        {/* スラッグの入力、タイトルから自動生成 */}
        <div className="form-group">
          <label htmlFor="slug">
            スラッグ
            <span className="required">
              必須
            </span>
          </label>
          <div className="slug-row">
            <input id="slug" type="text" value={slug}
              onChange={handleSlugChange}
              disabled={saving}
              aria-required="true"
              aria-invalid={Boolean(validationErrors.slug)}
              aria-describedby={validationErrors.slug ? "slug-error" : undefined}
              placeholder="my-first-post"
            />
            <button type="button" disabled={saving}
              onClick={() => {
                setSlug(generateSlug(title));
                setValidationErrors((prev) => ({ ...prev, slug: "" }));
              }}
            >
              タイトルから生成
            </button>
          </div>
          <small>
            200文字以内、半角英数字とハイフンのみ
          </small>
        </div>

        {/* 本文の入力 */}
        <div className="form-group">
          <label htmlFor="body">
            本文
          </label>
          {/* HTML形式の本文を編集できるリッチテキストエディタ */}
          <RichTextEditor id="body" value={body} onChange={setBody} disabled={saving} />
        </div>

        {/* 記事ステータスの選択 */}
        <div className="form-group">
          <label htmlFor="status">ステータス</label>
          <select id="status" value={status}
            onChange={(event) => setStatus(event.target.value)}
            disabled={saving}
          >
            <option value="DRAFT">下書き</option>
            <option value="PUBLISHED">公開</option>
            <option value="ARCHIVED">アーカイブ</option>
          </select>
        </div>

        {/* 公開ステータス時のみ公開日時を入力可能にする */}
        {status === "PUBLISHED" && (
          <div className="form-group">
            <label htmlFor="published_at">公開日時</label>
            <input id="published_at" type="datetime-local" value={publishedAt}
              onChange={(event) => setPublishedAt(event.target.value)}
              disabled={saving}
            />
            <small>未入力の場合は保存時に公開。未来日時なら予約公開になります。</small>
          </div>
        )}

        {/* カテゴリの選択 */}
        <div className="form-group">
          <label htmlFor="category_id">カテゴリ</label>
          <select id="category_id" value={categoryId}
            onChange={(event) => setCategoryId(event.target.value)}
            disabled={saving}
          >
            <option value="">カテゴリなし</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>{category.name}</option>
            ))}
          </select>
        </div>

        {/* 登録済みタグの選択と新規タグの追加 */}
        <fieldset className="form-group tag-fieldset" disabled={saving || addingTag}>
          <legend>タグ（複数選択可）</legend>
          <div className="tag-options">
            {tags.map((tag) => (
              <label key={tag.id} className="tag-option">
                <input type="checkbox" checked={tagNames.includes(tag.name)}
                  onChange={() => toggleTag(tag.name)}
                />
                {tag.name}
              </label>
            ))}
          </div>
          <div className="tag-input-row">
            <input aria-label="新しいタグ名" placeholder="新しいタグ名（30文字以内）"
              value={tagInput}
              onChange={(event) => {
                setTagInput(event.target.value);
                setTagError("");
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  addTag();
                }
              }}
            />
            <button type="button" onClick={addTag} disabled={addingTag}>
              {addingTag ? "追加中..." : "タグ追加"}
            </button>
          </div>
          {tagError && (
            <p className="tag-error-message" role="alert">{tagError}</p>
          )}
          <div className="selected-tags">
            {tagNames.map((name) => (
              <button key={name} type="button" className="selected-tag"
                onClick={() => toggleTag(name)} title={`${name}を解除`}
              >
                {name} ×
              </button>
            ))}
          </div>
        </fieldset>

        {/* 編集時のみ変更履歴ボタンを表示 */}
        {isEdit && (
          <div className="revision-actions">
            <button type="button" className="cancel-button"
              onClick={() => setShowRevisions((prev) => !prev)} disabled={saving}
            >
              {showRevisions ? "変更履歴を閉じる" : "変更履歴"}
            </button>
          </div>
        )}

        {/* 変更履歴の選択・復元を保存／キャンセルボタンより上に表示 */}
        {isEdit && showRevisions && (
          <RevisionHistory articleId={id} onRestored={handleRestored} />
        )}

        <div className="form-actions">
          <button type="submit" className="save-button" disabled={saving || addingTag}>
            {saving ? "保存中" : "保存"}
          </button>
          <button type="button" className="cancel-button" onClick={handleCancel} disabled={saving || addingTag}>
            キャンセル
          </button>
        </div>
      </form>
    </div>
  );
}

export default ArticleForm;
