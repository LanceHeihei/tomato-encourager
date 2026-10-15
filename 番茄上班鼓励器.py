# -*- coding: utf-8 -*-
"""
番茄上班鼓励器 · 上班拒绝内耗 - 无所吊谓
跨平台 tkinter 桌面应用（Windows / macOS / Linux），零第三方依赖。

运行方式：
  Windows: py 番茄上班鼓励器.py
  macOS:   python3 番茄上班鼓励器.py
  Linux:   python3 番茄上班鼓励器.py

打包方式：
  本地:   pyinstaller --onefile --windowed --name "番茄上班鼓励器" 番茄上班鼓励器.py
  CI:     push to GitHub → Actions 自动构建 Windows exe + macOS .app
"""
import json
import sys
import time
import datetime as dt
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path

# ==================== 跨平台适配 ====================
def get_font():
    """自动检测操作系统，返回对应中文字体名"""
    if sys.platform == "win32":
        return "Microsoft YaHei"
    elif sys.platform == "darwin":
        return "PingFang SC"
    else:
        return "Noto Sans CJK SC"

def get_data_dir():
    """配置文件/历史记录存放目录：优先程序同目录，打包后使用用户主目录"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，__file__ 指向临时目录，改用用户目录
        return Path.home() / ".tomato_encourager"
    return Path(__file__).resolve().parent

FONT = get_font()
IS_MAC = (sys.platform == "darwin")
IS_WIN = (sys.platform == "win32")

BASE = get_data_dir()
BASE.mkdir(parents=True, exist_ok=True)
CFG_PATH = BASE / "encourager_config.json"
HIS_PATH = BASE / "encourager_history.json"

# ==================== 主题配色 ====================
THEMES = {
    "樱花粉": dict(bg="#f7f1e8", dlg_bg="#fbf7f2", title="#e08ba3", accent="#e7b3c6",
                   accent_fg="#7d3f52", number="#3ea6c9", text="#5a86b8",
                   dot_on="#35c2a0", dot_off="#9a9a9a"),
    "薄荷绿": dict(bg="#eef6f0", dlg_bg="#f4faf6", title="#3ba58a", accent="#a8dcc4",
                   accent_fg="#20604c", number="#2e8b6e", text="#4a8a7a",
                   dot_on="#2fbf9a", dot_off="#9a9a9a"),
    "湖水蓝": dict(bg="#eef3f8", dlg_bg="#f4f8fc", title="#4a7fb5", accent="#a9c6e8",
                   accent_fg="#28507d", number="#2e6da4", text="#4a7fb5",
                   dot_on="#2fbf9a", dot_off="#9a9a9a"),
}

DEFAULT_CFG = dict(start="09:00", end="17:00", wage="200",
                   slogan="上班拒绝内耗 - 无所吊谓",
                   theme="樱花粉", topmost=False)


# ==================== 纯计算逻辑 ====================
def hm_to_sec(hm: str) -> int:
    h, m = hm.split(":")
    return int(h) * 3600 + int(m) * 60


def calc_rate(wage: float, start: str, end: str) -> float:
    """每秒费率 = 日薪 / 上班总秒数"""
    secs = hm_to_sec(end) - hm_to_sec(start)
    if secs <= 0:
        raise ValueError("下班时间必须晚于上班时间")
    if wage <= 0:
        raise ValueError("日薪必须为正数")
    return wage / secs


def time_options():
    return [f"{h:02d}:{m:02d}" for h in range(6, 24) for m in (0, 30)]


def load_cfg() -> dict:
    cfg = dict(DEFAULT_CFG)
    try:
        cfg.update(json.loads(CFG_PATH.read_text(encoding="utf-8")))
    except Exception:
        pass
    if cfg.get("theme") not in THEMES:
        cfg["theme"] = DEFAULT_CFG["theme"]
    return cfg


def save_cfg(cfg: dict):
    CFG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def load_history() -> list:
    try:
        return json.loads(HIS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_history(records: list):
    HIS_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


# ==================== 主应用 ====================
class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("番茄上班鼓励器")
        root.resizable(False, False)
        self.cfg = load_cfg()
        self.state = "idle"
        self.rate = 0.0
        self.clock_in_mono = None
        self.clock_in_wall = None
        self.clock_out_wall = None
        self.start_hm = self.end_hm = None
        self._tick_id = None
        self.vars = {k: tk.StringVar(value=str(self.cfg[k])) for k in ("start", "end", "wage")}
        self.top_var = tk.BooleanVar(value=bool(self.cfg["topmost"]))
        self.build()
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- UI 重建 ----------
    def build(self):
        if self._tick_id:
            try:
                self.root.after_cancel(self._tick_id)
            except Exception:
                pass
            self._tick_id = None
        for w in self.root.winfo_children():
            w.destroy()
        t = self.t = THEMES[self.cfg["theme"]]
        self.root.configure(bg=t["bg"])
        self.root.attributes("-topmost", bool(self.cfg["topmost"]))

        # macOS 上 ttk 控件在自定义背景色中可能显得突兀，用 frame 包裹保持一致
        top = tk.Frame(self.root, bg=t["bg"])
        top.pack(fill="x", padx=14, pady=(10, 0))
        tk.Checkbutton(top, text="置顶", variable=self.top_var, command=self.toggle_top,
                       bg=t["bg"], fg=t["text"], selectcolor=t["dlg_bg"],
                       activebackground=t["bg"], activeforeground=t["text"],
                       font=(FONT, 9)).pack(side="left")
        tk.Button(top, text="历史", command=self.show_history, relief="flat", cursor="hand2",
                  bg=t["dlg_bg"], fg=t["text"], font=(FONT, 9)).pack(side="right")
        tk.Button(top, text="设置", command=self.show_settings, relief="flat", cursor="hand2",
                  bg=t["dlg_bg"], fg=t["text"], font=(FONT, 9)).pack(side="right", padx=(0, 6))

        tk.Label(self.root, text="番 茄 上 班 鼓 励 器", bg=t["bg"], fg=t["title"],
                 font=(FONT, 26, "bold")).pack(pady=(14, 2))

        self.status_lbl = tk.Label(self.root, text="", bg=t["bg"], font=(FONT, 12, "bold"))
        self.status_lbl.pack(pady=(2, 6))

        self.body = tk.Frame(self.root, bg=t["bg"])
        self.body.pack(fill="both", expand=True)

        self.slogan_lbl = tk.Label(self.root, text=self.cfg["slogan"], bg=t["bg"],
                                   fg=t["text"], font=(FONT, 11), cursor="hand2")
        self.slogan_lbl.pack(pady=(4, 10))
        # macOS 上双击事件名为 Double-Button-1，Windows/Linux 相同
        self.slogan_lbl.bind("<Double-Button-1>", lambda e: self.edit_slogan())

        self.action_btn = tk.Button(self.root, width=16, relief="flat", cursor="hand2",
                                    font=(FONT, 13, "bold"), bg=t["accent"], fg=t["accent_fg"],
                                    activebackground=t["accent"], activeforeground=t["accent_fg"])
        self.action_btn.pack(pady=(0, 16))
        self.render_state()

    def render_state(self):
        t = self.t
        for w in self.body.winfo_children():
            w.destroy()
        if self.state == "idle":
            self.status_lbl.config(text="● 未开工", fg=t["dot_off"])
            self.action_btn.config(text="上  班", command=self.on_clock_in)
            self.build_idle()
        else:
            self.status_lbl.config(text="● 工作中", fg=t["dot_on"])
            self.action_btn.config(text="下  班", command=self.on_clock_out)
            self.build_working()
            self.rate_lbl.config(text=f"+ ¥{self.rate:.4f} / 秒")
            self.tick()

    def build_idle(self):
        t = self.t
        row = tk.Frame(self.body, bg=t["bg"])
        row.pack(pady=10, expand=True)
        opts = time_options()
        for label, key in (("上班时间", "start"), ("下班时间", "end")):
            col = tk.Frame(row, bg=t["bg"])
            col.pack(side="left", padx=12)
            tk.Label(col, text=label, bg=t["bg"], fg=t["title"],
                     font=(FONT, 12, "bold")).pack(pady=(0, 4))
            cb = ttk.Combobox(col, values=opts, state="readonly", width=7,
                              textvariable=self.vars[key])
            cb.pack()
        col = tk.Frame(row, bg=t["bg"])
        col.pack(side="left", padx=12)
        tk.Label(col, text="日薪", bg=t["bg"], fg=t["title"],
                 font=(FONT, 12, "bold")).pack(pady=(0, 4))
        inner = tk.Frame(col, bg=t["bg"])
        inner.pack()
        tk.Entry(inner, textvariable=self.vars["wage"], width=6,
                 font=(FONT, 11), justify="center").pack(side="left")
        tk.Button(inner, text="计算", command=self.show_salary_calc, relief="flat",
                  cursor="hand2", bg=t["dlg_bg"], fg=t["text"],
                  font=(FONT, 9)).pack(side="left", padx=(4, 0))

    def build_working(self):
        t = self.t
        f = tk.Frame(self.body, bg=t["bg"])
        f.pack(expand=True)
        row = tk.Frame(f, bg=t["bg"])
        row.pack(pady=(22, 0))
        tk.Label(row, text="今日已赚", bg=t["bg"], fg=t["text"],
                 font=(FONT, 13)).pack(side="left", padx=(0, 8))
        tk.Label(row, text="¥", bg=t["bg"], fg="#d4574e",
                 font=(FONT, 16, "bold")).pack(side="left")
        self.earned_lbl = tk.Label(row, text="0.0000", bg=t["bg"], fg=t["number"],
                                   font=(FONT, 34, "bold"))
        self.earned_lbl.pack(side="left")
        self.rate_lbl = tk.Label(f, text="", bg=t["bg"], fg=t["text"], font=(FONT, 10))
        self.rate_lbl.pack(anchor="e", padx=42, pady=(2, 0))

    # ---------- 定时器 ----------
    def tick(self):
        if self.state != "working":
            return
        elapsed = time.monotonic() - self.clock_in_mono
        self.earned_lbl.config(text=f"{self.rate * elapsed:.4f}")
        self._tick_id = self.root.after(100, self.tick)

    # ---------- 状态切换 ----------
    def on_clock_in(self):
        try:
            wage = float(self.vars["wage"].get())
            rate = calc_rate(wage, self.vars["start"].get(), self.vars["end"].get())
        except ValueError as e:
            messagebox.showerror("输入有误", f"请检查设置：{e}")
            return
        self.rate = rate
        self.start_hm = self.vars["start"].get()
        self.end_hm = self.vars["end"].get()
        self.clock_in_mono = time.monotonic()
        self.clock_in_wall = dt.datetime.now()
        self.state = "working"
        self.render_state()

    def on_clock_out(self):
        h, m = map(int, self.end_hm.split(":"))
        if dt.datetime.now().time() < dt.time(h, m):
            if not messagebox.askyesno("无所吊谓", "是否提前下班?"):
                return
        self.settle()

    def settle(self):
        if self._tick_id:
            self.root.after_cancel(self._tick_id)
            self._tick_id = None
        elapsed = time.monotonic() - self.clock_in_mono
        amount = self.rate * elapsed
        self.clock_out_wall = dt.datetime.now()
        self.show_celebration(amount)

    # ---------- 弹窗 ----------
    def _center_over_root(self, win, w, h):
        win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

    def show_celebration(self, amount: float):
        t = self.t
        win = tk.Toplevel(self.root)
        win.title("(●ˇ∀ˇ●)")
        win.configure(bg=t["dlg_bg"])
        win.resizable(False, False)
        win.transient(self.root)
        self._center_over_root(win, 360, 230)
        tk.Label(win, text="恭喜你下班啦", bg=t["dlg_bg"], fg="#5a5fd0",
                 font=(FONT, 18, "bold")).pack(pady=(26, 6))
        tk.Label(win, text="(￣y▽￣)~ 今日怒赚", bg=t["dlg_bg"], fg="#d43a2f",
                 font=(FONT, 14, "bold")).pack()
        tk.Label(win, text=f"¥{amount:.2f}", bg=t["dlg_bg"], fg="#d43a2f",
                 font=(FONT, 20, "bold")).pack(pady=(2, 12))
        btn = tk.Button(win, text="确  定", width=14, relief="flat", cursor="hand2",
                        bg=t["accent"], fg=t["accent_fg"], font=(FONT, 11, "bold"),
                        command=lambda: self.finish_settle(win, amount))
        btn.pack()
        win.protocol("WM_DELETE_WINDOW", lambda: self.finish_settle(win, amount))
        win.grab_set()
        btn.focus_set()

    def finish_settle(self, win, amount: float):
        win.destroy()
        rec = {
            "日期": self.clock_in_wall.strftime("%Y-%m-%d"),
            "上班": self.clock_in_wall.strftime("%H:%M:%S"),
            "下班": self.clock_out_wall.strftime("%H:%M:%S"),
            "计划班次": f"{self.start_hm}~{self.end_hm}",
            "时长分钟": round((self.clock_out_wall - self.clock_in_wall).total_seconds() / 60, 1),
            "收入元": round(amount, 2),
        }
        records = load_history()
        records.append(rec)
        save_history(records)
        self.state = "idle"
        self.render_state()

    def show_salary_calc(self):
        t = self.t
        win = tk.Toplevel(self.root)
        win.title("月薪 → 日薪")
        win.configure(bg=t["dlg_bg"])
        win.resizable(False, False)
        win.transient(self.root)
        self._center_over_root(win, 300, 170)
        tk.Label(win, text="月薪(元)", bg=t["dlg_bg"], fg=t["text"],
                 font=(FONT, 10)).pack(pady=(16, 2))
        salary_var = tk.StringVar(value="6600")
        tk.Entry(win, textvariable=salary_var, width=10, justify="center",
                 font=(FONT, 11)).pack()
        days_var = tk.StringVar(value="21.75")
        fr = tk.Frame(win, bg=t["dlg_bg"])
        fr.pack(pady=(8, 2))
        tk.Label(fr, text="月计薪天数", bg=t["dlg_bg"], fg=t["text"],
                 font=(FONT, 10)).pack(side="left")
        tk.Entry(fr, textvariable=days_var, width=6, justify="center",
                 font=(FONT, 10)).pack(side="left", padx=(4, 0))

        def do_calc():
            try:
                wage = round(float(salary_var.get()) / float(days_var.get()), 2)
                if wage <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("输入有误", "月薪与天数必须是正数", parent=win)
                return
            self.vars["wage"].set(f"{wage:.2f}")
            win.destroy()

        tk.Button(win, text="换算并填入日薪", command=do_calc, relief="flat", cursor="hand2",
                  bg=t["accent"], fg=t["accent_fg"], font=(FONT, 10, "bold")).pack(pady=(10, 0))

    def show_history(self):
        t = self.t
        records = load_history()
        win = tk.Toplevel(self.root)
        win.title("怒赚历史")
        win.configure(bg=t["dlg_bg"])
        win.transient(self.root)
        self._center_over_root(win, 520, 340)
        cols = ("日期", "上班", "下班", "计划班次", "时长分钟", "收入元")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
        widths = (80, 70, 70, 100, 70, 80)
        for c, w in zip(cols, widths):
            tree.heading(c, text=c)
            tree.column(c, width=w, anchor="center")
        for r in reversed(records):
            tree.insert("", "end", values=(r.get("日期"), r.get("上班"), r.get("下班"),
                                           r.get("计划班次"), r.get("时长分钟"), r.get("收入元")))
        tree.pack(fill="both", expand=True, padx=10, pady=(10, 4))
        total = sum(r.get("收入元", 0) for r in records)
        tk.Label(win, text=f"共 {len(records)} 次上班，累计怒赚 ¥{total:.2f}",
                 bg=t["dlg_bg"], fg=t["title"], font=(FONT, 11, "bold")).pack(pady=(0, 10))

    def show_settings(self):
        t = self.t
        win = tk.Toplevel(self.root)
        win.title("设置")
        win.configure(bg=t["dlg_bg"])
        win.resizable(False, False)
        win.transient(self.root)
        self._center_over_root(win, 320, 220)
        tk.Label(win, text="slogan（主界面双击 slogan 也可改）", bg=t["dlg_bg"],
                 fg=t["text"], font=(FONT, 9)).pack(pady=(14, 2))
        slogan_var = tk.StringVar(value=self.cfg["slogan"])
        tk.Entry(win, textvariable=slogan_var, width=26, justify="center",
                 font=(FONT, 10)).pack()
        tk.Label(win, text="主题色", bg=t["dlg_bg"], fg=t["text"],
                 font=(FONT, 9)).pack(pady=(12, 2))
        theme_var = tk.StringVar(value=self.cfg["theme"])
        for name in THEMES:
            tk.Radiobutton(win, text=name, variable=theme_var, value=name,
                           bg=t["dlg_bg"], fg=t["text"], selectcolor=t["bg"],
                           activebackground=t["dlg_bg"], font=(FONT, 10)).pack(anchor="w", padx=60)

        def do_save():
            self.cfg["slogan"] = slogan_var.get().strip() or DEFAULT_CFG["slogan"]
            self.cfg["theme"] = theme_var.get()
            save_cfg(self.cfg)
            win.destroy()
            self.build()

        tk.Button(win, text="保存并应用", command=do_save, relief="flat", cursor="hand2",
                  bg=t["accent"], fg=t["accent_fg"], font=(FONT, 10, "bold")).pack(pady=(10, 12))

    # ---------- 小动作 ----------
    def toggle_top(self):
        self.cfg["topmost"] = bool(self.top_var.get())
        self.root.attributes("-topmost", self.cfg["topmost"])
        save_cfg(self.cfg)

    def edit_slogan(self):
        s = simpledialog.askstring("自定义 slogan", "输入新的 slogan：",
                                   initialvalue=self.cfg["slogan"], parent=self.root)
        if s and s.strip():
            self.cfg["slogan"] = s.strip()
            save_cfg(self.cfg)
            self.slogan_lbl.config(text=self.cfg["slogan"])

    def on_close(self):
        if self.state == "working":
            if not messagebox.askyesno("等一下", "还在工作中，直接退出不会结算今日收入。\n确定退出吗?"):
                return
        self.root.destroy()


def main():
    # Windows 高分屏适配
    if IS_WIN:
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    # macOS: 确保窗口在 Dock 正常显示
    if IS_MAC:
        try:
            from ctypes import cdll, util
            objc = cdll.LoadLibrary(util.find_library("objc"))
            objc.objc_msgSend.argtypes = [c_void_p, c_void_p]
        except Exception:
            pass  # 非关键路径，失败不影响运行

    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
