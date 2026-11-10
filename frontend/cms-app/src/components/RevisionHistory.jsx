/**
 * 記事の変更履歴一覧と復元
 */
import { useEffect, useState } from "react";
import axios from "axios";


const statusLabels = {
  DRAFT: "下書き",
  PUBLISHED: "公開",
  ARCHIVED: "アーカイブ"
};

function RevisionHistory({ articleId, onRestored }) {
  // 変更履歴一覧の状態
  const [revisions, setRevisions] = useState([]);
  // 選択したリビジョンID
  const [selectedId, setSelectedId] = useState("");
  // ロード中・復元中・エラーの状態
  const [loading, setLoading] = useState(true);
  // 復元中の状態
  const [restoring, setRestoring] = useState(false);
  // APIエラー
  const [error, setError] = useState("");

  // 変更履歴一覧取得APIを呼び出す
  useEffect(() => {
    const controller = new AbortController();
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        // 記事の変更履歴一覧取得APIを呼び出す
        const response = await axios.get(
          `/api/articles/${articleId}/revisions`,
          {
            signal: controller.signal
          }
        );
        if (!controller.signal.aborted) setRevisions(response.data);
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error(err);
          setError("変更履歴の取得に失敗しました。");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };
    load();
    return () => controller.abort();
  }, [articleId]);

  const selected = revisions.find((item) => String(item.id) === selectedId);

  // 選択したリビジョンを確認後に復元する
  const handleRestore = async () => {
    if (!selected || restoring) return;
    if (!window.confirm("選択したバージョンに戻しますか？ 現在の内容は変更履歴に保存されます。")) return;
    setRestoring(true);
    setError("");
    try {
      // 記事の変更履歴復元APIを呼び出す
      await axios.post(
        `/api/articles/${articleId}/revisions/${selected.id}/restore`
      );
      onRestored();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || "復元に失敗しました。");
    } finally {
      setRestoring(false);
    }
  };

  return (
    <section className="revision-history" aria-label="変更履歴">
      <h2>変更履歴</h2>
      {error && <p className="error-message" role="alert">{error}</p>}
      {loading ? <p>読み込み中...</p> : revisions.length === 0 ? (
        <p>変更履歴はありません。</p>
      ) : (
        <>
          {/* 履歴はバックエンドで作成日時の新しい順に取得 */}
          <label htmlFor="revision-select">復元するバージョン</label>
          <select id="revision-select" value={selectedId} disabled={restoring}
            onChange={(event) => setSelectedId(event.target.value)}>
            <option value="">選択してください</option>
            {revisions.map((item) => (
              <option key={item.id} value={item.id}>
                {String(item.created_at).replace("T", " ").slice(0, 19)}（履歴ID：{item.id}）
              </option>
            ))}
          </select>
          {selected && (
            <div className="revision-preview">
              <p><strong>タイトル：</strong>{selected.title}</p>
              <p><strong>ステータス：</strong>{statusLabels[selected.status]}</p>
              <p><strong>本文（HTML）：</strong></p>
              <pre>{selected.body || "（本文なし）"}</pre>
            </div>
          )}
          <button type="button" className="save-button" disabled={!selected || restoring}
            onClick={handleRestore}>
            {restoring ? "復元中..." : "このバージョンに戻す"}
          </button>
        </>
      )}
    </section>
  );
}

export default RevisionHistory;
