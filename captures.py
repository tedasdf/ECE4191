import tkinter as tk
from tkinter import ttk
from functions import *

class Captures(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)

        # --- Top Menu Bar ---
        top_frame = tk.Frame(self, bg="white", pady=5)
        top_frame.pack(fill="x")

        logo = tk.Label(top_frame, text="🐨", font=("Arial", 18))
        logo.pack(side="left", padx=10)

        connectionsetup_button = tk.Button(
            top_frame, text="Connection Setup",
            command=lambda: controller.show_frame(ConnectionSetup))
        connectionsetup_button.pack(side="left", padx=5)

        captures_button = tk.Button(
            top_frame, text="Device Control",
            command=lambda: controller.show_frame(DeviceControl))
        captures_button.pack(side="left", padx=5)

        tk.Button(top_frame, text="Captures", relief="sunken").pack(side="left", padx=5)

        tk.Label(top_frame, text="Wildlife Bot", font=("Arial", 18, "bold"), bg="white").pack(side="right", padx=15)

        # file browser
        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True)

        refresh_button = tk.Button(main_frame, text="Refresh", command=lambda:populate_tree(media_dir, files_tree, ALL_EXTS))
        refresh_button.pack(side="top", padx=10, pady=10)

        files_tree = ttk.Treeview(main_frame, columns=("time", "size", "type"), show="tree headings")
        files_tree.pack(fill="both", expand=True, padx=20, pady=20)

        files_tree.heading("#0", text="File Name", anchor="w")
        files_tree.heading("size", text="Size", anchor="w")
        files_tree.heading("type", text="Type", anchor="w")
        files_tree.heading("time", text="Last Modified", anchor="w")

        files_tree.column("#0", width=200)
        files_tree.column("size", width=100)
        files_tree.column("type", width=80)
        files_tree.column("time", width=150)

        media_dir = "./media"
        populate_tree(media_dir, files_tree, ALL_EXTS)
        files_tree.bind("<Double-1>", lambda event: tree_open_file(event, media_dir, files_tree))
