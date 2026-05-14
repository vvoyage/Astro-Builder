import { create } from 'zustand';
import { saveFile as saveFileApi, getFile } from '@/api/editor';

interface EditorStore {
  projectId: string | null;
  files: string[];
  currentFile: string | null;
  fileContent: string;
  isDirty: boolean;
  isEditing: boolean;
  isBuilding: boolean;
  previewUrl: string | null;
  activeSnapshotVersion: number | null;
  selectedElement: { editable_id: string; file_path: string; element_html: string } | null;

  setProjectId: (id: string) => void;
  setFiles: (files: string[]) => void;
  setCurrentFile: (path: string) => void;
  setFileContent: (content: string) => void;
  setPreviewUrl: (url: string | null) => void;
  setIsEditing: (v: boolean) => void;
  setIsBuilding: (v: boolean) => void;
  setActiveSnapshotVersion: (version: number | null) => void;
  setSelectedElement: (el: { editable_id: string; file_path: string; element_html: string } | null) => void;
  saveFile: () => Promise<void>;
  loadFile: (path: string) => Promise<void>;
  reloadCurrentFile: () => Promise<void>;
  refreshPreview: (newUrl?: string) => void;
}

export const useEditorStore = create<EditorStore>((set, get) => ({
  projectId: null,
  files: [],
  currentFile: null,
  fileContent: '',
  isDirty: false,
  isEditing: false,
  isBuilding: false,
  previewUrl: null,
  activeSnapshotVersion: null,
  selectedElement: null,

  setProjectId: (id) => set({ projectId: id }),
  setFiles: (files) => set({ files }),
  setCurrentFile: (path) => set({ currentFile: path, isDirty: false }),
  setFileContent: (content) => set({ fileContent: content, isDirty: true }),
  setPreviewUrl: (url) => set({ previewUrl: url }),
  setIsEditing: (v) => set({ isEditing: v }),
  setIsBuilding: (v) => set({ isBuilding: v }),
  setActiveSnapshotVersion: (version) => set({ activeSnapshotVersion: version }),
  setSelectedElement: (el) => set({ selectedElement: el }),

  saveFile: async () => {
    const { projectId, currentFile, fileContent } = get();
    if (!projectId || !currentFile) return;
    await saveFileApi(projectId, currentFile, fileContent);
    set({ isDirty: false });
  },

  loadFile: async (path: string) => {
    const { projectId } = get();
    if (!projectId) return;
    
    // Проверяем, является ли файл страницей Astro, чтобы обновить превью
    if (path.startsWith('src/pages/') && path.endsWith('.astro')) {
      const { previewUrl } = get();
      if (previewUrl) {
        const pageName = path.replace('src/pages/', '').replace('.astro', '');
        const baseUrlMatch = previewUrl.match(/^(.*\/build)/);
        
        if (baseUrlMatch) {
          const baseUrl = baseUrlMatch[1];
          let newPreviewUrl = `${baseUrl}/index.html`;
          
          if (pageName !== 'index') {
            newPreviewUrl = `${baseUrl}/${pageName}/index.html`;
          }
          
          const cacheBusterMatch = previewUrl.match(/(\?t=\d+)/);
          if (cacheBusterMatch) {
            newPreviewUrl += cacheBusterMatch[1];
          }
          
          set({ previewUrl: newPreviewUrl });
        }
      }
    }

    set({ currentFile: path, isDirty: false });
    try {
      const fc = await getFile(projectId, path);
      set({ fileContent: fc.content });
    } catch {
      console.error(`Не удалось загрузить файл: ${path}`);
    }
  },

  reloadCurrentFile: async () => {
    const { projectId, currentFile } = get();
    if (!projectId || !currentFile) return;
    const fc = await getFile(projectId, currentFile);
    set({ fileContent: fc.content, isDirty: false });
  },

  refreshPreview: (newUrl?: string) => {
    let base = (get().previewUrl ?? newUrl ?? '').split('?')[0];
    
    // Если мы обновляем URL после завершения сборки, но в данный момент находимся на подстранице,
    // мы должны попытаться сохранить эту подстраницу в новом URL, если новый URL указывает только на главную (index.html).
    if (newUrl && base && newUrl !== base && newUrl.endsWith('/build/index.html') && !base.endsWith('/build/index.html')) {
      // Сохраняем базовый URL текущей подстраницы
    } else if (newUrl) {
      base = newUrl.split('?')[0];
    }
    
    if (!base) return;
    set({ previewUrl: `${base}?t=${Date.now()}` });
  },
}));
