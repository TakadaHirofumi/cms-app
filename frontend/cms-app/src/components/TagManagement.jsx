/**
 * タグ管理画面
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import "./Management.css";


export default function TagManagement() {
  // 記事一覧画面への遷移
  const navigate = useNavigate();
  // APIから取得したタグ一覧
  const [tags, setTags] = useState([]);
  // タグ一覧を取得中か確認
  const [loading, setLoading] = useState(true);
  // APIエラーメッセージ
  const [error, setError] = useState("");
  // 削除処理中の対象ID
  const [deletingId, setDeletingId] = useState(null);
  // 登録・削除後の一覧API再取得を通知する値
  const [reloadVersion, setReloadVersion] = useState(0);

  // 初期表示と削除成功時にDBのタグ一覧を再取得する
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setError("");
      try {
        // 一覧取得APIを呼び出す
        const response = await axios.get(
          "/api/tags",
          { signal: controller.signal }
        );
        if (!controller.signal.aborted) setTags(response.data);
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error(err);
          setError("タグ一覧の取得に失敗しました。");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, [reloadVersion]);

  // 確認ダイアログで承認された場合のみ削除APIを呼び出す
  async function handleDelete(tag) {
    if (deletingId !== null) return;
    const confirmed = window.confirm(
      `タグ「${tag.name}」を削除しますか？\n記事は削除されず、このタグとの関連付けだけが解除されます。`
    );
    if (!confirmed) return;
    setDeletingId(tag.id);
    setError("");
    try {
      // 削除APIを呼び出す
      await axios.delete(
        `/api/tags/${tag.id}`
      );
      setReloadVersion((v) => v + 1);
    } catch (err) {
      console.error(err);
      setError("タグの削除に失敗しました。再読み込みして確認してください。");
    } finally {
      setDeletingId(null);
    }
  }

  // 管理画面のヘッダー・フォーム・一覧表・エラーを表示
  return (
    <main className="management-page">
      <div className="management-header">
        <h1>タグ管理</h1>
        <button type="button" className="management-secondary" onClick={() => navigate("/")}>
          記事一覧へ戻る
        </button>
      </div>
      <p className="management-description">タグは記事作成・編集画面で新しいタグ名を入力して保存すると、自動的に登録されます。</p>
      {error && <p className="management-error" role="alert">{error}</p>}
      <section className="management-panel" aria-labelledby="tag-list-heading">
        <h2 id="tag-list-heading">登録済みタグ（{tags.length}件）</h2>
        {loading ? <p role="status">読み込み中...</p> : tags.length === 0 ? (
          <p className="management-empty">タグは登録されていません。</p>
        ) : (
          <div className="management-table-scroll">
            <table className="management-table">
              <thead><tr><th scope="col">ID</th><th scope="col">タグ名</th><th scope="col">操作</th></tr></thead>
              <tbody>{tags.map((tag) => (
                <tr key={tag.id}>
                  <td>{tag.id}</td><td>{tag.name}</td>
                  <td><button type="button" className="management-danger"
                    disabled={deletingId !== null} onClick={() => handleDelete(tag)}>
                    {deletingId === tag.id ? "削除中..." : "削除"}
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
