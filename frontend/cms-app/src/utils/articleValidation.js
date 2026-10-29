/**
 * 記事作成・編集画面共通の入力チェック
 */


// 記事タイトルの最大文字数
export const TITLE_MAX_LENGTH = 200;
// 記事タイトルが空欄である場合のエラーメッセージ
export const TITLE_REQUIRED_ERROR = "タイトルを入力してください。";
// 記事タイトルが201文字以上である場合のエラーメッセージ
export const TITLE_LENGTH_ERROR = "タイトルに201文字以上入力されているため、200文字までに減らして入力してください。";
// スラッグの最大文字数
export const SLUG_MAX_LENGTH = 200;
// スラッグが空欄である場合のエラーメッセージ
export const SLUG_REQUIRED_ERROR = "スラッグを入力してください。";
// スラッグが201文字以上である場合のエラーメッセージ
export const SLUG_LENGTH_ERROR = "スラッグに201文字以上入力されているため、200文字までに減らして入力してください。";
// スラッグに使用できない文字が含まれている場合のエラーメッセージ
export const SLUG_FORMAT_ERROR = "スラッグは半角英数字とハイフンのみ入力してください。";

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
 * スラッグの入力チェック
 *
 * @param {string} slug - 入力されたスラッグ
 * @returns {string} エラーメッセージ
 *                   正常な場合は空文字
 */
export const validateArticleSlug = (slug) => {
  // 必須チェック
  if (!slug.trim()) {
    return SLUG_REQUIRED_ERROR;
  }

  // 文字数チェック
  if (slug.length > SLUG_MAX_LENGTH) {
    return SLUG_LENGTH_ERROR;
  }

  // 半角英数字・ハイフンの入力チェック
  if (!/^[A-Za-z0-9-]+$/.test(slug)) {
    return SLUG_FORMAT_ERROR;
  }
  return "";
};

/**
 * タイトルからスラッグを自動生成
 *
 * @param {string} title - 入力されたタイトル
 * @returns {string} 生成したスラッグ
 */
export const generateSlug = (title) => {
  // 英数字を半角に変換し、小文字に統一
  return title.normalize("NFKC").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "")
    .slice(0, SLUG_MAX_LENGTH).replace(/-+$/g, "");
};

/**
 * 記事全体の入力チェック
 */
export const validateArticle = (article) => {
  return {
    title: validateArticleTitle(article.title),
    slug: validateArticleSlug(article.slug),
  };
};
