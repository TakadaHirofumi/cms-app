/**
 * 記事作成・編集画面
 */
import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate, useParams } from "react-router-dom";
import { validateArticle } from "../utils/articleValidation";
import "./ArticleForm.css";


// URLに記事IDがある場合は記事編集画面、ない場合は記事作成画面に切り替え
function ArticleForm() {
  // 記事ID
  const { id } = useParams();
  const navigate = useNavigate();
  // 記事IDが存在する場合は編集、存在しない場合は新規作成
  const isEdit = Boolean(id);
  // 記事タイトル
  const [title, setTitle] = useState("");
  // 記事本文
  const [body, setBody] = useState("");
  // 編集対象記事の取得状態
  const [loading, setLoading] = useState(isEdit);
  // 記事の保存状態
  const [saving, setSaving] = useState(false);
  // 入力エラー
  const [validationErrors, setValidationErrors] = useState({
    title: "",
  });
  // APIエラー
  const [error, setError] = useState("");

  // 編集時のみ既存の記事を取得し、入力欄へ反映
  useEffect(() => {
    if (!isEdit) return;
    const controller = new AbortController();
    const fetchArticle = async () => {
      setLoading(true);
      try {
        // 既存値取得APIを呼び出す
        const response = await axios.get(
          `/api/articles/${id}`,
          { signal: controller.signal }
        );
        setTitle(response.data.title);
        setBody(response.data.body ?? "");
      } catch (err) {
        if (controller.signal.aborted) return;
        console.error(err);
        setError("記事の取得に失敗しました。");
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };
    fetchArticle();

    return () => controller.abort();
  }, [id, isEdit]);

  // 記事タイトルの入力値を更新し、直前の記事タイトル入力エラーをクリア
  const handleTitleChange = (event) => {
    setTitle(event.target.value);
    setValidationErrors((prev) => ({
      ...prev,
      title: "",
    }));
  };

  // 保存前に共通入力チェックを実行し、作成ならPOST、編集ならPUTで保存
  const handleSubmit = async (event) => {
    event.preventDefault();
    if (saving) return;
    setError("");

    // 共通入力チェック
    const errors = validateArticle({
      title,
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
        body,
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

      // 保存成功後、記事一覧へ戻る
      navigate("/");
    } catch (err) {
      console.error(err);
      setError("記事の保存に失敗しました。");
    } finally {
      setSaving(false);
    }
  };

  // キャンセルボタン押下時、保存せず記事一覧画面へ遷移
  const handleCancel = () => {
    navigate("/");
  };

  // 編集対象の取得中はフォームの代わりに読込中メッセージを表示
  if (loading) {
    return (
      <div className="article-form-container">
        読み込み中...
      </div>
    );
  }

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

      {/* APIエラー */}
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      <form className="article-form" onSubmit={handleSubmit} noValidate>
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
        </div>

        <div className="form-group">
          <label htmlFor="body">
            本文
          </label>
          <textarea id="body" value={body}
            onChange={(event) =>
              setBody(event.target.value)
            }
            disabled={saving}
            rows={15}
          />
        </div>

        <div className="form-actions">
          <button type="submit" className="save-button" disabled={saving}>
            {saving ? "保存中" : "保存"}
          </button>
          <button type="button" className="cancel-button" onClick={handleCancel} disabled={saving}>
            キャンセル
          </button>
        </div>
      </form>
    </div>
  );
}

export default ArticleForm;
