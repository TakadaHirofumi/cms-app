/**
 * カテゴリ管理画面
 */
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import "./Management.css";


// スラッグの入力値を検証する正規表現（英数字とハイフンのみ）
const SLUG_PATTERN = /^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$/;

function getApiError(error, fallback) {
  const status = error.response?.status;
  if (status === 409) return "カテゴリ名またはスラッグが既に登録されています。";
  if (status === 422) return "入力内容が正しくありません。カテゴリ名とスラッグを確認してください。";
  return fallback;
}

export default function CategoryManagement() {
  // 記事一覧画面への遷移
  const navigate = useNavigate();
  // APIから取得したカテゴリ一覧
  const [categories, setCategories] = useState([]);
  // カテゴリ名の入力値
  const [name, setName] = useState("");
  // スラッグの入力値
  const [slug, setSlug] = useState("");
  // 入力チェックエラー
  const [errors, setErrors] = useState({});
  // APIエラーメッセージ
  const [error, setError] = useState("");
  // カテゴリ一覧を取得中か確認
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  // 削除処理中の対象ID
  const [deletingId, setDeletingId] = useState(null);
  // 登録・削除後の一覧API再取得を通知する値
  const [reloadVersion, setReloadVersion] = useState(0);

  // 初期表示と登録・削除成功時にDBのカテゴリ一覧を再取得する
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setError("");
      try {
        // 一覧取得APIを呼び出す
        const response = await axios.get(
          "/api/categories",
          { signal: controller.signal }
        );
        if (!controller.signal.aborted) setCategories(response.data);
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error(err);
          setError("カテゴリ一覧の取得に失敗しました。");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, [reloadVersion]);

  const reload = useCallback(() => setReloadVersion((v) => v + 1), []);

  // カテゴリ名、スラッグを保存前に検証する（サーバーでも検証）
  function validate() {
    const next = {};
    if (!name.trim() || Array.from(name.trim()).length > 30) {
      next.name = "カテゴリ名は30文字以内で入力してください。";
    }
    if (slug.length > 200 || !SLUG_PATTERN.test(slug)) {
      next.slug = "スラッグは200文字以内の英数字とハイフンで入力してください。";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  // 入力チェック後にカテゴリ登録APIを呼び出し、成功したら一覧を再取得
  async function handleCreate(event) {
    event.preventDefault();
    if (busy || deletingId !== null || !validate()) return;
    setBusy(true);
    setError("");
    try {
      // カテゴリ登録APIを呼び出す
      await axios.post(
        "/api/categories",
        { name: name.trim(), slug }
      );
      setName("");
      setSlug("");
      setErrors({});
      reload();
    } catch (err) {
      console.error(err);
      setError(getApiError(err, "カテゴリの登録に失敗しました。"));
    } finally {
      setBusy(false);
    }
  }

  // 確認ダイアログで承認された場合のみ削除APIを呼び出す
  async function handleDelete(category) {
    if (busy || deletingId !== null) return;
    const confirmed = window.confirm(
      `カテゴリ「${category.name}」を削除しますか？\nこのカテゴリの記事は削除されず、「カテゴリなし」に変更されます。`
    );
    if (!confirmed) return;
    setDeletingId(category.id);
    setError("");
    try {
      // 削除APIを呼び出す
      await axios.delete(
        `/api/categories/${category.id}`
      );
      reload();
    } catch (err) {
      console.error(err);
      setError("カテゴリの削除に失敗しました。再読み込みして確認してください。");
    } finally {
      setDeletingId(null);
    }
  }

  // 管理画面のヘッダー・フォーム・一覧表・エラーを表示
  return (
    <main className="management-page">
      <div className="management-header">
        <h1>カテゴリ管理</h1>
        <button type="button" className="management-secondary" onClick={() => navigate("/")}>
          記事一覧へ戻る
        </button>
      </div>

      {error && <p className="management-error" role="alert">{error}</p>}

      <section className="management-panel" aria-labelledby="category-create-heading">
        <h2 id="category-create-heading">カテゴリ新規作成</h2>
        <form className="management-form" onSubmit={handleCreate} noValidate>
          <div className="management-field">
            <label htmlFor="category-name">カテゴリ名 <span className="management-required">必須</span></label>
            <input id="category-name" value={name} maxLength={31}
              onChange={(e) => { setName(e.target.value); setErrors((prev) => ({ ...prev, name: "" })); }}
              placeholder="例：技術" aria-invalid={Boolean(errors.name)} aria-describedby={errors.name ? "category-name-error" : undefined} />
            {errors.name && <p id="category-name-error" className="management-field-error">{errors.name}</p>}
          </div>
          <div className="management-field">
            <label htmlFor="category-slug">スラッグ <span className="management-required">必須</span></label>
            <input id="category-slug" value={slug} maxLength={31}
              onChange={(e) => { setSlug(e.target.value); setErrors((prev) => ({ ...prev, slug: "" })); }}
              placeholder="例：technology" aria-invalid={Boolean(errors.slug)} aria-describedby={errors.slug ? "category-slug-error" : undefined} />
            {errors.slug && <p id="category-slug-error" className="management-field-error">{errors.slug}</p>}
          </div>
          <button type="submit" className="management-primary" disabled={busy || deletingId !== null}>
            {busy ? "登録中..." : "カテゴリを登録"}
          </button>
        </form>
      </section>

      <section className="management-panel" aria-labelledby="category-list-heading">
        <h2 id="category-list-heading">登録済みカテゴリ（{categories.length}件）</h2>
        {loading ? <p role="status">読み込み中...</p> : categories.length === 0 ? (
          <p className="management-empty">カテゴリは登録されていません。</p>
        ) : (
          <div className="management-table-scroll">
            <table className="management-table">
              <thead><tr><th scope="col">ID</th><th scope="col">カテゴリ名</th><th scope="col">スラッグ</th><th scope="col">操作</th></tr></thead>
              <tbody>{categories.map((category) => (
                <tr key={category.id}>
                  <td>{category.id}</td><td>{category.name}</td><td>{category.slug}</td>
                  <td><button type="button" className="management-danger"
                    disabled={busy || deletingId !== null} onClick={() => handleDelete(category)}>
                    {deletingId === category.id ? "削除中..." : "削除"}
                  </button></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
