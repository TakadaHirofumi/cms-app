/**
 * 未読コメント件数を取得してコメント通知一覧画面へ遷移
 */
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../utils/authUtils";


// ブラウザ通知に対応している場合のみ許可状態を取得する
function getNotificationPermission() {
  return typeof window.Notification === "function" && window.isSecureContext
    ? window.Notification.permission : "unsupported";
}

// ブラウザ通知の失敗が未読件数取得や他機能に影響しないようにする
function showBrowserNotification(count) {
  try {
    if (getNotificationPermission() !== "granted" || count <= 0) return;
    new window.Notification("新着コメント通知", {
      body: `あなたの記事に${count}件の未読コメントがあります。`,
      tag: "cms-unread-comments",
    });
  } catch (err) { console.error(err); }
}

export default function NotificationBell() {
  // 認証済みユーザーの未読件数を取得する
  const { user } = useAuth();
  // 未読件数
  const [count, setCount] = useState(0);
  // 通知許可状態と前回取得した未読件数を保持する
  const [permission, setPermission] = useState(getNotificationPermission);
  // 通知許可を求める処理中か
  const [requesting, setRequesting] = useState(false);
  // 前回取得した未読件数と、複数の取得処理が重なった場合に最新の応答のみ反映するためのバージョン番号を保持する
  const previousCount = useRef(null);
  // 複数の取得処理が重なった場合に最新の応答のみ反映するためのバージョン番号を保持する
  const requestVersion = useRef(0);

  // ユーザーのボタン操作を契機としてブラウザに通知許可を求める
  async function handleEnableNotification() {
    if (requesting || getNotificationPermission() !== "default") return;
    setRequesting(true);
    try {
      const result = await window.Notification.requestPermission();
      setPermission(result);
      // 許可直後にも未読件数を取得し、未読があれば通知する
      if (result === "granted") {
        previousCount.current = null;
        window.dispatchEvent(new Event("cms-notifications-read"));
      }
    } catch (err) { console.error(err); }
    finally { setRequesting(false); }
  }

  useEffect(() => {
    if (!user) return;
    let active = true;
    const controller = new AbortController();
    previousCount.current = null;
    async function loadCount() {
      // 複数の取得処理が重なった場合は最新の応答のみ反映する
      const version = ++requestVersion.current;
      try {
        // 未読通知件数取得APIを呼び出す
        const response = await axios.get(
          "/api/notifications/unread-count",
          {
            signal: controller.signal
          }
        );
        if (!active || version !== requestVersion.current) return;
        const nextCount = response.data.unread_count;
        setCount(nextCount);
        // ブラウザ設定で許可状態が変更された場合も反映する
        const currentPermission = getNotificationPermission();
        setPermission(currentPermission);
        // 初回取得または未読件数が増加した場合のみ通知する
        if (currentPermission === "granted") {
          if (nextCount > 0 && (previousCount.current === null || nextCount > previousCount.current)) {
            showBrowserNotification(nextCount);
          }
          previousCount.current = nextCount;
        } else {
          previousCount.current = null;
        }
      } catch (err) { if (active) console.error(err); }
    }
    loadCount();
    // 画面表示中は定期的に未読件数を再取得する
    const timer = setInterval(loadCount, 30000);
    window.addEventListener("cms-notifications-read", loadCount);
    return () => { active = false; controller.abort(); clearInterval(timer); window.removeEventListener("cms-notifications-read", loadCount); };
  }, [user]);
  return <>
    <Link to="/notifications" aria-label={`通知：未読${count}件`}>通知 {count > 0 && <strong className="phase4-count">{count}</strong>}</Link>
    {/* 未選択の場合のみ通知許可ボタンを表示する */}
    {permission === "default" && <button type="button" className="phase4-notification-enable" disabled={requesting} onClick={handleEnableNotification}>ブラウザ通知を有効にする</button>}
  </>;
}
