import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface EditorSettings {
  fontSize: number;
  tabSize: number;
  wordWrap: "on" | "off" | "wordWrapColumn" | "bounded";
  minimap: boolean;
  lineNumbers: "on" | "off" | "relative" | "interval";
  scrollBeyondLastLine: boolean;
}

export interface KeybindingEntry {
  id: string;
  label: string;
  keys: string[];
  context: string;
}

export const DEFAULT_KEYBINDINGS: KeybindingEntry[] = [
  { id: "save", label: "Save file", keys: ["Ctrl+S", "Cmd+S"], context: "editor" },
  { id: "send", label: "Send message", keys: ["Enter"], context: "chat" },
  { id: "newline", label: "New line in chat", keys: ["Shift+Enter"], context: "chat" },
  { id: "toggle-sidebar", label: "Toggle sidebar", keys: ["Ctrl+B", "Cmd+B"], context: "global" },
];

interface SettingsState {
  editor: EditorSettings;
  updateEditor: (settings: Partial<EditorSettings>) => void;
  resetEditor: () => void;
}

const defaultEditorSettings: EditorSettings = {
  fontSize: 13,
  tabSize: 2,
  wordWrap: "on",
  minimap: false,
  lineNumbers: "on",
  scrollBeyondLastLine: false,
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      editor: { ...defaultEditorSettings },
      updateEditor: (settings) =>
        set((state) => ({ editor: { ...state.editor, ...settings } })),
      resetEditor: () => set({ editor: { ...defaultEditorSettings } }),
    }),
    {
      name: "cran-settings",
      partialize: (state) => ({ editor: state.editor }),
    },
  ),
);
