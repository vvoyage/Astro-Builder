import { useState } from 'react';
import StatsCards from '@/components/admin/StatsCards';
import UserTable from '@/components/admin/UserTable';
import TemplatesTable from '@/components/admin/TemplatesTable';

type Tab = 'users' | 'templates' | 'stats';

const TAB_LABELS: Record<Tab, string> = {
  users: 'Пользователи',
  templates: 'Шаблоны',
  stats: 'Статистика',
};

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>('users');

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-white">Панель администратора</h1>

      <div className="flex gap-1 border-b border-gray-700">
        {(Object.keys(TAB_LABELS) as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              tab === t
                ? 'border-b-2 border-indigo-500 text-indigo-400'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      {tab === 'users' && <UserTable />}
      {tab === 'templates' && <TemplatesTable />}
      {tab === 'stats' && <StatsCards />}
    </div>
  );
}
