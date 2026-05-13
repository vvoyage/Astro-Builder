import { useQuery } from '@tanstack/react-query';
import Modal from '@/components/ui/Modal';
import { getAdminUser } from '@/api/admin';

interface UserDetailModalProps {
  userId: string | null;
  onClose: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  ready: 'text-green-400',
  generating: 'text-yellow-400',
  building: 'text-blue-400',
  failed: 'text-red-400',
  queued: 'text-gray-400',
};

export default function UserDetailModal({ userId, onClose }: UserDetailModalProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'user', userId],
    queryFn: () => getAdminUser(userId!),
    enabled: !!userId,
  });

  return (
    <Modal open={!!userId} onClose={onClose} title="Детали пользователя">
      {isLoading && <p className="text-gray-400">Загрузка...</p>}
      {data && (
        <div className="space-y-4">
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Email</span>
              <span className="text-white">{data.email}</span>
            </div>
            {data.full_name && (
              <div className="flex justify-between">
                <span className="text-gray-400">Имя</span>
                <span className="text-white">{data.full_name}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-400">Статус</span>
              <span className={data.is_active ? 'text-green-400' : 'text-red-400'}>
                {data.is_active ? 'Активен' : 'Заблокирован'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">ID</span>
              <span className="font-mono text-xs text-gray-300">{data.id}</span>
            </div>
          </div>

          <div>
            <h4 className="mb-2 text-sm font-semibold text-gray-300">
              Проекты ({data.projects.length})
            </h4>
            {data.projects.length === 0 ? (
              <p className="text-sm text-gray-500">Нет проектов</p>
            ) : (
              <ul className="space-y-1 max-h-60 overflow-y-auto pr-1">
                {data.projects.map((p) => (
                  <li
                    key={p.id}
                    className="flex items-center justify-between rounded-lg bg-gray-800 px-3 py-2 text-sm"
                  >
                    <span className="truncate text-gray-200">{p.name}</span>
                    <span className={`ml-3 shrink-0 ${STATUS_COLORS[p.status] ?? 'text-gray-400'}`}>
                      {p.status}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}
