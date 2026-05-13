import Modal from '@/components/ui/Modal';

interface ConfirmDeleteModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title?: string;
  description?: string;
  loading?: boolean;
}

export default function ConfirmDeleteModal({
  open,
  onClose,
  onConfirm,
  title = 'Подтверждение удаления',
  description = 'Это действие необратимо. Продолжить?',
  loading = false,
}: ConfirmDeleteModalProps) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="text-sm text-gray-300">{description}</p>
      <div className="mt-6 flex justify-end gap-3">
        <button
          onClick={onClose}
          disabled={loading}
          className="rounded px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors disabled:opacity-50"
        >
          Отмена
        </button>
        <button
          onClick={onConfirm}
          disabled={loading}
          className="rounded bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-500 transition-colors disabled:opacity-50"
        >
          {loading ? 'Удаление...' : 'Удалить'}
        </button>
      </div>
    </Modal>
  );
}
