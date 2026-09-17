"use client";

import { useCallback, useEffect, useState } from "react";
import { apiClient, type ApiError } from "@/lib/api";
import type { UserRole } from "@/types";

interface ManagedUser {
  id: string;
  email: string;
  full_name: string;
  phone?: string | null;
  role: UserRole;
  branch_id?: string | null;
}

const ROLE_LABELS: Record<UserRole, string> = {
  customer: "Khách hàng",
  staff: "Nhân viên bán hàng",
  baker: "Thợ bánh",
  admin: "Quản lý",
};

export default function AdminUsersPage() {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState("");
  const [error, setError] = useState("");

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiClient.get<{ users: ManagedUser[] }>("/api/v1/admin/users");
      setUsers(response.users);
    } catch {
      setError("Không thể tải danh sách tài khoản.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  async function changeRole(user: ManagedUser, role: UserRole) {
    if (role === "admin" || user.role === role) return;
    setSavingId(user.id);
    setError("");
    try {
      const updated = await apiClient.patch<ManagedUser>(`/api/v1/admin/users/${user.id}/role`, { role });
      setUsers((current) => current.map((item) => (item.id === user.id ? { ...item, role: updated.role } : item)));
    } catch (err) {
      const detail = (err as ApiError)?.detail;
      setError(typeof detail === "string" ? detail : "Không thể cập nhật vai trò.");
    } finally {
      setSavingId("");
    }
  }

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-6">
        <h1 className="font-heading text-2xl font-bold text-ink">Quản lý nhân sự</h1>
        <p className="mt-1 text-sm text-muted">
          Phân tài khoản đã đăng ký thành nhân viên bán hàng hoặc thợ bánh.
        </p>
      </div>

      {error && <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

      {loading ? (
        <div className="rounded-2xl bg-white p-10 text-center text-muted">Đang tải tài khoản...</div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-line bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface/70 text-left text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-3">Họ tên</th>
                  <th className="px-4 py-3">Liên hệ</th>
                  <th className="px-4 py-3">Vai trò</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {users.map((user) => (
                  <tr key={user.id}>
                    <td className="px-4 py-4 font-medium text-ink">{user.full_name || "Chưa cập nhật"}</td>
                    <td className="px-4 py-4 text-muted">
                      <p>{user.email}</p>
                      {user.phone && <p className="text-xs">{user.phone}</p>}
                    </td>
                    <td className="px-4 py-4">
                      {user.role === "admin" ? (
                        <span className="rounded-full bg-subtle px-3 py-1.5 font-medium text-ink">Quản lý</span>
                      ) : (
                        <select
                          value={user.role}
                          disabled={savingId === user.id}
                          onChange={(event) => changeRole(user, event.target.value as UserRole)}
                          className="min-h-[40px] rounded-lg border border-line bg-white px-3 text-ink focus:border-brand focus:outline-none disabled:opacity-50"
                        >
                          <option value="customer">{ROLE_LABELS.customer}</option>
                          <option value="staff">{ROLE_LABELS.staff}</option>
                          <option value="baker">{ROLE_LABELS.baker}</option>
                        </select>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
