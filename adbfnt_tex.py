import tkinter as tk
from tkinter import messagebox
import xml.etree.ElementTree as ET
import os

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("フォントメンテナー")
        self.root.geometry("800x450")

        # --- 1. メニューの作成 ---
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        
        # ファイルメニュー
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        # 「フォント読み込み」を追加
        file_menu.add_command(label="フォント読み込み", command=self.load_fonts)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=root.quit)
        self.menu_bar.add_cascade(label="ファイル", menu=file_menu)

        # --- 2. PanedWindow (左右分割) ---
        self.paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # --- 3. 左フレーム (Listbox) ---
        self.left_frame = tk.Frame(self.paned)
        self.paned.add(self.left_frame, width=550)

        self.listbox = tk.Listbox(self.left_frame, font=("MS Gothic", 10))
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 【動作】Listboxで要素を選択したときにLabelを更新するバインド
        self.listbox.bind('<<ListboxSelect>>', self.update_label)

        # --- 4. 右フレーム (ステータス表示 & ボタン) ---
        self.right_frame = tk.Frame(self.paned)
        self.paned.add(self.right_frame)

        # 複数行ラベル
        self.status_label = tk.Label(
            self.right_frame, 
            text="メニューから「フォント読み込み」を選択して、\nフォント情報を読み込んでください。", 
            justify=tk.LEFT, 
            anchor="nw",
            relief=tk.RIDGE,
            padx=10, pady=10,
            bg="white"
        )
        self.status_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 【動作】ボタンを押したときの処理
        self.action_button = tk.Button(
            self.right_frame, 
            text="選択項目の処理を実行", 
            command=self.execute_action,
            height=2
        )
        self.action_button.pack(fill=tk.X, padx=10, pady=10)

    def _make_adb_fnt_paths(self, id, name):
        orig_path_r = os.path.expandvars(r"%APPDATA%\Adobe\CoreSync\plugins\livetype\r") + "\\" + id
        orig_path_w = os.path.expandvars(r"%APPDATA%\Adobe\CoreSync\plugins\livetype\w") + "\\" + id
        return [orig_path_r, orig_path_w]
    
    def _find_adb_fnt(self, id, name):
        paths = self._make_adb_fnt_paths(id, name)
        for path in paths:
            if os.path.exists(path):
                return path
        return None
    
    def _is_otf(self, fname):
        with open(fname, "rb") as f:
            first_byte = f.read(1)
            return (first_byte != b'\x00')
    
    def _make_hardlink_path(self, name, is_otf):
        return os.path.expandvars(r"%TL_ROOT%/../texmf-local/fonts/truetype/adobe") + "\\" + name + (".otf" if is_otf else ".ttf")
    
    def _find_hardlink(self, name):
        # otf
        hardlink_path_otf = self._make_hardlink_path(name, is_otf=True)
        if os.path.exists(hardlink_path_otf):
            return hardlink_path_otf
        hardlink_path_ttf = self._make_hardlink_path(name, is_otf=False)
        if os.path.exists(hardlink_path_ttf):
            return hardlink_path_ttf
        return None
    
    def _create_hardlink(self, id, name):
        found_hardlink = self._find_hardlink(name)
        if found_hardlink:
            return found_hardlink
        
        orig_path = self._find_adb_fnt(id, name)
        if not orig_path:
            return None
        is_otf = self._is_otf(orig_path)

        hardlink_path = self._make_hardlink_path(name, is_otf)

        if not os.path.exists(hardlink_path):
            os.link(orig_path, hardlink_path)
        
        return hardlink_path

    def _load_adb_fnt_info(self, id, name):
        orig_path = self._find_adb_fnt(id, name)
        hardlink_path = self._find_hardlink(name)
        return {
            "id": id,
            "name": name,
            "orig_path": orig_path,
            "hardlink_path": hardlink_path,
            "is_otf": self._is_otf(orig_path) if orig_path else None
            }

    # --- 5. 各処理のメソッド定義 ---
    def _load_adb_xml(self):
        font_list = []
        adb_xml_path = os.path.expandvars(r"%APPDATA%\Adobe\CoreSync\plugins\livetype\c\entitlements.xml")
        tree = ET.parse(adb_xml_path)
        root = tree.getroot()
        fonts = root.findall(".//fonts/font")
        for font in fonts:
            id = font.find("id").text
            name = font.find("properties/fullName").text
            info = self._load_adb_fnt_info(id, name)
            font_list.append(info)
        return font_list

    _font_list = []

    def load_fonts(self):
        # メニュー：フォント読み込みの処理（仮）
        # ここにフォント読み込みのロジックを記述
        print("システムからフォントを読み込み中...")
        self._font_list = self._load_adb_xml()
        # Listboxをクリアしてから新しいフォント情報を追加
        self.listbox.delete(0, tk.END)
        for font_info in self._font_list:
            display_name = font_info["name"]
            # orig_pathが存在しない場合は赤で表示して末尾に「（未インストール）」を追加
            if not font_info["orig_path"]:
                display_name += "（未インストール）"
                self.listbox.insert(tk.END, display_name)
                self.listbox.itemconfig(tk.END, fg="red")
            # ハードリンクが存在する場合は黒、存在しない場合は赤かつ末尾に「（未リンク）」で表示
            elif font_info["hardlink_path"]:
                self.listbox.insert(tk.END, display_name)
            else:
                self.listbox.insert(tk.END, display_name + "（未リンク）")
                self.listbox.itemconfig(tk.END, fg="red")
        self.status_label.config(text="左のリストから項目を選択してください。")
        self.action_button.config(state=tk.DISABLED)
        self.listbox.selection_clear(0, tk.END)

    def update_label(self, event):
        # Listbox選択時にラベルを更新する処理
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            selected_item = self._font_list[index]
            
            # 詳細テキスト
            text = f"""ID: {selected_item['id']}
Name: {selected_item['name']}"""
            if not selected_item['orig_path']:
                text += "\nStatus: フォントが見つかりません。Adobe Fontsからインストールしてください。"
                self.action_button.config(state=tk.DISABLED)
            else:
                text += "\nFontType: " + ("OTF" if selected_item['is_otf'] else "TTF")
                if not selected_item['hardlink_path']:
                    text += "\nStatus: 未リンク。リンク作成が可能です"
                    self.action_button.config(state=tk.NORMAL)
                else:
                    self.action_button.config(state=tk.DISABLED)
                self.status_label.config(text=text)
        else:
            self.status_label.config(text="左のリストから項目を選択してください。")
            self.action_button.config(state=tk.DISABLED)

    def execute_action(self):
        """ボタン押下時の処理"""
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("注意", "まずはリストから項目を選択してください。")
            return
        
        selected_item = self._font_list[selection[0]]
        self._create_hardlink(selected_item['id'], selected_item['name'])
        self.load_fonts()
        print(f"Executing process for: {selected_item['name']}")
        messagebox.showinfo("実行", f"「{selected_item['name']}」に対する処理を完了しました。")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()