import os
import tkinter as tk
from tkinter import ttk
from datetime import datetime

# File extensions to show
ALL_EXTS = [".wav", ".mp4"]

def populate_tree(media_dir, tree, allowed_exts, show_subdirs=False):
    """Populate the treeview with files and optionally subdirectories."""
    # Clear existing items
    for item in tree.get_children():
        tree.delete(item)

    if not os.path.exists(media_dir):
        return

    # Populate based on mode
    if show_subdirs:
        # Show animal folders and allow expansion
        for subfolder in sorted(os.listdir(media_dir)):
            subpath = os.path.join(media_dir, subfolder)
            if os.path.isdir(subpath):
                folder_id = tree.insert("", "end", text=subfolder, values=("", "Folder", ""))
                # Add placeholder so it can be expanded
                tree.insert(folder_id, "end", text="Loading...", values=("", "", ""))
    else:
        # Regular folder — show files directly
        for file in sorted(os.listdir(media_dir)):
            full_path = os.path.join(media_dir, file)
            if os.path.isfile(full_path) and os.path.splitext(file)[1].lower() in allowed_exts:
                stats = os.stat(full_path)
                size_kb = stats.st_size // 1024
                mtime = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                ftype = os.path.splitext(file)[1].replace('.', '').upper()
                tree.insert("", "end", text=file, values=(f"{size_kb} KB", ftype, mtime))

def populate_subfolder(tree, parent_id, folder_path):
    """When a folder node is expanded, populate it with media files."""
    # Clear the placeholder
    for child in tree.get_children(parent_id):
        tree.delete(child)

    # Add files inside that folder
    for file in sorted(os.listdir(folder_path)):
        full_path = os.path.join(folder_path, file)
        if os.path.isfile(full_path) and os.path.splitext(file)[1].lower() in ALL_EXTS:
            stats = os.stat(full_path)
            size_kb = stats.st_size // 1024
            mtime = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            ftype = os.path.splitext(file)[1].replace('.', '').upper()
            tree.insert(parent_id, "end", text=file, values=(f"{size_kb} KB", ftype, mtime))

def tree_open_file(event, base_dir, tree):
    """Open a file when double-clicked in the tree."""
    item_id = tree.focus()
    if not item_id:
        return
    filename = tree.item(item_id, "text")

    # Build full path by walking up the tree hierarchy
    path_parts = [filename]
    parent = tree.parent(item_id)
    while parent:
        path_parts.insert(0, tree.item(parent, "text"))
        parent = tree.parent(parent)
    file_path = os.path.join(base_dir, *path_parts)

    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            os.startfile(file_path)  # Windows only
        except AttributeError:
            import subprocess, platform
            if platform.system() == "Darwin":
                subprocess.call(["open", file_path])
            else:
                subprocess.call(["xdg-open", file_path])

class Captures(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # Define all top-level folders
        self.folder_map = {
            "Audio Detections": "./media/audio_detections",
            "Visual Detections": "./media/visual_detections",
            "Audio Recordings": "./media/recordings/audio",
            "Video Recordings": "./media/recordings/video"
        }

        self.current_folder = "Audio Detections"
        self.buttons = {}

        # Top button bar
        button_frame = tk.Frame(self)
        button_frame.pack(side="top", fill="x", pady=10)

        inner_button_frame = tk.Frame(button_frame)
        inner_button_frame.pack(anchor="center")

        for name in self.folder_map.keys():
            btn = tk.Button(
                inner_button_frame,
                text=name,
                width=18,
                relief="raised",
                command=lambda n=name: self.switch_folder(n)
            )
            btn.pack(side="left", padx=6, pady=5)
            self.buttons[name] = btn

        # Main content
        self.main_frame = tk.Frame(self)
        self.main_frame.pack(fill="both", expand=True)

        self.files_tree = ttk.Treeview(
            self.main_frame,
            columns=("size", "type", "time"),
            show="tree headings"
        )
        self.files_tree.pack(fill="both", expand=True, padx=20, pady=20)

        self.files_tree.heading("#0", text="File Name", anchor="w")
        self.files_tree.heading("size", text="Size", anchor="w")
        self.files_tree.heading("type", text="Type", anchor="w")
        self.files_tree.heading("time", text="Last Modified", anchor="w")

        self.files_tree.column("#0", width=250)
        self.files_tree.column("size", width=100)
        self.files_tree.column("type", width=80)
        self.files_tree.column("time", width=150)

        self.files_tree.bind(
            "<Double-1>",
            lambda event: tree_open_file(event, self.folder_map[self.current_folder], self.files_tree)
        )
        self.files_tree.bind(
            "<<TreeviewOpen>>",
            self.on_tree_expand
        )

        # Initial load
        self.refresh_current_folder()
        self.update_button_styles()

        # Refresh automatically when page becomes visible
        self.bind("<Map>", lambda e: self.refresh_current_folder())

    def refresh_current_folder(self):
        """Refresh the file list for the current folder."""
        folder_path = self.folder_map[self.current_folder]
        show_subdirs = "Detections" in self.current_folder  # detections have nested folders
        populate_tree(folder_path, self.files_tree, ALL_EXTS, show_subdirs)
        self.update_button_styles()

    def switch_folder(self, folder_name):
        """Switch between the 4 main sections."""
        self.current_folder = folder_name
        self.refresh_current_folder()

    def on_tree_expand(self, event):
        """Populate animal subfolders when expanded."""
        item_id = self.files_tree.focus()
        parent_text = self.files_tree.item(item_id, "text")
        base_path = self.folder_map[self.current_folder]
        folder_path = os.path.join(base_path, parent_text)
        populate_subfolder(self.files_tree, item_id, folder_path)

    def update_button_styles(self):
        """Highlight the active button."""
        for name, btn in self.buttons.items():
            if name == self.current_folder:
                btn.config(bg="#0078D7", fg="white", relief="sunken")
            else:
                btn.config(bg="SystemButtonFace", fg="black", relief="raised")

# Run app
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Media Browser")
    root.geometry("800x550")

    app = Captures(root)
    app.pack(fill="both", expand=True)

    root.mainloop()
