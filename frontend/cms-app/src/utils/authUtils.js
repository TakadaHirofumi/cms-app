/**
 * 認証情報の取得・権限判定の共通処理
 */
import { createContext, useContext } from "react";

// 認証情報を共有するコンテキスト
export const AuthContext = createContext(null);

/**
 * ログインユーザーの認証情報を取得する
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("AuthProviderの内側で使用してください。");
  return context;
}

/**
 * ADMINは全記事、EDITORは本人の記事だけ編集可能
 */
export function canEditArticle(user, article) {
  return Boolean(user && article && (user.role === "ADMIN" ||
    (user.role === "EDITOR" && user.id === article.author_user_id)));
}
