"""
==============================================================
  PERSONAL EXPENSE TRACKER WITH BUDGET ALERTS
  Project for : MCA 2nd Semester
  Student     : Sachin
  Institute   : Rawal Institute of Management
  Technology  : Python 3 + Tkinter + MySQL
==============================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox
import datetime

# ── MySQL CONNECTION ───────────────────────────
try:
    import mysql.connector
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mysql-connector-python"])
    import mysql.connector

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "root123",
    "database": "expense_tracker_db"
}

def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

# ── DATABASE INITIALIZATION ────────────────────
def init_db():
    # First connect WITHOUT database to create it if not exists
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root123"
    )
    c = conn.cursor()
    c.execute("CREATE DATABASE IF NOT EXISTS expense_tracker_db")
    conn.commit()
    conn.close()

    # Now connect WITH database
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id     INT AUTO_INCREMENT PRIMARY KEY,
            name   VARCHAR(100) UNIQUE NOT NULL,
            budget DECIMAL(10,2) NOT NULL DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            category    VARCHAR(100) NOT NULL,
            amount      DECIMAL(10,2) NOT NULL,
            description TEXT,
            date        DATE NOT NULL
        )
    """)

    # Seed default categories if empty
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        defaults = [("Food",3000),("Transport",1500),("Education",2000),
                    ("Entertainment",1000),("Other",2000)]
        c.executemany("INSERT IGNORE INTO categories(name,budget) VALUES(%s,%s)", defaults)

    conn.commit()
    conn.close()

# ── DATABASE HELPERS ───────────────────────────
def db_add_expense(cat, amt, desc, date):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO expenses(category,amount,description,date) VALUES(%s,%s,%s,%s)",
              (cat, amt, desc, date))
    conn.commit()
    conn.close()

def db_get_expenses(month=None):
    conn = get_conn()
    c = conn.cursor()

    if month:
        start = month + "-01"

        # next month calculation
        import datetime
        dt = datetime.datetime.strptime(month, "%Y-%m")
        next_month = (dt.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        end = next_month.strftime("%Y-%m-%d")

        print("Range:", start, "to", end)  # debug

        c.execute(
            "SELECT id,date,category,description,amount FROM expenses "
            "WHERE date >= %s AND date < %s ORDER BY date DESC",
            (start, end)
        )
    else:
        c.execute("SELECT id,date,category,description,amount FROM expenses ORDER BY date DESC")

    rows = c.fetchall()
    conn.close()
    return rows

def format_query(query, params):
    q = query.replace("%%", "%")   # fix %% → %
    for p in params:
        if isinstance(p, str):
            p = f"'{p}'"
        q = q.replace("%s", str(p), 1)
    return q    

def db_delete_expense(eid):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id=%s", (eid,))
    conn.commit()
    conn.close()

def db_get_categories():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT name,budget FROM categories ORDER BY name")
    rows = c.fetchall()
    conn.close()
    return rows

def db_get_spent(month):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT category,SUM(amount) FROM expenses "
        "WHERE DATE_FORMAT(date,'%%Y-%%m')=%s GROUP BY category",
        (month,))
    rows = c.fetchall()
    conn.close()
    return dict(rows)

def db_update_budget(cat, b):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE categories SET budget=%s WHERE name=%s", (b, cat))
    conn.commit()
    conn.close()

def db_add_category(name, b):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO categories(name,budget) VALUES(%s,%s)", (name, b))
        conn.commit()
        conn.close()
        return True
    except mysql.connector.errors.IntegrityError:
        conn.close()
        return False

# ── COLORS ────────────────────────────────────
BG      = "#f0f4f8"
SIDEBAR = "#1e3a5f"
ACCENT  = "#2563eb"
DANGER  = "#dc2626"
SUCCESS = "#16a34a"
WARNING = "#d97706"
WHITE   = "#ffffff"
DARK    = "#1e293b"
GRAY    = "#64748b"

# ── APP ───────────────────────────────────────
class ExpenseApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Personal Expense Tracker with Budget Alerts")
        self.geometry("1060x660")
        self.configure(bg=BG)
        self.resizable(True, True)

        try:
            init_db()
        except Exception as e:
            messagebox.showerror("Database Error",
                f"Could not connect to MySQL!\n\n{e}\n\n"
                "Make sure MySQL is running and credentials are correct.")
            self.destroy()
            return

        self.cur_month = datetime.date.today().strftime("%Y-%m")
        self._build_sidebar()
        self.content = tk.Frame(self, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)
        self.show_dashboard()

    def _build_sidebar(self):
        sb = tk.Frame(self, bg=SIDEBAR, width=200)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        tk.Label(sb, text="💰 ExpenseTracker", font=("Times New Roman",13,"bold"),
                 bg=SIDEBAR, fg=WHITE, wraplength=180).pack(pady=(20,4))
        tk.Label(sb, text="MCA Project – Sachin", font=("Times New Roman",9),
                 bg=SIDEBAR, fg="#94a3b8").pack(pady=(0,22))
        for lbl, cmd in [
            ("🏠  Dashboard",       self.show_dashboard),
            ("➕  Add Expense",     self.show_add),
            ("📋  View Expenses",   self.show_view),
            ("📊  Budget Status",   self.show_budget),
            ("⚙️  Manage Budget",   self.show_manage),
        ]:
            tk.Button(sb, text=lbl, font=("Times New Roman",11),
                      bg=SIDEBAR, fg=WHITE, bd=0,
                      activebackground=ACCENT, activeforeground=WHITE,
                      anchor="w", padx=18, pady=10, cursor="hand2",
                      command=cmd).pack(fill="x")

    def _clear(self):
        for w in self.content.winfo_children(): w.destroy()

    def _header(self, title, sub=""):
        h = tk.Frame(self.content, bg=ACCENT, height=60)
        h.pack(fill="x"); h.pack_propagate(False)
        tk.Label(h, text=title, font=("Times New Roman",16,"bold"),
                 bg=ACCENT, fg=WHITE).pack(side="left", padx=20)
        if sub:
            tk.Label(h, text=sub, font=("Times New Roman",10),
                     bg=ACCENT, fg="#bfdbfe").pack(side="right", padx=20)

    def _card(self, parent, title, val, color=ACCENT):
        f = tk.Frame(parent, bg=WHITE, width=175, height=95,
                     highlightthickness=1, highlightbackground="#e2e8f0")
        f.pack(side="left", padx=8, pady=10); f.pack_propagate(False)
        tk.Label(f, text=title, font=("Times New Roman",9), bg=WHITE, fg=GRAY).pack(pady=(14,2))
        tk.Label(f, text=val,   font=("Times New Roman",15,"bold"), bg=WHITE, fg=color).pack()

    # ── DASHBOARD ─────────────────────────────
    def show_dashboard(self):
        self._clear(); self._header("Dashboard", f"Month: {self.cur_month}")
        rows = db_get_expenses(self.cur_month)
        total_spent = sum(float(r[4]) for r in rows)
        cats = db_get_categories()
        total_budget = sum(float(b) for _,b in cats)
        remaining = total_budget - total_spent

        cf = tk.Frame(self.content, bg=BG); cf.pack(fill="x", padx=20, pady=12)
        self._card(cf, "Monthly Budget", f"Rs.{total_budget:,.0f}", ACCENT)
        self._card(cf, "Total Spent",    f"Rs.{total_spent:,.0f}", DANGER)
        self._card(cf, "Remaining",
                   f"Rs.{remaining:,.0f}", SUCCESS if remaining>=0 else DANGER)
        self._card(cf, "Transactions",   str(len(rows)), WARNING)

        spent_map = db_get_spent(self.cur_month)
        alerts = [(n, float(spent_map.get(n,0))/float(b)*100, float(b))
                  for n,b in cats if float(b)>0 and float(spent_map.get(n,0))/float(b)*100>=80]
        if alerts:
            af = tk.Frame(self.content, bg="#fef2f2",
                          highlightthickness=1, highlightbackground="#fca5a5")
            af.pack(fill="x", padx=20, pady=4)
            tk.Label(af, text="  ⚠ Budget Alerts", font=("Times New Roman",11,"bold"),
                     bg="#fef2f2", fg=DANGER).pack(anchor="w", padx=10, pady=(8,2))
            for n, pct, b in alerts:
                tag = "EXCEEDED" if pct>=100 else "Near Limit"
                clr = DANGER if pct>=100 else WARNING
                tk.Label(af, text=f"   {tag}: {n}  ({pct:.1f}% of Rs.{b:,.0f} used)",
                         font=("Times New Roman",10), bg="#fef2f2", fg=clr).pack(anchor="w", padx=10)
            tk.Label(af, text="", bg="#fef2f2").pack(pady=3)

        tk.Label(self.content, text="Recent Transactions",
                 font=("Times New Roman",12,"bold"), bg=BG, fg=DARK).pack(anchor="w", padx=20, pady=(8,2))
        cols = ("Date","Category","Description","Amount (Rs.)")
        t = ttk.Treeview(self.content, columns=cols, show="headings", height=8)
        for c in cols: t.heading(c,text=c); t.column(c,width=180)
        for r in rows[:10]:
            t.insert("","end", values=(r[1],r[2],r[3] or "—",f"Rs.{float(r[4]):,.2f}"))
        t.pack(fill="x", padx=20)

    # ── ADD EXPENSE ───────────────────────────
    def show_add(self):
        self._clear(); self._header("Add New Expense")
        cats = [n for n,_ in db_get_categories()]
        form = tk.Frame(self.content, bg=WHITE,
                        highlightthickness=1, highlightbackground="#e2e8f0")
        form.pack(padx=50, pady=25)

        cat_var  = tk.StringVar(value=cats[0] if cats else "")
        amt_var  = tk.StringVar()
        desc_var = tk.StringVar()
        date_var = tk.StringVar(value=datetime.date.today().strftime("%Y-%m-%d"))

        for i, (lbl, widget) in enumerate([
            ("Category",    ttk.Combobox(form, textvariable=cat_var, values=cats,
                                         state="readonly", font=("Times New Roman",11), width=28)),
            ("Amount (Rs.)",tk.Entry(form, textvariable=amt_var,  font=("Times New Roman",11),
                                      width=30, relief="solid", bd=1)),
            ("Description", tk.Entry(form, textvariable=desc_var, font=("Times New Roman",11),
                                      width=30, relief="solid", bd=1)),
            ("Date (YYYY-MM-DD)", tk.Entry(form, textvariable=date_var, font=("Times New Roman",11),
                                            width=30, relief="solid", bd=1)),
        ]):
            tk.Label(form, text=lbl, font=("Times New Roman",11,"bold"),
                     bg=WHITE, fg=DARK).grid(row=i, column=0, sticky="w", padx=30, pady=12)
            widget.grid(row=i, column=1, padx=20, pady=12)

        def submit():
            cat   = cat_var.get()
            amt_s = amt_var.get().strip()
            desc  = desc_var.get().strip()
            date  = date_var.get().strip()
            if not amt_s or not date:
                messagebox.showwarning("Missing","Amount and Date are required."); return
            try:
                amt = float(amt_s); assert amt > 0
            except:
                messagebox.showerror("Invalid","Enter a valid positive amount."); return
            try:
                datetime.datetime.strptime(date, "%Y-%m-%d")
            except:
                messagebox.showerror("Invalid Date","Use YYYY-MM-DD format."); return

            db_add_expense(cat, amt, desc, date)
            m = date[:7]
            spent_map = db_get_spent(m)
            spent = float(spent_map.get(cat, 0))
            bgt   = float(dict(db_get_categories()).get(cat, 0))
            pct   = (spent/bgt*100) if bgt > 0 else 0
            if pct >= 100:
                messagebox.showwarning("BUDGET EXCEEDED",
                    f"You exceeded your {cat} budget!\nSpent: Rs.{spent:.2f} / Budget: Rs.{bgt:.2f}")
            elif pct >= 80:
                messagebox.showinfo("Budget Alert",
                    f"Warning! {pct:.1f}% of {cat} budget used.\nSpent: Rs.{spent:.2f} / Budget: Rs.{bgt:.2f}")
            else:
                messagebox.showinfo("Saved", f"Expense of Rs.{amt:.2f} added!")
            amt_var.set(""); desc_var.set("")

        tk.Button(form, text="  Add Expense  ",
                  font=("Times New Roman",12,"bold"),
                  bg=ACCENT, fg=WHITE, relief="flat", padx=20, pady=8,
                  cursor="hand2", command=submit).grid(row=4, column=0, columnspan=2, pady=18)

    # ── VIEW EXPENSES ─────────────────────────
    def show_view(self):
        self._clear(); self._header("View & Delete Expenses")
        ctrl = tk.Frame(self.content, bg=BG); ctrl.pack(fill="x", padx=20, pady=8)
        tk.Label(ctrl, text="Filter Month (YYYY-MM):", font=("Times New Roman",11), bg=BG).pack(side="left")
        mv = tk.StringVar(value=self.cur_month)
        tk.Entry(ctrl, textvariable=mv, font=("Times New Roman",11),
                 width=12, relief="solid", bd=1).pack(side="left", padx=8)

        cols = ("ID","Date","Category","Description","Amount (Rs.)")
        tree = ttk.Treeview(self.content, columns=cols, show="headings", height=18)
        tree.column("ID",width=45); tree.column("Date",width=120); tree.column("Category",width=130)
        tree.column("Description",width=250); tree.column("Amount (Rs.)",width=120)
        for c in cols: tree.heading(c, text=c)
        
        def load():
            month = mv.get().strip()
            print("Month:", month)
            for r in tree.get_children(): tree.delete(r)
            data = db_get_expenses(month or None)

            print("Data from DB:", data)   # 🔥 ADD THIS
            for r in db_get_expenses(mv.get().strip() or None):
                tree.insert("","end",
                    values=(r[0], r[1], r[2], r[3] or "—", f"Rs.{float(r[4]):,.2f}"))

        def delete_sel():
            sel = tree.selection()
            if not sel: messagebox.showinfo("Select","Select a row first."); return
            eid = tree.item(sel[0])["values"][0]
            if messagebox.askyesno("Confirm", f"Delete expense ID {eid}?"):
                db_delete_expense(eid); load()

        tk.Button(ctrl, text="Filter", font=("Times New Roman",10),
                  bg=ACCENT, fg=WHITE, relief="flat", padx=10, pady=3,
                  cursor="hand2", command=load).pack(side="left")
        tk.Button(ctrl, text="Delete Selected", font=("Times New Roman",10),
                  bg=DANGER, fg=WHITE, relief="flat", padx=10, pady=3,
                  cursor="hand2", command=delete_sel).pack(side="right")
        tree.pack(fill="both", expand=True, padx=20, pady=4)
        load()

    # ── BUDGET STATUS ─────────────────────────
    def show_budget(self):
        self._clear(); self._header("Budget Status", f"Month: {self.cur_month}")
        cats = db_get_categories()
        spent_map = db_get_spent(self.cur_month)

        fr = tk.Frame(self.content, bg=BG); fr.pack(fill="both", expand=True, padx=30, pady=15)
        for name, budget in cats:
            spent = float(spent_map.get(name, 0))
            budget = float(budget)
            pct   = min((spent/budget*100) if budget>0 else 0, 100)
            clr   = SUCCESS if pct<70 else (WARNING if pct<100 else DANGER)

            row = tk.Frame(fr, bg=BG); row.pack(fill="x", pady=8)
            tk.Label(row, text=name, font=("Times New Roman",11,"bold"),
                     bg=BG, fg=DARK, width=14, anchor="w").pack(side="left")
            bar_bg = tk.Frame(row, bg="#e2e8f0", height=20, width=460)
            bar_bg.pack(side="left"); bar_bg.pack_propagate(False)
            w = max(int(460*pct/100), 2)
            tk.Frame(bar_bg, bg=clr, height=20, width=w).place(x=0,y=0)
            tk.Label(row, text=f"  Rs.{spent:,.0f} / Rs.{budget:,.0f}  ({pct:.1f}%)",
                     font=("Times New Roman",10), bg=BG, fg=clr).pack(side="left")

    # ── MANAGE BUDGET ─────────────────────────
    def show_manage(self):
        self._clear(); self._header("Manage Budgets & Categories")
        cats = db_get_categories()

        tk.Label(self.content, text="Update Monthly Budgets (Rs.)",
                 font=("Times New Roman",12,"bold"), bg=BG, fg=DARK).pack(anchor="w", padx=20, pady=(15,5))
        form = tk.Frame(self.content, bg=WHITE,
                        highlightthickness=1, highlightbackground="#e2e8f0")
        form.pack(padx=20, fill="x")
        entries = {}
        for i,(name,budget) in enumerate(cats):
            tk.Label(form, text=name, font=("Times New Roman",11),
                     bg=WHITE, fg=DARK, width=18, anchor="w").grid(row=i, column=0, padx=20, pady=8)
            v = tk.StringVar(value=str(float(budget)))
            tk.Entry(form, textvariable=v, font=("Times New Roman",11),
                     width=14, relief="solid", bd=1).grid(row=i, column=1, padx=10)
            entries[name] = v

        def save():
            for n,v in entries.items():
                try: db_update_budget(n, float(v.get()))
                except: messagebox.showerror("Error", f"Invalid value for {n}"); return
            messagebox.showinfo("Saved","All budgets updated!")

        tk.Button(form, text="Save Budgets", font=("Times New Roman",11,"bold"),
                  bg=SUCCESS, fg=WHITE, relief="flat", padx=16, pady=6,
                  cursor="hand2", command=save).grid(row=len(cats), column=0, columnspan=2, pady=14)

        tk.Label(self.content, text="Add New Category",
                 font=("Times New Roman",12,"bold"), bg=BG, fg=DARK).pack(anchor="w", padx=20, pady=(18,5))
        af = tk.Frame(self.content, bg=WHITE,
                      highlightthickness=1, highlightbackground="#e2e8f0")
        af.pack(padx=20, fill="x")
        nn = tk.StringVar(); nb = tk.StringVar()
        tk.Label(af, text="Name:", font=("Times New Roman",11), bg=WHITE).grid(row=0, column=0, padx=20, pady=12)
        tk.Entry(af, textvariable=nn, font=("Times New Roman",11), width=18,
                 relief="solid", bd=1).grid(row=0, column=1, padx=8)
        tk.Label(af, text="Budget:", font=("Times New Roman",11), bg=WHITE).grid(row=0, column=2, padx=10)
        tk.Entry(af, textvariable=nb, font=("Times New Roman",11), width=12,
                 relief="solid", bd=1).grid(row=0, column=3, padx=8)

        def add():
            n, b = nn.get().strip(), nb.get().strip()
            if not n or not b: messagebox.showwarning("Missing","Enter name and budget."); return
            try: b = float(b)
            except: messagebox.showerror("Error","Budget must be a number."); return
            if db_add_category(n, b):
                messagebox.showinfo("Added", f"Category '{n}' added!")
                self.show_manage()
            else:
                messagebox.showerror("Duplicate", f"'{n}' already exists.")

        tk.Button(af, text="Add Category", font=("Times New Roman",11,"bold"),
                  bg=ACCENT, fg=WHITE, relief="flat", padx=12, pady=5,
                  cursor="hand2", command=add).grid(row=0, column=4, padx=15)

# ── ENTRY POINT ───────────────────────────────
if __name__ == "__main__":
    app = ExpenseApp()
    app.mainloop()
