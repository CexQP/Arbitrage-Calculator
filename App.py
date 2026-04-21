import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime  # Tarih işlemleri için eklendi

FILE_NAME = "arbitraj_data.json"
CSFLOAT_FEE = 0.02
STEAM_SELL_FEE = 0.13

# Profesyonel Steam Renk Paleti
BG_APP = "#171D25"
BG_CARD = "#1B2838"
BG_ENTRY = "#2A475E"
TEXT_MAIN = "#C7D5E0"
ACCENT = "#66C0F4"
BTN_GREEN = "#5C7E10"
BTN_GREEN_HOVER = "#739E14"
BTN_RED = "#A00000"
BTN_RED_HOVER = "#C20000"
BTN_BLUE = "#2A475E"
BTN_BLUE_HOVER = "#3B6282"
EDIT_COLOR = "#D08000"

FONT_MAIN = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 12, "bold")

# Kolonlara Başlangıç ve Bitiş Tarihleri Eklendi
columns = [
    "Başlangıç", "Bitiş", "Adım 1 İtem", "Adet 1", "Harcanan Steam",
    "Kazanılan CSF", "Adım 2 İtem", "Adet 2", "Son Steam Bakiye", "Net Kar %"
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
    widget.bind("<Enter>", lambda e: widget.config(bg=hover_bg))
    widget.bind("<Leave>", lambda e: widget.config(bg=default_bg))


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("CS2 Arbitraj Aracı Pro")
        self.root.geometry("1500x850")  # Kolonlar arttığı için biraz genişletildi
        self.root.configure(bg=BG_APP)

        self.setup_style()
        self.data_store = []
        self.editing_index = None
        self.editing_item = None

        # --- ÜST BÖLÜM: Tablo ---
        top_container = tk.Frame(root, bg=BG_APP)
        top_container.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        table_frame = tk.Frame(top_container, bg=BG_CARD, highlightbackground=BG_ENTRY, highlightthickness=1)
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
        for col in columns:
            self.tree.heading(col, text=col)
            # Kolon genişlikleri
            if col in ["Başlangıç", "Bitiş"]:
                w = 110
            elif "Adet" in col:
                w = 60
            elif "Kar" in col:
                w = 90
            else:
                w = 130
            self.tree.column(col, width=w, anchor="center")

        self.tree.pack(fill="both", expand=True, side="left", padx=1, pady=1)

        tree_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        tree_scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.tag_configure("profit", foreground="#61C554")
        self.tree.tag_configure("loss", foreground="#E54D4D")
        self.tree.tag_configure("neutral", foreground="#FFFFFF")

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
        bottom_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.left_card = tk.Frame(bottom_frame, bg=BG_CARD, highlightbackground=BG_ENTRY, highlightthickness=1)
        self.left_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.build_step_card(self.left_card, 1, "ADIM 1: Steam -> CSFloat")

        self.right_card = tk.Frame(bottom_frame, bg=BG_CARD, highlightbackground=BG_ENTRY, highlightthickness=1)
        self.right_card.pack(side="right", fill="both", expand=True, padx=(10, 0))
        self.build_step_card(self.right_card, 2, "ADIM 2: CSFloat -> Steam")

        self.action_btn = tk.Button(root, text="HESAPLA VE DÖNGÜYÜ KAYDET", bg=BTN_GREEN, fg="white",
                                    font=("Segoe UI", 14, "bold"), relief="flat", command=self.calculate_and_save)
        self.action_btn.pack(fill="x", padx=20, pady=(0, 20), ipady=10)
        create_hover_effect(self.action_btn, BTN_GREEN, BTN_GREEN_HOVER)

        self.load_data()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_style(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=BG_CARD, foreground="white", rowheight=35, fieldbackground=BG_CARD,
                        borderwidth=0, font=FONT_MAIN)
        style.configure("Treeview.Heading", background=BG_APP, foreground=ACCENT, font=FONT_BOLD, borderwidth=0,
                        padding=5)
        style.map("Treeview", background=[("selected", BG_ENTRY)])
        self.root.tk.eval(f"ttk::style configure Treeview.Item -padding 5")

    def build_step_card(self, parent, step, title):
        header = tk.Frame(parent, bg=BG_ENTRY)
        header.pack(fill="x")
        tk.Label(header, text=title, bg=BG_ENTRY, fg=ACCENT, font=FONT_TITLE, pady=8).pack()

        form_frame = tk.Frame(parent, bg=BG_CARD)
        form_frame.pack(fill="x", padx=20, pady=15)

        item_var = tk.StringVar()
        qty_var = tk.StringVar()
        qty_var.trace_add("write", lambda *args, s=step: self.generate_inputs(s))

        if step == 1:
            self.step1_item_var = item_var
            self.step1_qty_var = qty_var
            self.step1_entries = []
            scroll_container = tk.Frame(parent, bg=BG_CARD)
            scroll_container.pack(fill="both", expand=True, padx=10, pady=5)
            self.step1_scroll = ScrollableFrame(scroll_container)
            self.step1_scroll.pack(fill="both", expand=True)
        else:
            self.step2_item_var = item_var
            self.step2_qty_var = qty_var
            self.step2_entries = []
            scroll_container = tk.Frame(parent, bg=BG_CARD)
            scroll_container.pack(fill="both", expand=True, padx=10, pady=5)
            self.step2_scroll = ScrollableFrame(scroll_container)
            self.step2_scroll.pack(fill="both", expand=True)

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
            else:
                qty_str = self.step2_qty_var.get()
                qty = int(qty_str) if qty_str else 0
                target_frame = self.step2_scroll.scrollable_frame
                entries_list = self.step2_entries
                label1, label2 = "CSF Alış ($)", "Steam Satış ($)"

            if qty > 200: return

            for widget in target_frame.winfo_children():
                widget.destroy()
            entries_list.clear()

            for i in range(qty):
                f = tk.Frame(target_frame, bg=BG_CARD)
                f.pack(fill="x", pady=3, padx=10)
                tk.Label(f, text=f"#{i + 1}", bg=BG_CARD, fg=ACCENT, font=FONT_BOLD, width=4, anchor="w").pack(
                    side="left")
                e1 = tk.Entry(f, bg=BG_ENTRY, fg="white", insertbackground="white", relief="flat", width=14,
                              justify="center")
                e1.pack(side="left", padx=5, ipady=4)
                e1.insert(0, label1)
                e1.bind("<FocusIn>", lambda args, e=e1, l=label1: self.clear_placeholder(e, l))
                e2 = tk.Entry(f, bg=BG_ENTRY, fg="white", insertbackground="white", relief="flat", width=14,
                              justify="center")
                e2.pack(side="left", padx=5, ipady=4)
                e2.insert(0, label2)
                e2.bind("<FocusIn>", lambda args, e=e2, l=label2: self.clear_placeholder(e, l))
                entries_list.append((e1, e2))
        except ValueError:
            pass

    def clear_placeholder(self, entry, placeholder):
        if entry.get() == placeholder:
            entry.delete(0, tk.END)

    def copy_all(self, step):
        entries = self.step1_entries if step == 1 else self.step2_entries
        if not entries: return
        val1 = entries[0][0].get()
        val2 = entries[0][1].get()
        for e1, e2 in entries[1:]:
            e1.delete(0, tk.END)
            e1.insert(0, val1)
            e2.delete(0, tk.END)
            e2.insert(0, val2)

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
            self.step1_entries[i][0].delete(0, tk.END)
            self.step1_entries[i][0].insert(0, str(detail["buy"]) if detail["buy"] != 0 else "Steam Alış ($)")
            self.step1_entries[i][1].delete(0, tk.END)
            self.step1_entries[i][1].insert(0, str(detail["sell"]) if detail["sell"] != 0 else "CSF Satış ($)")

        self.step2_item_var.set(record["step2_item"])
        self.step2_qty_var.set(str(record["step2_qty"]))
        for i, detail in enumerate(record["step2_details"]):
            self.step2_entries[i][0].delete(0, tk.END)
            self.step2_entries[i][0].insert(0, str(detail["buy"]) if detail["buy"] != 0 else "CSF Alış ($)")
            self.step2_entries[i][1].delete(0, tk.END)
            self.step2_entries[i][1].insert(0, str(detail["sell"]) if detail["sell"] != 0 else "Steam Satış ($)")

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
            total_steam_used = 0.0
            total_csf_got = 0.0
            step1_details = []

            for e1, e2 in self.step1_entries:
                buy_val = self.safe_parse_float(e1.get(), "Steam Alış ($)")
                sell_val = self.safe_parse_float(e2.get(), "CSF Satış ($)")
                total_steam_used += buy_val
                total_csf_got += sell_val * (1 - CSFLOAT_FEE)
                step1_details.append({"buy": buy_val, "sell": sell_val})

            total_csf_used = 0.0
            total_steam_final = 0.0
            step2_details = []

            for e1, e2 in self.step2_entries:
                buy_val = self.safe_parse_float(e1.get(), "CSF Alış ($)")
                sell_val = self.safe_parse_float(e2.get(), "Steam Satış ($)")
                total_csf_used += buy_val
                total_steam_final += sell_val * (1 - STEAM_SELL_FEE)
                step2_details.append({"buy": buy_val, "sell": sell_val})

            csf_kalan_bakiye = total_csf_got - total_csf_used
            toplam_son_deger = total_steam_final + csf_kalan_bakiye

            # Zaman Belirleme Mantığı
            now_str = datetime.now().strftime("%d.%m.%Y %H:%M")

            if self.editing_index is not None:
                # Düzenleme Modu
                old_record = self.data_store[self.editing_index]
                start_date = old_record.get("start_date", now_str)
                # Eğer kâr oluşmuşsa bitiş tarihini bugün yap, yoksa eskiyi koru
                end_date = now_str if (toplam_son_deger > 0 and old_record.get(
                    "end_date") == "⏳ Devam Ediyor") else old_record.get("end_date", "⏳ Devam Ediyor")
            else:
                # Yeni Kayıt Modu
                start_date = now_str
                end_date = "⏳ Devam Ediyor"

            if total_steam_used > 0:
                if toplam_son_deger == 0:
                    profit_pct = 0.0
                else:
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
                    "csf_used": round(total_csf_used, 2),
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
            messagebox.showerror("Hata", f"İşlem sırasında bir hata oluştu: {e}")

    def format_values(self, record):
        s = record["summary"]
        pct = s["profit_pct"]
        if pct > 0:
            tag, pct_str = "profit", f"+%{pct}"
        elif pct < 0:
            tag, pct_str = "loss", f"-%{abs(pct)}"
        else:
            tag, pct_str = "neutral", "%0.0"

        return (
            record["start_date"], record["end_date"],
            record["step1_item"], record["step1_qty"], f"${s['steam_used']}", f"${s['csf_got']}",
            record["step2_item"], record["step2_qty"], f"${s['steam_final']}",
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
        self.action_btn.config(text="HESAPLA VE DÖNGÜYÜ KAYDET", bg=BTN_GREEN)
        create_hover_effect(self.action_btn, BTN_GREEN, BTN_GREEN_HOVER)
        self.editing_index = None
        self.editing_item = None

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