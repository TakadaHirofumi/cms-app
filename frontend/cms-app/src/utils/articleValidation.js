/**
 * 記事作成・編集画面共通の入力チェック
 */
export const TITLE_MAX_LENGTH = 200;
export const TITLE_REQUIRED_ERROR = "タイトルを入力してください。";
export const TITLE_LENGTH_ERROR = "タイトルに201文字以上入力されているため、200文字までに減らして入力してください。";

/**
 * タイトルの入力チェック
 *
 * @param {string} title - 入力されたタイトル
 * @returns {string} エラーメッセージ
 *                   正常な場合は空文字
 */
export const validateArticleTitle = (title) => {
  // 必須チェック
  if (!title.trim()) {
    return TITLE_REQUIRED_ERROR;
  }

  // 文字数チェック
  if (Array.from(title).length > TITLE_MAX_LENGTH) {
    return TITLE_LENGTH_ERROR;
  }
  return "";
};

/**
 * 記事全体の入力チェック
 *
 * 将来的に本文やカテゴリの入力チェックを
 * 追加することを想定
 */
export const validateArticle = (article) => {
  return {
    title: validateArticleTitle(article.title),
  };
};
