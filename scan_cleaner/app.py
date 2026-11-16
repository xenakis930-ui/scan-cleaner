from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from PIL import Image, ImageTk

from .analysis import analyze_pages
from .document import PageInfo, load_document, export_pdf


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Limpiador de Escaneos - Hojas en blanco y recicladas")
        self.geometry("1200x760")
        self.minsize(980, 640)

        self.pages: list[PageInfo] = []
        self.thumbs: list[ImageTk.PhotoImage] = []
        self.preview_imgtk: ImageTk.PhotoImage | None = None
        self.current_path: Path | None = None

        self.blank_thr = tk.DoubleVar(value=0.78)
        self.recycled_thr = tk.DoubleVar(value=0.55)
        self.blank_action = tk.StringVar(value="remove")
        self.recycled_action = tk.StringVar(value="separate")

        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)

        ttk.Button(top, text="Abrir archivo...", command=self.open_file).pack(side=tk.LEFT)
        ttk.Button(top, text="Reanalizar", command=self.reanalyze).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Exportar resultado...", command=self.export_result).pack(side=tk.LEFT)

        opts = ttk.LabelFrame(self, text="Detección y acciones por defecto (editables)", padding=8)
        opts.pack(fill=tk.X, padx=8, pady=4)

        ttk.Label(opts, text="Umbral blanco").grid(row=0, column=0, sticky="w")
        tk.Scale(opts, from_=0.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL, variable=self.blank_thr, length=220).grid(row=0, column=1, padx=6)
        ttk.Label(opts, text="Acción si blanco").grid(row=0, column=2, sticky="w", padx=(12, 4))
        ttk.Combobox(opts, textvariable=self.blank_action, values=["remove", "separate", "keep"], state="readonly", width=12).grid(row=0, column=3)

        ttk.Label(opts, text="Umbral reciclada").grid(row=1, column=0, sticky="w")
        tk.Scale(opts, from_=0.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL, variable=self.recycled_thr, length=220).grid(row=1, column=1, padx=6)
        ttk.Label(opts, text="Acción si reciclada").grid(row=1, column=2, sticky="w", padx=(12, 4))
        ttk.Combobox(opts, textvariable=self.recycled_action, values=["separate", "remove", "keep"], state="readonly", width=12).grid(row=1, column=3)

        self.status = tk.StringVar(value="Abre un PDF o imagen escaneada para comenzar.")
        ttk.Label(self, textvariable=self.status, padding=(8, 2)).pack(fill=tk.X)

        main = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        left = ttk.Frame(main)
        right = ttk.Frame(main, padding=6)
        main.add(left, weight=1)
        main.add(right, weight=2)

        cols = ("page", "blank", "recycled", "action", "reason")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("page", text="Página")
        self.tree.heading("blank", text="Puntaje blanco")
        self.tree.heading("recycled", text="Puntaje reciclada")
        self.tree.heading("action", text="Acción")
        self.tree.heading("reason", text="Detección")
        self.tree.column("page", width=60, anchor="center")
        self.tree.column("blank", width=110, anchor="center")
        self.tree.column("recycled", width=120, anchor="center")
        self.tree.column("action", width=100, anchor="center")
        self.tree.column("reason", width=260)
        vsb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.show_selected())

        ttk.Label(right, text="Vista previa y edición de página seleccionada", font=("", 10, "bold")).pack(anchor="w")
        self.preview_label = ttk.Label(right)
        self.preview_label.pack(fill=tk.BOTH, expand=True, pady=6)

        edit = ttk.Frame(right)
        edit.pack(fill=tk.X)
        ttk.Label(edit, text="Acción para esta página:").pack(side=tk.LEFT)
        self.page_action = tk.StringVar(value="keep")
        self.page_action_cb = ttk.Combobox(edit, textvariable=self.page_action, values=["keep", "remove", "separate"], state="readonly", width=14)
        self.page_action_cb.pack(side=tk.LEFT, padx=8)
        self.page_action_cb.bind("<<ComboboxSelected>>", lambda e: self.apply_page_action())
        ttk.Button(edit, text="Restaurar acción automática", command=self.reset_page_action).pack(side=tk.LEFT)

        self.detail = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.detail, wraplength=520, justify="left").pack(anchor="w", pady=4)

    def open_file(self):
        path = filedialog.askopenfilename(title="Seleccionar archivo escaneado", filetypes=[
            ("Documentos e imágenes", "*.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp"),
            ("PDF", "*.pdf"), ("Imágenes", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp"), ("Todos", "*.*")
        ])
        if not path:
            return
        self.current_path = Path(path)
        self.status.set(f"Cargando {self.current_path.name}...")
        self.update_idletasks()

        def work():
            try:
                images = load_document(path)
                pages = analyze_pages(images, self.blank_thr.get(), self.recycled_thr.get(), self.blank_action.get(), self.recycled_action.get())
                self.after(0, lambda: self.set_pages(pages, f"Cargado: {self.current_path.name} ({len(pages)} páginas)"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.after(0, lambda: self.status.set("Error al cargar el archivo."))
        threading.Thread(target=work, daemon=True).start()

    def set_pages(self, pages: list[PageInfo], status: str):
        self.pages = pages
        self.refresh_tree()
        self.status.set(status)
        if self.pages:
            self.tree.selection_set("p0")
            self.show_selected()

    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for p in self.pages:
            reason = "; ".join(p.reasons) if p.reasons else "OK"
            self.tree.insert("", tk.END, iid=f"p{p.index}", values=(p.index + 1, f"{p.blank_score:.2f}", f"{p.recycled_score:.2f}", p.action, reason))

    def reanalyze(self):
        if not self.current_path:
            messagebox.showinfo("Reanalizar", "Primero abre un archivo.")
            return
        # keep manual overrides? we re-run auto and reset; simpler
        self.open_file_path(self.current_path)

    def open_file_path(self, path: Path):
        self.current_path = path
        self.status.set(f"Reanalizando {path.name}...")
        self.update_idletasks()

        def work():
            try:
                images = load_document(path)
                pages = analyze_pages(images, self.blank_thr.get(), self.recycled_thr.get(), self.blank_action.get(), self.recycled_action.get())
                self.after(0, lambda: self.set_pages(pages, f"Reanalizado: {path.name} ({len(pages)} páginas)"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
        threading.Thread(target=work, daemon=True).start()

    def selected_page(self) -> PageInfo | None:
        sel = self.tree.selection()
        if not sel:
            return None
        idx = int(sel[0][1:])
        if 0 <= idx < len(self.pages):
            return self.pages[idx]
        return None

    def show_selected(self):
        p = self.selected_page()
        if not p:
            return
        self.page_action.set(p.action)
        img = p.image.copy()
        img.thumbnail((700, 800))
        self.preview_imgtk = ImageTk.PhotoImage(img)
        self.preview_label.configure(image=self.preview_imgtk)
        d = p.details
        self.detail.set(
            f"Página {p.index+1} | blanco={p.blank_score:.3f} (detectado={p.blank_detected}) | "
            f"reciclada={p.recycled_score:.3f} (detectado={p.recycled_detected}) | "
            f"acción auto={p.auto_action}\nDetalles: {d}"
        )

    def apply_page_action(self):
        p = self.selected_page()
        if not p:
            return
        p.action = self.page_action.get()  # type: ignore
        self.refresh_tree()
        self.tree.selection_set(f"p{p.index}")
        self.status.set(f"Página {p.index+1}: acción cambiada a '{p.action}'.")

    def reset_page_action(self):
        p = self.selected_page()
        if not p:
            return
        p.action = p.auto_action
        self.page_action.set(p.action)
        self.refresh_tree()
        self.tree.selection_set(f"p{p.index}")

    def export_result(self):
        if not self.pages:
            messagebox.showinfo("Exportar", "No hay páginas cargadas.")
            return
        base = self.current_path.stem if self.current_path else "resultado"
        out_dir = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if not out_dir:
            return
        out_dir = Path(out_dir)
        keep = [p for p in self.pages if p.action == "keep"]
        remove = [p for p in self.pages if p.action == "remove"]
        separate = [p for p in self.pages if p.action == "separate"]
        try:
            if keep:
                export_pdf(self.pages, out_dir / f"{base}_limpio.pdf", {"keep"})
            if remove:
                export_pdf(self.pages, out_dir / f"{base}_eliminadas.pdf", {"remove"})
            if separate:
                export_pdf(self.pages, out_dir / f"{base}_recicladas_o_separadas.pdf", {"separate"})
            msg = f"Exportado en {out_dir}\nConservar: {len(keep)} | Eliminar: {len(remove)} | Separar: {len(separate)}"
            if not keep:
                msg += "\n(Nota: no se generó archivo limpio porque ninguna página quedó en 'keep')."
            messagebox.showinfo("Exportación completa", msg)
            self.status.set(msg.replace('\n', ' '))
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e))


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
