import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime
import sys

def resource_path(relative_path):
    """ PyInstaller için dosya yolunu ayarlar """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Pillow kütüphanesi görüntü işleme için
try:
    from PIL import Image, ImageTk

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

FILE_NAME = "arbitraj_data.json"
CSFLOAT_FEE = 0.02
STEAM_SELL_FEE = 0.13

# Profesyonel Steam Renk Paleti
BG_APP = "#171D25"
BG_CARD = "#1B2838"
BG_ENTRY = "#2A475E"
TEXT_MAIN = "#C7D5E0"
ACCENT = "white"  # Beyaz ok/vurgu rengi
BTN_GREEN = "#5C7E10"
BTN_GREEN_HOVER = "#739E14"
BTN_RED = "#A00000"
BTN_RED_HOVER = "#C20000"
BTN_BLUE = "#2A475E"
BTN_BLUE_HOVER = "#3B6282"
EDIT_COLOR = "#D08000"
TEXT_ERROR = "#E54D4D"

# Kutu Renkleri
BOX1_COLOR = "#1E3A8A"  # Lacivert
BOX2_COLOR = "#000000"  # Siyah

# Kilitli (Disabled) input renkleri
BG_DISABLED = "#1A2836"
FG_DISABLED = "#5A6D7C"

FONT_MAIN = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 12, "bold")

# Kolonlar (İkinci Item ve Adet'in sonuna hata vermemesi için görünmez bir boşluk eklendi)
columns = [
    "Başlangıç", "Bitiş", "Item", "Adet", "Harcanan Steam",
    "Kazanılan CSF", "CSF Geçiş %", "Item ", "Adet ", "Kalan CSF", "Son Steam Bakiye", "Net Kar %"
]


class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, bg=BG_CARD, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=BG_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=BG_CARD)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.bind_mouse_scroll()

    def bind_mouse_scroll(self):
        def _on_enter(event):
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        def _on_leave(event):
            self.canvas.unbind_all("<MouseWheel>")

        self.canvas.bind('<Enter>', _on_enter)
        self.canvas.bind('<Leave>', _on_leave)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


def create_hover_effect(widget, default_bg, hover_bg):
    def on_enter(e):
        if widget.cget("state") != "disabled":
            widget.config(bg=hover_bg)

    def on_leave(e):
        if widget.cget("state") != "disabled":
            widget.config(bg=default_bg)

    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("CS2 Arbitraj Aracı Pro")
        self.root.state("zoomed")  # Windows için tam ekran (maximize)
        self.root.bind("<Escape>", lambda e: self.root.attributes("-fullscreen", False))
        self.root.configure(bg=BG_APP)

        self.setup_style()
        self.data_store = []
        self.editing_index = None
        self.editing_item = None

        # --- LOGO YÜKLEME VE BOYUTLANDIRMA ---
        MAX_SIZE_HEADER = (180, 35)  # Üst logolar için
        MAX_SIZE_ICON = (100, 30)  # Alt form başlık logoları için

        self.steam_img_header = None
        self.csf_img_header = None
        self.steam_img_icon = None
        self.csf_img_icon = None

        if HAS_PIL:
            try:
                steam_pil = Image.open(resource_path("steam_logo.png"))
                steam_pil_header = steam_pil.copy()
                steam_pil_icon = steam_pil.copy()

                steam_pil_header.thumbnail(MAX_SIZE_HEADER, Image.Resampling.LANCZOS)
                steam_pil_icon.thumbnail(MAX_SIZE_ICON, Image.Resampling.LANCZOS)

                self.steam_img_header = ImageTk.PhotoImage(steam_pil_header)
                self.steam_img_icon = ImageTk.PhotoImage(steam_pil_icon)
            except:
                pass

            try:
                csf_pil = Image.open(resource_path("csfloat_logo.png"))
                csf_pil_header = csf_pil.copy()
                csf_pil_icon = csf_pil.copy()

                csf_pil_header.thumbnail(MAX_SIZE_HEADER, Image.Resampling.LANCZOS)
                csf_pil_icon.thumbnail(MAX_SIZE_ICON, Image.Resampling.LANCZOS)

                self.csf_img_header = ImageTk.PhotoImage(csf_pil_header)
                self.csf_img_icon = ImageTk.PhotoImage(csf_pil_icon)
            except:
                pass
        else:
            messagebox.showwarning("Kütüphane Eksik",
                                   "Logoları düzgün boyutlandırmak için 'Pillow' kütüphanesi gerekli.\nLütfen terminale şunu yazın: pip install pillow")
        # ------------------------------------

        # --- ÜST BÖLÜM: Tablo ve Logoların Ana Kapsayıcısı ---
        top_container = tk.Frame(root, bg=BG_APP)
        top_container.pack(fill="both", expand=True, padx=20, pady=(10, 10))

        # 1. LOGO ALANI (Tablonun üstü)
        self.header_frame = tk.Frame(top_container, bg=BG_APP, height=45)
        self.header_frame.pack(fill="x")
        self.header_frame.pack_propagate(False)

        self.steam_logo_frame = tk.Frame(self.header_frame, bg=BG_APP)
        if self.steam_img_header:
            tk.Label(self.steam_logo_frame, image=self.steam_img_header, bg=BG_APP).pack(expand=True)
        else:
            tk.Label(self.steam_logo_frame, text="Steam Logo", fg="white", bg=BG_APP, font=FONT_TITLE).pack(expand=True)

        self.csf_logo_frame = tk.Frame(self.header_frame, bg=BG_APP)
        if self.csf_img_header:
            tk.Label(self.csf_logo_frame, image=self.csf_img_header, bg=BG_APP).pack(expand=True)
        else:
            tk.Label(self.csf_logo_frame, text="CSFloat Logo", fg="white", bg=BG_APP, font=FONT_TITLE).pack(expand=True)

        # 2. TABLO ALANI
        self.table_frame = tk.Frame(top_container, bg=BG_CARD, highlightbackground=BG_ENTRY, highlightthickness=1)
        self.table_frame.pack(fill="both", expand=True, pady=(5, 0))

        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", height=8)
        for col in columns:
            # .strip() ile arkadaki boşlukları silip ekrana sadece Item ve Adet yazdırıyoruz
            self.tree.heading(col, text=col.strip())

            if col in ["Başlangıç", "Bitiş"]:
                w = 110
            elif "Adet" in col:
                w = 60
            elif "Kar" in col or "Geçiş" in col or "Kalan" in col:
                w = 90
            else:
                w = 120
            self.tree.column(col, width=w, anchor="center")

        self.tree.pack(fill="both", expand=True, side="left", padx=1, pady=1)

        tree_scroll = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        tree_scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.tag_configure("profit", foreground="#61C554")
        self.tree.tag_configure("loss", foreground="#E54D4D")
        self.tree.tag_configure("neutral", foreground="#FFFFFF")

        # --- YENİ: TABLO İÇİ KARE KUTU ÇİZİMLERİ ---
        self.b1_left = tk.Frame(self.table_frame, bg=BOX1_COLOR)
        self.b1_right = tk.Frame(self.table_frame, bg=BOX1_COLOR)
        self.b1_top = tk.Frame(self.table_frame, bg=BOX1_COLOR)
        self.b1_bot = tk.Frame(self.table_frame, bg=BOX1_COLOR)

        self.b2_left = tk.Frame(self.table_frame, bg=BOX2_COLOR)
        self.b2_right = tk.Frame(self.table_frame, bg=BOX2_COLOR)
        self.b2_top = tk.Frame(self.table_frame, bg=BOX2_COLOR)
        self.b2_bot = tk.Frame(self.table_frame, bg=BOX2_COLOR)

        self.tree.bind("<Configure>", self.update_box_overlays)
        self.tree.bind("<B1-Motion>", self.update_box_overlays)
        self.tree.bind("<ButtonRelease-1>", self.update_box_overlays)

        # 3. TABLO ALTI BUTONLARI
        btn_frame = tk.Frame(top_container, bg=BG_APP)
        btn_frame.pack(fill="x", pady=5)

        btn_del = tk.Button(btn_frame, text="🗑 Seçili Satırı Sil", bg=BTN_RED, fg="white", font=FONT_BOLD,
                            relief="flat", padx=10, command=self.delete_row)
        btn_del.pack(side="right", padx=(10, 0))
        create_hover_effect(btn_del, BTN_RED, BTN_RED_HOVER)

        btn_edit = tk.Button(btn_frame, text="✏️ Seçili Satırı Düzenle", bg=BTN_BLUE, fg="white", font=FONT_BOLD,
                             relief="flat", padx=10, command=self.load_for_edit)
        btn_edit.pack(side="right")
        create_hover_effect(btn_edit, BTN_BLUE, BTN_BLUE_HOVER)

        # --- ALT BÖLÜM: Dinamik Giriş Formu ---
        bottom_frame = tk.Frame(root, bg=BG_APP)
        bottom_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        # Adım 1 Form Çerçevesi
        self.left_card = tk.Frame(bottom_frame, bg=BG_CARD, highlightbackground=BOX1_COLOR, highlightthickness=5)
        self.left_card.pack(side="left", fill="both", expand=True)
        self.build_step_card(self.left_card, 1)

        tk.Frame(bottom_frame, bg=BG_APP, width=10).pack(side="left")

        # Adım 2 Form Çerçevesi
        self.right_card = tk.Frame(bottom_frame, bg=BG_CARD, highlightbackground=BOX2_COLOR, highlightthickness=5)
        self.right_card.pack(side="left", fill="both", expand=True)
        self.build_step_card(self.right_card, 2)

        # HESAPLA BUTONU
        self.action_btn = tk.Button(root, text="HESAPLA VE DÖNGÜYÜ KAYDET", bg=BTN_GREEN, fg="white",
                                    font=("Segoe UI", 14, "bold"), relief="flat", command=self.calculate_and_save)
        self.action_btn.pack(fill="x", padx=20, pady=(0, 20), ipady=10)
        create_hover_effect(self.action_btn, BTN_GREEN, BTN_GREEN_HOVER)

        self.load_data()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def update_box_overlays(self, event=None):
        self.root.after(10, self._draw_boxes)

    def _draw_boxes(self):
        x_offset = 1
        col_widths = [self.tree.column(col, "width") for col in columns]

        b1_start = x_offset + sum(col_widths[0:2])
        b1_end = b1_start + sum(col_widths[2:6])

        b2_start = x_offset + sum(col_widths[0:7])
        b2_end = b2_start + sum(col_widths[7:11])

        bw = 5

        self.b1_left.place(x=b1_start, y=1, width=bw, relheight=1, height=-2)
        self.b1_right.place(x=b1_end - bw, y=1, width=bw, relheight=1, height=-2)
        self.b1_top.place(x=b1_start, y=1, width=b1_end - b1_start, height=bw)
        self.b1_bot.place(x=b1_start, rely=1, y=-bw - 1, width=b1_end - b1_start, height=bw)

        self.b2_left.place(x=b2_start, y=1, width=bw, relheight=1, height=-2)
        self.b2_right.place(x=b2_end - bw, y=1, width=bw, relheight=1, height=-2)
        self.b2_top.place(x=b2_start, y=1, width=b2_end - b2_start, height=bw)
        self.b2_bot.place(x=b2_start, rely=1, y=-bw - 1, width=b2_end - b2_start, height=bw)

        self.steam_logo_frame.place(x=b1_start + 1, y=0, width=b1_end - b1_start, height=45)
        self.csf_logo_frame.place(x=b2_start + 1, y=0, width=b2_end - b2_start, height=45)

    def setup_style(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=BG_CARD, foreground="white", rowheight=35, fieldbackground=BG_CARD,
                        borderwidth=0, font=FONT_MAIN)
        style.configure("Treeview.Heading", background=BG_APP, foreground="#66C0F4", font=FONT_BOLD, borderwidth=0,
                        padding=5)
        style.map("Treeview", background=[("selected", BG_ENTRY)])
        self.root.tk.eval(f"ttk::style configure Treeview.Item -padding 5")

    def build_step_card(self, parent, step):
        header = tk.Frame(parent, bg=BG_ENTRY)
        header.pack(fill="x")

        if self.steam_img_icon and self.csf_img_icon:
            title_container = tk.Frame(header, bg=BG_ENTRY)
            title_container.pack(pady=8)

            if step == 1:
                tk.Label(title_container, image=self.steam_img_icon, bg=BG_ENTRY).pack(side="left")
                tk.Label(title_container, text=" ➔ ", bg=BG_ENTRY, fg=ACCENT, font=("Segoe UI", 16, "bold")).pack(
                    side="left")
                tk.Label(title_container, image=self.csf_img_icon, bg=BG_ENTRY).pack(side="left")
            else:
                tk.Label(title_container, image=self.csf_img_icon, bg=BG_ENTRY).pack(side="left")
                tk.Label(title_container, text=" ➔ ", bg=BG_ENTRY, fg=ACCENT, font=("Segoe UI", 16, "bold")).pack(
                    side="left")
                tk.Label(title_container, image=self.steam_img_icon, bg=BG_ENTRY).pack(side="left")
        else:
            title_text = "Steam ➔ CSFloat" if step == 1 else "CSFloat ➔ Steam"
            title_color = BOX1_COLOR if step == 1 else "white"
            tk.Label(header, text=title_text, bg=BG_ENTRY, fg=title_color, font=FONT_TITLE, pady=8).pack()

        form_frame = tk.Frame(parent, bg=BG_CARD)
        form_frame.pack(fill="x", padx=20, pady=15)

        item_var = tk.StringVar()
        qty_var = tk.StringVar()
        qty_var.trace_add("write", lambda *args, s=step: self.generate_inputs(s))

        lbl_step_err = tk.Label(form_frame, text="", bg=BG_CARD, fg=TEXT_ERROR, font=FONT_BOLD)
        lbl_step_err.grid(row=2, column=0, columnspan=3, sticky="w", padx=5, pady=(5, 0))

        if step == 1:
            self.step1_item_var = item_var
            self.step1_qty_var = qty_var
            self.step1_entries = []
            self.step1_err_lbl = lbl_step_err
            scroll_container = tk.Frame(parent, bg=BG_CARD)
            scroll_container.pack(fill="both", expand=True, padx=10, pady=5)
            self.step1_scroll = ScrollableFrame(scroll_container)
            self.step1_scroll.pack(fill="both", expand=True)
        else:
            self.step2_item_var = item_var
            self.step2_qty_var = qty_var
            self.step2_entries = []
            self.step2_err_lbl = lbl_step_err
            scroll_container = tk.Frame(parent, bg=BG_CARD)
            scroll_container.pack(fill="both", expand=True, padx=10, pady=5)
            self.step2_scroll = ScrollableFrame(scroll_container)
            self.step2_scroll.pack(fill="both", expand=True)

            self.lbl_warning = tk.Label(form_frame, text="", bg=BG_CARD, fg=TEXT_ERROR, font=FONT_BOLD)
            self.lbl_warning.grid(row=0, column=2, sticky="w", padx=10)

        tk.Label(form_frame, text="İtem Adı:", bg=BG_CARD, fg=TEXT_MAIN, font=FONT_BOLD).grid(row=0, column=0,
                                                                                              sticky="w", pady=5,
                                                                                              padx=5)
        e_item = tk.Entry(form_frame, textvariable=item_var, bg=BG_ENTRY, fg="white", font=FONT_MAIN, relief="flat",
                          insertbackground="white", width=30)
        e_item.grid(row=0, column=1, sticky="w", pady=5, ipady=4, padx=5)

        tk.Label(form_frame, text="Adet:", bg=BG_CARD, fg=TEXT_MAIN, font=FONT_BOLD).grid(row=1, column=0, sticky="w",
                                                                                          pady=5, padx=5)
        e_qty = tk.Entry(form_frame, textvariable=qty_var, bg=BG_ENTRY, fg="white", font=FONT_MAIN, relief="flat",
                         insertbackground="white", width=8, justify="center")
        e_qty.grid(row=1, column=1, sticky="w", pady=5, ipady=4, padx=5)

        btn_copy = tk.Button(form_frame, text="⏬ İlk Fiyatı Tümüne Uygula", bg=BG_ENTRY, fg=TEXT_MAIN,
                             font=("Segoe UI", 9), relief="flat", command=lambda s=step: self.copy_all(s))
        btn_copy.grid(row=1, column=1, sticky="e", padx=5)
        create_hover_effect(btn_copy, BG_ENTRY, BTN_BLUE_HOVER)

    def generate_inputs(self, step):
        try:
            if step == 1:
                qty_str = self.step1_qty_var.get()
                qty = int(qty_str) if qty_str else 0
                target_frame = self.step1_scroll.scrollable_frame
                entries_list = self.step1_entries
                label1, label2 = "Steam Alış ($)", "CSF Satış ($)"
                self.step1_err_lbl.config(text="")
            else:
                qty_str = self.step2_qty_var.get()
                qty = int(qty_str) if qty_str else 0
                target_frame = self.step2_scroll.scrollable_frame
                entries_list = self.step2_entries
                label1, label2 = "CSF Alış ($)", "Steam Satış ($)"
                self.step2_err_lbl.config(text="")

            if qty > 200: return

            for widget in target_frame.winfo_children():
                widget.destroy()
            entries_list.clear()

            for i in range(qty):
                f = tk.Frame(target_frame, bg=BG_CARD)
                f.pack(fill="x", pady=3, padx=10)
                tk.Label(f, text=f"#{i + 1}", bg=BG_CARD, fg="#66C0F4", font=FONT_BOLD, width=4, anchor="w").pack(
                    side="left")

                e1 = tk.Entry(f, bg=BG_ENTRY, fg="white", insertbackground="white", relief="flat", width=14,
                              justify="center")
                e1.pack(side="left", padx=5, ipady=4)
                e1.insert(0, label1)
                e1.bind("<FocusIn>", lambda args, e=e1, l=label1: self.clear_placeholder(e, l))

                e1.bind("<KeyRelease>", lambda event, s=step: self.on_entry_change(event, s), add="+")

                e2 = tk.Entry(f, bg=BG_ENTRY, fg="white", insertbackground="white", relief="flat", width=14,
                              justify="center", disabledbackground=BG_DISABLED, disabledforeground=FG_DISABLED)
                e2.pack(side="left", padx=5, ipady=4)
                e2.insert(0, label2)
                e2.bind("<FocusIn>", lambda args, e=e2, l=label2: self.clear_placeholder(e, l))
                e2.bind("<KeyRelease>", self.check_balance_realtime, add="+")

                e2.config(state="disabled")

                lbl_err = tk.Label(f, text="", bg=BG_CARD, fg=TEXT_ERROR, font=("Segoe UI", 9, "bold"))
                lbl_err.pack(side="left", padx=5)

                entries_list.append((e1, e2, lbl_err))

            self.check_unlock(step)
            self.check_balance_realtime()

        except ValueError:
            pass

    def on_entry_change(self, event, step):
        self.check_unlock(step)
        self.check_balance_realtime()

        entries = self.step1_entries if step == 1 else self.step2_entries
        for e1, e2, lbl in entries:
            lbl.config(text="")

    def check_unlock(self, step):
        entries = self.step1_entries if step == 1 else self.step2_entries
        placeholder = "Steam Alış ($)" if step == 1 else "CSF Alış ($)"

        if not entries:
            return

        all_valid = True
        for e1, e2, _ in entries:
            val = e1.get().strip()
            if val == "" or val == placeholder:
                all_valid = False
                break
            try:
                float(val)
            except ValueError:
                all_valid = False
                break

        new_state = "normal" if all_valid else "disabled"

        for e1, e2, _ in entries:
            if e2.cget("state") != new_state:
                e2.config(state=new_state)

    def check_balance_realtime(self, event=None):
        if not hasattr(self, 'lbl_warning'): return

        total_csf_got = 0.0
        for e1, e2, _ in self.step1_entries:
            sell_val = self.safe_parse_float(e2.get(), "CSF Satış ($)")
            total_csf_got += sell_val * (1 - CSFLOAT_FEE)

        total_csf_used = 0.0
        for e1, e2, _ in self.step2_entries:
            buy_val = self.safe_parse_float(e1.get(), "CSF Alış ($)")
            total_csf_used += buy_val

        if total_csf_used > total_csf_got and total_csf_used > 0:
            fark = total_csf_used - total_csf_got
            self.lbl_warning.config(text=f"⚠️ Bakiye Yetersiz! (-${fark:.2f})")
            self.action_btn.config(state="disabled", bg="#3a4f0a")
        else:
            self.lbl_warning.config(text="")
            btn_color = EDIT_COLOR if self.editing_index is not None else BTN_GREEN
            self.action_btn.config(state="normal", bg=btn_color)

    def clear_placeholder(self, entry, placeholder):
        if entry.cget("state") == "disabled": return
        if entry.get() == placeholder:
            entry.delete(0, tk.END)

    def copy_all(self, step):
        entries = self.step1_entries if step == 1 else self.step2_entries
        if not entries: return
        val1 = entries[0][0].get()
        val2 = entries[0][1].get()

        for e1, e2, _ in entries[1:]:
            e1.delete(0, tk.END)
            e1.insert(0, val1)

            e2_state = e2.cget("state")
            e2.config(state="normal")
            e2.delete(0, tk.END)
            e2.insert(0, val2)
            if e2_state == "disabled":
                e2.config(state="disabled")

        self.check_unlock(step)
        self.check_balance_realtime()

    def load_for_edit(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Bilgi", "Lütfen düzenlemek için bir satır seçin.")
            return

        self.editing_item = selected[0]
        self.editing_index = self.tree.index(self.editing_item)
        record = self.data_store[self.editing_index]

        self.action_btn.config(text="DEĞİŞİKLİKLERİ KAYDET", bg=EDIT_COLOR)
        create_hover_effect(self.action_btn, EDIT_COLOR, "#E68E00")

        self.step1_item_var.set(record["step1_item"])
        self.step1_qty_var.set(str(record["step1_qty"]))
        for i, detail in enumerate(record["step1_details"]):
            e1, e2, _ = self.step1_entries[i]
            e1.delete(0, tk.END)
            e1.insert(0, str(detail["buy"]) if detail["buy"] != 0 else "Steam Alış ($)")

            e2.config(state="normal")
            e2.delete(0, tk.END)
            e2.insert(0, str(detail["sell"]) if detail["sell"] != 0 else "CSF Satış ($)")
        self.check_unlock(1)

        self.step2_item_var.set(record["step2_item"])
        self.step2_qty_var.set(str(record["step2_qty"]))
        for i, detail in enumerate(record["step2_details"]):
            e1, e2, _ = self.step2_entries[i]
            e1.delete(0, tk.END)
            e1.insert(0, str(detail["buy"]) if detail["buy"] != 0 else "CSF Alış ($)")

            e2.config(state="normal")
            e2.delete(0, tk.END)
            e2.insert(0, str(detail["sell"]) if detail["sell"] != 0 else "Steam Satış ($)")
        self.check_unlock(2)

        self.check_balance_realtime()

    def safe_parse_float(self, val_str, placeholder):
        val_str = val_str.strip()
        if not val_str or val_str == placeholder:
            return 0.0
        try:
            return float(val_str)
        except:
            return 0.0

    def calculate_and_save(self):
        try:
            self.step1_err_lbl.config(text="")
            self.step2_err_lbl.config(text="")
            for _, _, lbl in self.step1_entries: lbl.config(text="")
            for _, _, lbl in self.step2_entries: lbl.config(text="")

            has_error = False

            if not self.step1_entries:
                self.step1_err_lbl.config(text="⚠️ Adım 1 için en az 1 ürün eklemelisiniz.")
                has_error = True
            else:
                for e1, e2, lbl in self.step1_entries:
                    v1 = e1.get().strip()
                    v2 = e2.get().strip()

                    if v1 in ["", "Steam Alış ($)"]:
                        lbl.config(text="⚠️ Alış fiyatı eksik!")
                        has_error = True
                    else:
                        try:
                            float(v1)
                        except ValueError:
                            lbl.config(text="⚠️ Geçersiz alış fiyatı!")
                            has_error = True

                    if v2 not in ["", "CSF Satış ($)"]:
                        try:
                            float(v2)
                        except ValueError:
                            lbl.config(text="⚠️ Geçersiz satış fiyatı!")
                            has_error = True

            for e1, e2, lbl in self.step2_entries:
                v1 = e1.get().strip()
                v2 = e2.get().strip()

                if v1 in ["", "CSF Alış ($)"]:
                    lbl.config(text="⚠️ Alış fiyatı eksik!")
                    has_error = True
                else:
                    try:
                        float(v1)
                    except ValueError:
                        lbl.config(text="⚠️ Geçersiz alış fiyatı!")
                        has_error = True

                if v2 not in ["", "Steam Satış ($)"]:
                    try:
                        float(v2)
                    except ValueError:
                        lbl.config(text="⚠️ Geçersiz satış fiyatı!")
                        has_error = True

            if has_error:
                return

            total_steam_used = 0.0
            total_csf_got = 0.0
            step1_details = []

            for e1, e2, _ in self.step1_entries:
                buy_val = self.safe_parse_float(e1.get(), "Steam Alış ($)")
                sell_val = self.safe_parse_float(e2.get(), "CSF Satış ($)")
                total_steam_used += buy_val
                total_csf_got += sell_val * (1 - CSFLOAT_FEE)
                step1_details.append({"buy": buy_val, "sell": sell_val})

            total_csf_used = 0.0
            total_steam_final = 0.0
            step2_details = []

            for e1, e2, _ in self.step2_entries:
                buy_val = self.safe_parse_float(e1.get(), "CSF Alış ($)")
                sell_val = self.safe_parse_float(e2.get(), "Steam Satış ($)")
                total_csf_used += buy_val
                total_steam_final += sell_val * (1 - STEAM_SELL_FEE)
                step2_details.append({"buy": buy_val, "sell": sell_val})

            if total_csf_used > total_csf_got:
                return

            csf_kalan_bakiye = total_csf_got - total_csf_used
            toplam_son_deger = total_steam_final + csf_kalan_bakiye

            if total_steam_used > 0:
                csf_gecis_yuzdesi = (total_csf_got / total_steam_used) * 100
            else:
                csf_gecis_yuzdesi = 0.0

            now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
            is_step2_done = False

            if len(step2_details) > 0:
                is_step2_done = True
                for d in step2_details:
                    if d["sell"] <= 0:
                        is_step2_done = False
                        break

            if self.editing_index is not None:
                old_record = self.data_store[self.editing_index]
                start_date = old_record.get("start_date", now_str)

                if is_step2_done and old_record.get("end_date") == "⏳ Devam Ediyor":
                    end_date = now_str
                elif not is_step2_done:
                    end_date = "⏳ Devam Ediyor"
                else:
                    end_date = old_record.get("end_date", "⏳ Devam Ediyor")
            else:
                start_date = now_str
                end_date = now_str if is_step2_done else "⏳ Devam Ediyor"

            if total_steam_used > 0:
                profit_pct = ((toplam_son_deger / total_steam_used) * 100) - 100
            else:
                profit_pct = 0.0

            record = {
                "start_date": start_date,
                "end_date": end_date,
                "step1_item": self.step1_item_var.get(),
                "step1_qty": len(step1_details),
                "step1_details": step1_details,
                "step2_item": self.step2_item_var.get(),
                "step2_qty": len(step2_details),
                "step2_details": step2_details,
                "summary": {
                    "steam_used": round(total_steam_used, 2),
                    "csf_got": round(total_csf_got, 2),
                    "csf_gecis_yuzdesi": round(csf_gecis_yuzdesi, 2),
                    "csf_used": round(total_csf_used, 2),
                    "csf_kalan": round(csf_kalan_bakiye, 2),
                    "steam_final": round(total_steam_final, 2),
                    "profit_pct": round(profit_pct, 2)
                }
            }

            if self.editing_index is not None:
                self.data_store[self.editing_index] = record
                self.update_tree_item(self.editing_item, record)
            else:
                self.data_store.append(record)
                self.insert_to_tree(record)

            self.clear_all_inputs()
        except Exception as e:
            messagebox.showerror("Hata", f"İşlem sırasında beklenmeyen bir hata oluştu: {e}")

    def format_values(self, record):
        s = record["summary"]
        pct = s["profit_pct"]

        if record["end_date"] == "⏳ Devam Ediyor" or record["step2_qty"] == 0:
            tag, pct_str = "neutral", "-"
        else:
            if pct > 0:
                tag, pct_str = "profit", f"+%{pct}"
            elif pct < 0:
                tag, pct_str = "loss", f"-%{abs(pct)}"
            else:
                tag, pct_str = "neutral", "%0.0"

        csf_gecis = s.get("csf_gecis_yuzdesi", 0.0)
        csf_gecis_str = f"%{csf_gecis}"

        csf_kalan_val = s.get("csf_kalan", 0.0)

        return (
            record["start_date"], record["end_date"],
            record["step1_item"], record["step1_qty"], f"${s['steam_used']}", f"${s['csf_got']}",
            csf_gecis_str,
            record["step2_item"], record["step2_qty"], f"${csf_kalan_val}", f"${s['steam_final']}",
            pct_str
        ), tag

    def insert_to_tree(self, record):
        values, tag = self.format_values(record)
        self.tree.insert("", "end", values=values, tags=(tag,))

    def update_tree_item(self, item, record):
        values, tag = self.format_values(record)
        self.tree.item(item, values=values, tags=(tag,))

    def delete_row(self):
        selected = self.tree.selection()
        for item in selected:
            idx = self.tree.index(item)
            del self.data_store[idx]
            self.tree.delete(item)

    def clear_all_inputs(self):
        self.step1_item_var.set("")
        self.step1_qty_var.set("")
        self.step2_item_var.set("")
        self.step2_qty_var.set("")
        self.action_btn.config(state="normal", text="HESAPLA VE DÖNGÜYÜ KAYDET", bg=BTN_GREEN)
        create_hover_effect(self.action_btn, BTN_GREEN, BTN_GREEN_HOVER)
        self.editing_index = None
        self.editing_item = None
        self.lbl_warning.config(text="")
        self.step1_err_lbl.config(text="")
        self.step2_err_lbl.config(text="")

    def save_data(self):
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            json.dump(self.data_store, f, ensure_ascii=False, indent=4)

    def load_data(self):
        if os.path.exists(FILE_NAME):
            with open(FILE_NAME, "r", encoding="utf-8") as f:
                try:
                    self.data_store = json.load(f)
                    for record in self.data_store:
                        self.insert_to_tree(record)
                except:
                    self.data_store = []

    def on_close(self):
        self.save_data()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()