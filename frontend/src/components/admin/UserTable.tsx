import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { listAdminUsers, patchAdminUser, deleteAdminUser, type AdminUserItem } from '@/api/admin';
import ConfirmDeleteModal from './ConfirmDeleteModal';
import UserDetailModal from './UserDetailModal';

const PAGE_SIZE = 50;

export default function UserTable() {
  const qc = useQueryClient();
  const [page, setPage] = useState(0);
  const [detailUserId, setDetailUserId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AdminUserItem | null>(null);

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['admin', 'users', page],
    queryFn: () => listAdminUsers(page * PAGE_SIZE, PAGE_SIZE),
  });

  const banMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      patchAdminUser(id, { is_active }),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ['admin', 'users'] });
      qc.invalidateQueries({ queryKey: ['admin', 'user', id] });
      toast.success('Статус обновлён');
    },
    onError: () => toast.error('Не удалось обновить статус'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAdminUser(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'users'] });
      qc.invalidateQueries({ queryKey: ['admin', 'stats'] });
      setDeleteTarget(null);
      toast.success('Пользователь удалён');
    },
    onError: () => toast.error('Не удалось удалить пользователя'),
  });

  if (isLoading) {
    return <p className="text-gray-400">Загрузка...</p>;
  }

  return (
    <>
      <div className="overflow-x-auto rounded-xl border border-gray-700">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 text-gray-400">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Email</th>
              <th className="px-4 py-3 text-left font-medium">Имя</th>
              <th className="px-4 py-3 text-center font-medium">Проекты</th>
              <th className="px-4 py-3 text-center font-medium">Статус</th>
              <th className="px-4 py-3 text-right font-medium">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700 bg-gray-900">
            {users.map((u) => (
              <tr
                key={u.id}
                className="cursor-pointer hover:bg-gray-800/60 transition-colors"
                onClick={() => setDetailUserId(u.id)}
              >
                <td className="px-4 py-3 text-gray-200">{u.email}</td>
                <td className="px-4 py-3 text-gray-400">{u.full_name ?? '—'}</td>
                <td className="px-4 py-3 text-center text-gray-300">{u.project_count}</td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      u.is_active
                        ? 'bg-green-900/50 text-green-400'
                        : 'bg-red-900/50 text-red-400'
                    }`}
                  >
                    {u.is_active ? 'Активен' : 'Заблокирован'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div
                    className="flex justify-end gap-2"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      onClick={() => banMutation.mutate({ id: u.id, is_active: !u.is_active })}
                      disabled={banMutation.isPending}
                      className={`rounded px-2 py-1 text-xs transition-colors disabled:opacity-50 ${
                        u.is_active
                          ? 'bg-yellow-800/60 text-yellow-300 hover:bg-yellow-700/60'
                          : 'bg-green-800/60 text-green-300 hover:bg-green-700/60'
                      }`}
                    >
                      {u.is_active ? 'Бан' : 'Разбан'}
                    </button>
                    <button
                      onClick={() => setDeleteTarget(u)}
                      className="rounded bg-red-900/60 px-2 py-1 text-xs text-red-300 hover:bg-red-800/60 transition-colors"
                    >
                      Удалить
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                  Пользователи не найдены
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex items-center justify-between text-sm text-gray-400">
        <button
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          disabled={page === 0}
          className="rounded px-3 py-1 hover:text-white disabled:opacity-40 transition-colors"
        >
          ← Назад
        </button>
        <span>Страница {page + 1}</span>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={users.length < PAGE_SIZE}
          className="rounded px-3 py-1 hover:text-white disabled:opacity-40 transition-colors"
        >
          Вперёд →
        </button>
      </div>

      <UserDetailModal userId={detailUserId} onClose={() => setDetailUserId(null)} />

      <ConfirmDeleteModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
        title="Удалить пользователя"
        description={`Удалить ${deleteTarget?.email}? Все его проекты и файлы будут безвозвратно удалены.`}
      />
    </>
  );
}
