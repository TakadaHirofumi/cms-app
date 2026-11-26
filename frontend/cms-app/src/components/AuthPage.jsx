/**
 * ユーザー登録・ログイン画面
 */
import { useState } from "react";
import { useNavigate, Link, Navigate } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../utils/authUtils";
import "./AuthPage.css";


// 画面切り替え時にフォームのstateを初期化する
export default function AuthPage({ register = false }) {
  return <AuthForm key={register ? "register" : "login"} register={register} />;
}

function AuthForm({ register }) {
  // 認証情報とログイン関数を取得
  const { user, loading, login } = useAuth();
  // メールアドレスフォームの状態
  const [email, setEmail] = useState("");
  // パスワードフォームの状態
  const [password, setPassword] = useState("");
  // 表示名フォームの状態（登録時のみ）
  const [displayName, setDisplayName] = useState("");
  // エラーメッセージ
  const [error, setError] = useState([]);
  // 送信中状態
  const [saving, setSaving] = useState(false);
  // 各画面への遷移
  const navigate = useNavigate();

  // 登録時はユーザーを作成し、続けてログインする
  async function handleSubmit(event) {
    event.preventDefault();
    if (saving) return;
    // 入力エラーを項目ごとに収集する
    const errors = [];
    if (register) {
      if (!displayName.trim()) errors.push("表示名を入力してください。");
      else if ([...displayName.trim()].length > 100) errors.push("表示名は100文字以内で入力してください。");
    }
    if (!email.trim()) errors.push("メールアドレスを入力してください。");
    else if (register && [...email.trim().toLowerCase()].length > 255) errors.push("メールアドレスは255文字以内で入力してください。");
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) errors.push("有効なメールアドレスを入力してください。");
    if (!password) errors.push("パスワードを入力してください。");
    else if (register) {
      if ([...password].length > 72) errors.push("パスワードは72文字以内で入力してください。");
      else if (new TextEncoder().encode(password).length > 72) errors.push("パスワードはUTF-8で72バイト以内で入力してください。");
      else if ([...password].length < 8 || !/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) errors.push("パスワードは8文字以上で英字と数字を含めてください。");
    }
    setError(errors);
    if (errors.length > 0) return;
    setSaving(true);
    try {
      // ユーザー登録APIを呼び出す
      if (register) await axios.post(
        "/api/auth/register",
        {
          email: email.trim(),
          password,
          display_name: displayName.trim()
        }
      );
      await login(email.trim(), password);
      // ログイン後は記事一覧画面へ遷移する
      navigate("/articles", { replace: true });
    } catch (err) {
      console.error(err);
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? [detail] : Array.isArray(detail) ?
        detail.map((item) => String(item.msg || "入力内容を確認してください。").replace(/^Value error, /, "")) :
        ["登録またはログインに失敗しました。入力内容を確認してください。"]);
    } finally {
      setSaving(false);
    }
  }

  // 認証済みの場合はログイン、記事一覧画面へ遷移する
  if (loading) return <main className="phase4-page phase4-auth-page"><p>認証情報を確認中...</p></main>;
  if (user) return <Navigate to="/articles" replace />;

  return <main className="phase4-page phase4-auth-page">
    <h1>{register ? "新規ユーザー登録" : "ログイン"}</h1>
    {error.map((message, index) => <p key={index} className="phase4-error" role="alert">{message}</p>)}
    <form className="phase4-form" onSubmit={handleSubmit} noValidate>
      {register && <label>表示名<input value={displayName} onChange={(e) => setDisplayName(e.target.value)} required /></label>}
      {register && <small>100文字以内</small>}
      <label>メールアドレス<input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
      <label>パスワード<input type="password" autoComplete={register ? "new-password" : "current-password"} value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
      {register && <small>8文字以上72文字以内（UTF-8で72バイト以内）、英字と数字を含めて入力してください。</small>}
      <button type="submit" disabled={saving}>{saving ? "処理中..." : register ? "登録してログイン" : "ログイン"}</button>
    </form>
    <p className="phase4-auth-link">{register ? <Link to="/">ログイン画面へ</Link> : <Link to="/register">新規ユーザー登録</Link>}</p>
    {/* 未ログインでも記事一覧画面へ遷移できるようにする */}
    {!register && <button type="button" className="phase4-guest-button" disabled={saving} onClick={() => navigate("/articles")}>ログインせずに記事一覧へ</button>}
  </main>;
}
