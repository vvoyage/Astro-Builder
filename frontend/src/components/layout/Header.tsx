import { Link } from 'react-router-dom';
import { useAuth } from '@/auth/useAuth';

function hasAdminRole(user: ReturnType<typeof useAuth>['user']): boolean {
  if (!user) return false;
  const roles: unknown = (user.profile as Record<string, unknown>)?.realm_access;
  if (!roles || typeof roles !== 'object') return false;
  const roleList = (roles as { roles?: string[] }).roles ?? [];
  return roleList.includes('admin');
}

export default function Header() {
  const { user, logout } = useAuth();
  const isAdmin = hasAdminRole(user);

  return (
    <header className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
      <Link to="/dashboard" className="text-lg font-bold text-white">
        Astro Builder
      </Link>
      <div className="flex items-center gap-4">
        {isAdmin && (
          <Link
            to="/admin"
            className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            Админ
          </Link>
        )}
        <span className="text-sm text-gray-400">{user?.profile?.email}</span>
        <button
          onClick={logout}
          className="rounded px-3 py-1 text-sm text-gray-400 hover:text-white transition-colors"
        >
          Выйти
        </button>
      </div>
    </header>
  );
}
