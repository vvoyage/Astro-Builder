import { useEffect, useState } from 'react';
import Modal from '@/components/ui/Modal';
import type { AdminTemplate, TemplatePayload } from '@/api/admin';

interface TemplateFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: TemplatePayload) => void;
  loading?: boolean;
  initial?: AdminTemplate | null;
}

const EMPTY: TemplatePayload = {
  slug: '',
  name: '',
  text_prompt: '',
  description: '',
  is_active: true,
};

export default function TemplateFormModal({
  open,
  onClose,
  onSubmit,
  loading = false,
  initial = null,
}: TemplateFormModalProps) {
  const [form, setForm] = useState<TemplatePayload>(EMPTY);

  useEffect(() => {
    if (open) {
      setForm(
        initial
          ? {
              slug: initial.slug,
              name: initial.name,
              text_prompt: initial.text_prompt,
              description: initial.description ?? '',
              is_active: initial.is_active,
            }
          : EMPTY,
      );
    }
  }, [open, initial]);

  function field(key: keyof TemplatePayload) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit(form);
  }

  const inputCls =
    'w-full rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none';
  const labelCls = 'block mb-1 text-xs text-gray-400';

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={initial ? 'Редактировать шаблон' : 'Новый шаблон'}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={labelCls}>Название</label>
            <input
              required
              className={inputCls}
              value={form.name}
              onChange={field('name')}
              placeholder="Лендинг для кофейни"
            />
          </div>
          <div>
            <label className={labelCls}>Slug</label>
            <input
              required
              className={inputCls}
              value={form.slug}
              onChange={field('slug')}
              placeholder="coffee-landing"
              pattern="[a-z0-9\-]+"
              title="Только строчные буквы, цифры и дефис"
            />
          </div>
        </div>

        <div>
          <label className={labelCls}>Описание (необязательно)</label>
          <input
            className={inputCls}
            value={form.description ?? ''}
            onChange={field('description')}
            placeholder="Краткое описание шаблона"
          />
        </div>

        <div>
          <label className={labelCls}>Текст промпта</label>
          <textarea
            required
            rows={6}
            className={inputCls}
            value={form.text_prompt}
            onChange={field('text_prompt')}
            placeholder="Создай лендинг для кофейни с секциями: главная, меню, о нас, контакты..."
          />
        </div>

        <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
            className="rounded border-gray-600 bg-gray-800 accent-indigo-500"
          />
          Активен (отображается пользователям)
        </label>

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="rounded px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors disabled:opacity-50"
          >
            Отмена
          </button>
          <button
            type="submit"
            disabled={loading}
            className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-500 transition-colors disabled:opacity-50"
          >
            {loading ? 'Сохранение...' : initial ? 'Сохранить' : 'Создать'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
