import { useQuery } from '@tanstack/react-query';
import { getAdminStats } from '@/api/admin';

function Card({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-gray-700 bg-gray-800 p-5">
      <p className="text-sm text-gray-400">{label}</p>
      <p className="mt-1 text-3xl font-bold text-white">{value}</p>
    </div>
  );
}

export default function StatsCards() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: getAdminStats,
  });

  if (isLoading) {
    return <p className="text-gray-400">Загрузка статистики...</p>;
  }

  if (isError || !data) {
    return <p className="text-red-400">Не удалось загрузить статистику</p>;
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card label="Пользователей" value={data.total_users} />
        <Card label="Проектов" value={data.total_projects} />
        <Card label="Шаблонов" value={data.total_templates} />
        <Card label="Статусов" value={data.projects_by_status.length} />
      </div>

      {data.projects_by_status.length > 0 && (
        <div className="rounded-xl border border-gray-700 bg-gray-800 p-5">
          <h3 className="mb-3 text-sm font-semibold text-gray-300">Проекты по статусу</h3>
          <div className="flex flex-wrap gap-3">
            {data.projects_by_status.map((s) => (
              <div
                key={s.status}
                className="flex items-center gap-2 rounded-lg bg-gray-700 px-3 py-2 text-sm"
              >
                <span className="text-gray-300">{s.status}</span>
                <span className="font-semibold text-white">{s.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
