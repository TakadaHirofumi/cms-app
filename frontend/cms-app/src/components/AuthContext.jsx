/**
 * JWT認証情報
 */
import { useEffect, useState } from "react";
import axios from "axios";
import { AuthContext } from "../utils/authUtils";


// JWTを保存するキー名
const TOKEN_KEY = "cms_access_token";

// API呼び出し時に保存済みJWTをAuthorizationヘッダーへ設定する
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 認証済みAPIで401エラーが発生した場合、JWTを破棄してログイン画面へ遷移する
axios.interceptors.response.use(
  (response) => response,
  (err) => {
    const token = localStorage.getItem(TOKEN_KEY);
    // 現在保持しているJWTを使用したAPIで401エラーが発生した場合
    if (
      err.response?.status === 401 &&
      token &&
      err.config?.headers?.Authorization === `Bearer ${token}`
    ) {
      // 有効期限切れなどで無効になったJWTを削除する
      localStorage.removeItem(TOKEN_KEY);
      // ログイン画面へ遷移する
      window.location.replace("/");
    }
    // 呼び出し元の例外処理へエラーを返す
    return Promise.reject(err);
  }
);

export function AuthProvider({ children }) {
  // ログインユーザーと認証情報の取得状態
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  // 画面再読み込み時に保存済みJWTの有効性をサーバーで検証する
  useEffect(() => {
    const controller = new AbortController();
    async function restoreLogin() {
      if (!localStorage.getItem(TOKEN_KEY)) { setLoading(false); return; }
      try {
        // ログインユーザー情報取得APIを呼び出す
        const response = await axios.get(
          "/api/auth/me",
          {
            signal: controller.signal
          }
        );
        if (!controller.signal.aborted) setUser(response.data);
      } catch (err) {
        if (!controller.signal.aborted) {
          if (err.response?.status === 401) localStorage.removeItem(TOKEN_KEY);
          setUser(null);
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    restoreLogin();
    return () => controller.abort();
  }, []);

  // ログインAPIから受け取ったJWTを保存してユーザー情報を取得する
  async function login(email, password) {
    // ログイン検証APIを呼び出す
    const response = await axios.post(
      "/api/auth/login",
      {
        email,
        password
      }
    );
    localStorage.setItem(TOKEN_KEY, response.data.access_token);
    try {
      // ログインユーザー情報取得APIを呼び出す
      const current = await axios.get(
        "/api/auth/me"
      );
      setUser(current.data);
      return current.data;
    } catch (err) {
      localStorage.removeItem(TOKEN_KEY);
      setUser(null);
      throw err;
    }
  }

  // ログアウト時はJWTを破棄し、表示中のユーザー情報を消去する
  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, loading, login, logout }}>
    {children}
  </AuthContext.Provider>;
}
