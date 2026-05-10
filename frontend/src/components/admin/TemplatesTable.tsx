import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  listAllTemplates,
  createTemplate,
  updateTemplate,
  deleteTemplate,
  type AdminTemplate,
  type TemplatePayload,
} from '@/api/admin';
import TemplateFormModal from './TemplateFormModal';
import ConfirmDeleteModal from './ConfirmDeleteModal';

export default function TemplatesTable() {
  const qc = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<AdminTemplate | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AdminTemplate | null>(null);

  const { data: templates = [], isLoading } = useQuery({
    queryKey: ['admin', 'templates'],
    queryFn: listAllTemplates,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['admin', 'templates'] });
    qc.invalidateQueries({ queryKey: ['templates'] }); // публичный кэш тоже
  };

  const createMut = useMutation({
    mutationFn: createTemplate,
    onSuccess: () => { invalidate(); setFormOpen(false); toast.success('Шаблон создан'); },
    onError: () => toast.error('Не удалось создать шаблон'),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: TemplatePayload }) =>
      updateTemplate(id, payload),
    onSuccess: () => { invalidate(); setEditing(null); toast.success('Шаблон сохранён'); },
    onError: () => toast.error('Не удалось сохранить шаблон'),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteTemplate(id),
    onSuccess: () => { invalidate(); setDeleteTarget(null); toast.success('Шаблон удалён'); },
    onError: () => toast.error('Не удалось удалить шаблон'),
  });

  function handleSubmit(payload: TemplatePayload) {
    if (editing) {
      updateMut.mutate({ id: editing.id, payload });
    } else {
      createMut.mutate(payload);
    }
  }

  const isSaving = createMut.isPending || updateMut.isPending;

  if (isLoading) return <p className="text-gray-400">Загрузка шаблонов...</p>;

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-400">Всего: {templates.length}</p>
        <button
          onClick={() => { setEditing(null); setFormOpen(true); }}
          className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-500 transition-colors"
        >
          + Новый шаблон
        </button>
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-700">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 text-gray-400">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Название</th>
              <th className="px-4 py-3 text-left font-medium">Slug</th>
              <th className="px-4 py-3 text-left font-medium">Описание</th>
              <th className="px-4 py-3 text-center font-medium">Активен</th>
              <th className="px-4 py-3 text-right font-medium">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700 bg-gray-900">
            {templates.map((t) => (
              <tr key={t.id} className="hover:bg-gray-800/60 transition-colors">
                <td className="px-4 py-3 text-gray-200 font-medium">{t.name}</td>
                <td className="px-4 py-3 font-mono text-xs text-gray-400">{t.slug}</td>
                <td className="px-4 py-3 text-gray-400 max-w-xs truncate">
                  {t.description ?? <span className="text-gray-600">—</span>}
                </td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      t.is_active
                        ? 'bg-green-900/50 text-green-400'
                        : 'bg-gray-700 text-gray-500'
                    }`}
                  >
                    {t.is_active ? 'Да' : 'Нет'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => { setEditing(t); setFormOpen(true); }}
                      className="rounded bg-gray-700 px-2 py-1 text-xs text-gray-300 hover:bg-gray-600 transition-colors"
                    >
                      Изменить
                    </button>
                    <button
                      onClick={() => setDeleteTarget(t)}
                      className="rounded bg-red-900/60 px-2 py-1 text-xs text-red-300 hover:bg-red-800/60 transition-colors"
                    >
                      Удалить
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {templates.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                  Шаблоны не добавлены
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <TemplateFormModal
        open={formOpen}
        onClose={() => { setFormOpen(false); setEditing(null); }}
        onSubmit={handleSubmit}
        loading={isSaving}
        initial={editing}
      />

      <ConfirmDeleteModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteMut.mutate(deleteTarget.id)}
        loading={deleteMut.isPending}
        title="Удалить шаблон"
        description={`Удалить шаблон «${deleteTarget?.name}»?`}
      />
    </>
  );
}
