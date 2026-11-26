/**
 * ADMIN専用のユーザー一覧・権限変更画面
 */
import { useEffect, useState } from "react";
import axios from "axios";
import { useAuth } from "../utils/authUtils";
import "./UserManagement.css";


export default function UserManagement() {
  // ログインユーザー情報
  const { user } = useAuth();
  // ユーザー一覧
  const [users, setUsers] = useState([]);
  // ロード中の状態
  const [loading, setLoading] = useState(true);
  // 権限変更中のユーザーID
  const [changingId, setChangingId] = useState(null);
  // APIエラー
  const [error, setError] = useState("");
  // ユーザー一覧を再取得するためのバージョン番号
  const [reloadVersion, setReloadVersion] = useState(0);

  // ADMIN権限でユーザー一覧を取得する
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true); setError("");
      try {
        // ユーザー一覧取得APIを呼び出す
        const response = await axios.get(
          "/api/users",
          {
            signal: controller.signal
          }
        );
        if (!controller.signal.aborted) setUsers(response.data);
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error(err);
          setError("ユーザー一覧の取得に失敗しました。");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, [reloadVersion]);

  // 自分自身のADMIN権限は変更せず、APIで指定ユーザーの権限を更新する
  async function handleRoleChange(target, role) {
    if (changingId !== null || target.role === role || target.id === user.id) return;
    if (!window.confirm(`${target.display_name}の権限を${role}に変更しますか？`)) return;
    setChangingId(target.id); setError("");
    try {
      // ユーザー権限変更APIを呼び出す
      await axios.patch(
        `/api/users/${target.id}/role`,
        {
          role
        }
      );
      setReloadVersion((value) => value + 1);
    } catch (err) {
      console.error(err);
      setError("権限変更に失敗しました。");
    } finally {
      setChangingId(null);
    }
  }

  return <main className="phase4-page">
    <h1>ユーザー管理</h1>
    {error && <p className="phase4-error" role="alert">{error}</p>}
    {loading ? <p>読み込み中...</p> : <div className="phase4-table-scroll"><table className="phase4-table">
      <thead><tr><th>ID</th><th>表示名</th><th>メールアドレス</th><th>権限</th></tr></thead>
      <tbody>{users.map((item) => <tr key={item.id}>
        <td>{item.id}</td><td>{item.display_name}</td><td>{item.email}</td>
        <td><select aria-label={`${item.display_name}の権限`} value={item.role}
          disabled={changingId !== null || item.id === user.id}
          onChange={(event) => handleRoleChange(item, event.target.value)}>
          <option value="VIEWER">VIEWER</option><option value="EDITOR">EDITOR</option><option value="ADMIN">ADMIN</option>
        </select>{item.id === user.id && "（自分）"}</td>
      </tr>)}</tbody>
    </table></div>}
  </main>;
}
