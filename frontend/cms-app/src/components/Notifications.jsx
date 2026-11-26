/**
 * コメント通知一覧・一括既読画面
 */
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import "./Notifications.css";


export default function Notifications() {
  // コメント通知一覧の取得状態
  const [items, setItems] = useState([]);
  // 画面の読み込み中
  const [loading, setLoading] = useState(true);
  // 画面の更新中
  const [busy, setBusy] = useState(false);
  // 画面のエラー状態
  const [error, setError] = useState("");
  // 画面の再読み込みをトリガーするためのバージョン番号
  const [reloadVersion, setReloadVersion] = useState(0);
  // 各画面への遷移
  const navigate = useNavigate();

  // 自分の記事に投稿されたコメント通知一覧を取得する
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true); setError("");
      try {
        // コメント通知一覧取得APIを呼び出す
        const response = await axios.get(
          "/api/notifications",
          {
            signal: controller.signal
          }
        );
        if (!controller.signal.aborted) setItems(response.data);
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error(err);
          setError("通知一覧の取得に失敗しました。");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, [reloadVersion]);

  // コメント単位の既読情報をMySQLへ保存して全通知を一括既読にする
  async function handleReadAll() {
    if (busy) return;
    setBusy(true); setError("");
    try {
      // コメント通知一括既読APIを呼び出す
      await axios.patch(
        "/api/notifications/read-all"
      );
      setReloadVersion((value) => value + 1);
      // ヘッダーの未読件数も同時に更新する
      window.dispatchEvent(new Event("cms-notifications-read"));
    } catch (err) {
      console.error(err);
      setError("通知の既読処理に失敗しました。");
    } finally {
      setBusy(false);
    }
  }

  return <main className="phase4-page">
    <div className="phase4-notification-header">
      <h1>通知一覧</h1>
      <button type="button" onClick={() => navigate("/articles")}>記事一覧へ</button>
    </div>
    <button type="button" onClick={handleReadAll} disabled={busy || loading || !items.some((item) => !item.is_read)}>
      {busy ? "更新中..." : "すべて既読にする"}
    </button>
    {error && <p className="phase4-error" role="alert">{error}</p>}
    {loading ? <p>読み込み中...</p> : items.length === 0 ? <p>通知はありません。</p> :
      <ul className="phase4-notifications">{items.map((item) => <li key={item.comment_id} className={item.is_read ? "" : "phase4-unread"}>
        <Link to={`/articles/${item.article_id}`}>{item.article_title}</Link>
        <p>{item.author_name}さんがコメントしました：{item.body}</p>
        <small>{String(item.created_at).replace("T", " ").slice(0, 19)} {item.is_read ? "既読" : "未読"}</small>
      </li>)}</ul>}
  </main>;
}
