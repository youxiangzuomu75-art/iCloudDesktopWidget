"""iCloud desktop calendar - read-only local CalDAV widget for Windows."""
import calendar
import datetime as dt
import json
import subprocess
import tempfile
import urllib.request
import hashlib
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

import caldav
import keyring

APP = 'iCloud Desktop Widget'
VERSION = '2.4.0'
UPDATE_API = 'https://api.github.com/repos/{repo}/releases/latest'

SERVICE = 'iCloudDesktopWidget.CalDAV'
CONFIG = Path(os.getenv('APPDATA', str(Path.home()))) / 'iCloudDesktopWidget' / 'settings.json'
JST = dt.timezone(dt.timedelta(hours=9))
BG = '#151b28'
PANEL = '#1f2939'
TEXT = '#eff4ff'
SUB = '#9daec7'
ACCENT = '#77c4ff'
BORDER = '#344358'
PALETTE = ['#7cc6ff','#f7ad72','#a4d99d','#e3a6ec','#e9c76a','#82d9cc','#ff8b9d','#b8b0ff']



THEMES = {
    'ダーク': {'bg':'#151b28','panel':'#1f2939','text':'#eff4ff','sub':'#9daec7','accent':'#77c4ff','border':'#344358','today':'#35516d','inactive':'#68768a'},
    'ライト': {'bg':'#f5f7fa','panel':'#e9eef5','text':'#1c2938','sub':'#62758c','accent':'#176bc1','border':'#d6dfea','today':'#bfdbf5','inactive':'#a7b0bc'},
    'ブルーグレー': {'bg':'#e6edf1','panel':'#d5e1e8','text':'#223645','sub':'#617989','accent':'#276d8b','border':'#b4c8d3','today':'#b3d5e5','inactive':'#8fa6b2'},
    'さくら': {'bg':'#fff7f8','panel':'#f9e8ed','text':'#463341','sub':'#8a6b7c','accent':'#b24c75','border':'#ead4df','today':'#f5cbd9','inactive':'#beaeb7'},
    'ミッドナイト': dict(zip(('bg','panel','text','sub','accent','border','today','inactive'), ['#101522','#1b2334','#eef4ff','#9aacc5','#7ebcff','#303e55','#28466a','#7183a1'])),
    'フォレスト': dict(zip(('bg','panel','text','sub','accent','border','today','inactive'), ['#132820','#1d3c30','#e8fff0','#a8cdb7','#80dca3','#365c48','#326449','#7a9d8b'])),
    'オーシャン': dict(zip(('bg','panel','text','sub','accent','border','today','inactive'), ['#092a3b','#103f54','#e4faff','#91c7d5','#52d5e9','#275b72','#17617a','#7babb8'])),
    'ラベンダー': dict(zip(('bg','panel','text','sub','accent','border','today','inactive'), ['#f4f0ff','#e8def9','#352c4c','#76698e','#8462c5','#d3c6ec','#d6c2f5','#a79abc'])),
    'ピーチ': dict(zip(('bg','panel','text','sub','accent','border','today','inactive'), ['#fff2e9','#ffe2d4','#49332e','#936e64','#d57957','#f3c9b6','#ffd3bd','#c9a598'])),
    'ミント': dict(zip(('bg','panel','text','sub','accent','border','today','inactive'), ['#e9f9f1','#d5f0e4','#234139','#6a9283','#24896c','#b1d9c9','#b7e9d2','#95b8ab'])),
    'クリーム': dict(zip(('bg','panel','text','sub','accent','border','today','inactive'), ['#fff9e8','#f5ebd1','#4a3a28','#87795f','#b77b3c','#e5d6b7','#ffe2a9','#b3a78d'])),
    'ローズ': dict(zip(('bg','panel','text','sub','accent','border','today','inactive'), ['#311e2c','#4c2a41','#fff0f7','#d6a7be','#f3a0cc','#68435e','#70415f','#b88ca5'])),
    'サンセット': dict(zip(('bg','panel','text','sub','accent','border','today','inactive'), ['#30222c','#493040','#fff2e6','#cbb4b7','#f5a16e','#69495b','#734b53','#aa8e96'])),
    'モノクロ': dict(zip(('bg','panel','text','sub','accent','border','today','inactive'), ['#181818','#292929','#f8f8f8','#aeb0b2','#ffffff','#444444','#484848','#7a7a7a'])),
    'セピア': dict(zip(('bg','panel','text','sub','accent','border','today','inactive'), ['#f1e8d8','#e7d9c4','#4b392c','#806b54','#a76c42','#cdbba4','#d4b28b','#ae9c87'])),
    'コバルト': dict(zip(('bg','panel','text','sub','accent','border','today','inactive'), ['#e9f0ff','#d4e2ff','#142c59','#647cac','#2356c8','#b7cafa','#b6ceff','#8fa5d1'])),
    'ワイン': dict(zip(('bg','panel','text','sub','accent','border','today','inactive'), ['#2b1822','#432634','#ffe8ee','#cc9ba9','#e678a0','#614050','#67334b','#ac7b8c'])),
    'アクア': dict(zip(('bg','panel','text','sub','accent','border','today','inactive'), ['#edfdfb','#d5f5f2','#1b4449','#6b999c','#238e9b','#a8d9d6','#b2e9e5','#89b6b7'])),
    'コーヒー': dict(zip(('bg','panel','text','sub','accent','border','today','inactive'), ['#261f1a','#392e26','#f8ede2','#bda799','#dda76e','#58463b','#604936','#a48c7c'])),
    'ネオン': dict(zip(('bg','panel','text','sub','accent','border','today','inactive'), ['#0e1020','#1c2040','#edf9ff','#aab9d4','#3af2d0','#343d6a','#294b67','#8494b8'])),
}

PATTERNS = ['なし','ドット','ストライプ','グリッド','斜線','チェック','波線','スター']
LAYOUTS = {'標準（カレンダー＋予定）':'standard', 'コンパクト（月間）':'compact', '予定一覧のみ':'agenda'}
MIN_SIZE = {'standard':(620,360),'compact':(350,300),'agenda':(330,230)}

def set_theme(name):
    global BG, PANEL, TEXT, SUB, ACCENT, BORDER, TODAY_BG, INACTIVE
    t = THEMES.get(name, THEMES['ダーク'])
    BG, PANEL, TEXT, SUB, ACCENT, BORDER = [t[k] for k in ('bg','panel','text','sub','accent','border')]
    TODAY_BG, INACTIVE = t['today'],t['inactive']

def load_settings():
    try: return json.loads(CONFIG.read_text(encoding='utf-8'))
    except Exception: return {}


def save_settings(data):
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def event_time(value):
    if isinstance(value, dt.datetime):
        if value.tzinfo is None: return value.replace(tzinfo=JST)
        return value.astimezone(JST)
    if isinstance(value, dt.date): return dt.datetime.combine(value, dt.time.min, tzinfo=JST)
    return None


class Widget:
    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        set_theme(self.settings.get('theme','ダーク'))
        self.user = self.settings.get('email','')
        self.password = keyring.get_password(SERVICE, self.user) if self.user else None
        self.calendars = []
        self.events = []
        self.show_month = dt.date.today().replace(day=1)
        self.busy = False
        self.last_good = None
        self.msgq = queue.Queue()
        root.title(APP)
        root.configure(bg=BG)
        root.geometry(self.settings.get('geometry_v2','760x450+55+65'))
        self.layout_mode = self.settings.get('layout_mode', 'standard')
        if self.layout_mode not in MIN_SIZE: self.layout_mode = 'standard'
        root.minsize(*MIN_SIZE[self.layout_mode])
        root.attributes('-topmost', False)
        self.borderless = bool(self.settings.get('borderless', False))
        root.attributes('-alpha', max(0.60, min(1.0, float(self.settings.get('opacity', 0.96)))))
        if self.borderless:
            root.overrideredirect(True)
        self._drag_origin = None
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.build()
        root.after(1800, self.check_updates_silent)
        root.after(150, self.pump)
        root.after(900, self.refresh)
        root.after(15*60*1000, self.periodic)

    def button(self, parent, label, command, width=None):
        return tk.Button(parent, text=label, command=command, bg=PANEL, fg=TEXT,
                         activebackground='#334863', activeforeground=TEXT,
                         relief='flat', borderwidth=0, cursor='hand2', font=('Yu Gothic UI',10),
                         padx=9, pady=5, width=width)

    def build(self):
        for child in self.root.winfo_children(): child.destroy()
        self.root.configure(bg=BG)
        mode=self.layout_mode
        header=tk.Frame(self.root,bg=BG)
        header.pack(fill='x',padx=10,pady=(7,1))
        title=tk.Label(header,text='iCloud カレンダー',bg=BG,fg=TEXT,
                       font=('Yu Gothic UI',12,'bold'),cursor='fleur')
        title.pack(side='left')
        for widget in (header,title):
            widget.bind('<ButtonPress-1>',self.drag_start)
            widget.bind('<B1-Motion>',self.drag_move)
        self.button(header,'終了',self.close).pack(side='right',padx=2)
        self.button(header,'表示設定',self.display_dialog).pack(side='right',padx=2)

        toolbar=tk.Frame(self.root,bg=BG)
        toolbar.pack(fill='x',padx=10,pady=(0,3))
        self.button(toolbar,'接続',self.connect_dialog).pack(side='left',padx=2)
        self.button(toolbar,'更新確認',self.check_updates_manual).pack(side='left',padx=2)
        self.button(toolbar,'更新',self.refresh).pack(side='left',padx=2)
        self.button(toolbar,'選択',self.pick_calendars).pack(side='left',padx=2)
        self.theme_var=tk.StringVar(value=self.settings.get('theme','ダーク'))
        menu=tk.OptionMenu(toolbar,self.theme_var,*THEMES.keys(),command=self.change_theme)
        menu.configure(bg=PANEL,fg=TEXT,activebackground=PANEL,activeforeground=TEXT,
                       highlightthickness=0,relief='flat',bd=0,font=('Yu Gothic UI',9))
        menu['menu'].configure(bg=PANEL,fg=TEXT)
        menu.pack(side='right',padx=2)

        self.pattern_canvas=tk.Canvas(self.root,bg=BG,highlightthickness=0,borderwidth=0,height=16)
        self.pattern_canvas.pack(fill='x',padx=10)
        self.pattern_canvas.bind('<Configure>',lambda event:self.draw_pattern(event.width))
        body=tk.Frame(self.root,bg=BG)
        body.pack(fill='both',expand=True,padx=9,pady=(3,2))
        self.gridframe=None
        self.month_label=None
        self.listbox=None

        if mode != 'agenda':
            left=tk.Frame(body,bg=BG)
            if mode=='standard':
                left.configure(width=300)
                left.pack(side='left',fill='y',padx=(0,8))
                left.pack_propagate(False)
            else:
                left.pack(fill='both',expand=True)
            nav=tk.Frame(left,bg=BG)
            nav.pack(fill='x',pady=(0,3))
            self.button(nav,'‹',lambda:self.move(-1),width=2).pack(side='left')
            self.month_label=tk.Label(nav,bg=BG,fg=TEXT,font=('Yu Gothic UI',11,'bold'))
            self.month_label.pack(side='left',expand=True)
            self.button(nav,'今日',self.today).pack(side='right')
            self.button(nav,'›',lambda:self.move(1),width=2).pack(side='right')
            self.gridframe=tk.Frame(left,bg=BG)
            self.gridframe.pack(fill='both',expand=True)

        if mode != 'compact':
            right=tk.Frame(body,bg=BG)
            right.pack(side='left',fill='both',expand=True)
            tk.Label(right,text='今後の予定',bg=BG,fg=TEXT,
                     font=('Yu Gothic UI',11,'bold'),anchor='w').pack(fill='x',pady=(2,3))
            wrap=tk.Frame(right,bg=BG)
            wrap.pack(fill='both',expand=True)
            self.listbox=tk.Text(wrap,bg=BG,fg=TEXT,font=('Yu Gothic UI',10),
                                wrap='word',relief='flat',borderwidth=0,
                                highlightthickness=0,spacing3=4,cursor='arrow')
            scroll=ttk.Scrollbar(wrap,orient='vertical',command=self.listbox.yview)
            self.listbox.configure(yscrollcommand=scroll.set,state='disabled')
            scroll.pack(side='right',fill='y')
            self.listbox.pack(side='left',fill='both',expand=True)
            self.listbox.tag_configure('date',foreground=ACCENT,font=('Yu Gothic UI',10,'bold'))
            self.listbox.tag_configure('sub',foreground=SUB)
        self.status=tk.Label(self.root,text='接続待機中',bg=BG,fg=SUB,
                             anchor='w',font=('Yu Gothic UI',8))
        self.status.pack(fill='x',padx=12,pady=(0,4))
        self.draw()

    def draw_pattern(self, width):
        canvas = getattr(self, 'pattern_canvas', None)
        if canvas is None: return
        canvas.delete('all')
        pattern = self.settings.get('pattern', 'なし')
        if pattern not in PATTERNS: pattern = 'なし'
        color = ACCENT
        w = max(100, width)
        if pattern == 'なし':
            canvas.create_line(0,12,w,12,fill=BORDER,width=1)
        elif pattern == 'ドット':
            for x in range(9,w,19):
                for y in (7,19): canvas.create_oval(x-2,y-2,x+2,y+2,fill=color,outline='')
        elif pattern == 'ストライプ':
            for x in range(0,w,16): canvas.create_rectangle(x,3,x+6,23,fill=color,outline='')
        elif pattern == 'グリッド':
            for x in range(0,w,22): canvas.create_line(x,1,x,24,fill=color)
            for y in (2,12,22): canvas.create_line(0,y,w,y,fill=color)
        elif pattern == '斜線':
            for x in range(-30,w,20): canvas.create_line(x,24,x+24,0,fill=color,width=2)
        elif pattern == 'チェック':
            for x in range(0,w,30):
                canvas.create_rectangle(x,1,x+15,12,fill=color,outline='')
                canvas.create_rectangle(x+15,12,x+30,23,fill=color,outline='')
        elif pattern == '波線':
            import math
            for x in range(w-1):
                y1=12+6*math.sin(x/13)
                y2=12+6*math.sin((x+1)/13)
                canvas.create_line(x,y1,x+1,y2,fill=color,width=2)
        elif pattern == 'スター':
            for x in range(16,w,33):
                canvas.create_text(x,12,text='✦',fill=color,font=('Segoe UI Symbol',13))

    def drag_start(self, event):
        self._drag_origin = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def drag_move(self, event):
        if self._drag_origin is not None:
            x = event.x_root - self._drag_origin[0]
            y = event.y_root - self._drag_origin[1]
            self.root.geometry(f'+{max(0,x)}+{max(0,y)}')

    def startup_script_path(self):
        folder = Path(os.environ.get('APPDATA', str(Path.home()))) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'
        return folder / 'iCloudDesktopWidget.vbs'

    def set_startup(self, enabled):
        script = self.startup_script_path()
        if not enabled:
            script.unlink(missing_ok=True)
            return
        exe = Path(sys.executable)
        if exe.name.lower() in ('python.exe', 'python3.exe'):
            silent = exe.with_name('pythonw.exe')
            if silent.exists():
                exe = silent
        app = Path(__file__).resolve()
        # Escape quotes for VBScript strings; no credentials go in this file.
        command = f'"{exe}" "{app}"'
        vbcommand = command.replace('"', '""')
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text('Set sh = CreateObject("WScript.Shell")\n'
                          f'sh.Run "{vbcommand}", 0, False\n', encoding='utf-8')

    def display_dialog(self):
        win=tk.Toplevel(self.root)
        win.title('表示・サイズ・自動起動')
        win.geometry('440x525')
        win.configure(bg=BG)
        tk.Label(win,text='表示モードとウィンドウサイズ',bg=BG,fg=TEXT,
                 font=('Yu Gothic UI',12,'bold')).pack(pady=(10,6))
        reverse={v:k for k,v in LAYOUTS.items()}
        mode_var=tk.StringVar(value=reverse.get(self.layout_mode,'標準（カレンダー＋予定）'))
        chooser=tk.OptionMenu(win,mode_var,*LAYOUTS.keys())
        chooser.configure(bg=PANEL,fg=TEXT,relief='flat',highlightthickness=0)
        chooser['menu'].configure(bg=PANEL,fg=TEXT)
        chooser.pack()
        sizes={'standard':(760,450),'compact':(430,350),'agenda':(410,380)}
        values=tk.Frame(win,bg=BG)
        values.pack(pady=(12,5))
        tk.Label(values,text='横幅(px)',bg=BG,fg=TEXT).grid(row=0,column=0,padx=5)
        tk.Label(values,text='高さ(px)',bg=BG,fg=TEXT).grid(row=0,column=1,padx=5)
        width_var=tk.StringVar(value=str(self.root.winfo_width()))
        height_var=tk.StringVar(value=str(self.root.winfo_height()))
        tk.Entry(values,textvariable=width_var,width=9,font=('Segoe UI',11)).grid(row=1,column=0,padx=5)
        tk.Entry(values,textvariable=height_var,width=9,font=('Segoe UI',11)).grid(row=1,column=1,padx=5)
        def preset():
            w,h=sizes[LAYOUTS[mode_var.get()]]
            width_var.set(str(w));height_var.set(str(h))
        self.button(win,'このモードの推奨サイズを入力',preset).pack(pady=(4,7))
        border_var=tk.BooleanVar(value=self.borderless)
        tk.Checkbutton(win,text='枠なし表示',variable=border_var,bg=BG,fg=TEXT,
                       selectcolor=PANEL,activebackground=BG,activeforeground=TEXT).pack(anchor='w',padx=35)
        tk.Label(win,text='透明度',bg=BG,fg=TEXT).pack(pady=(5,0))
        alpha=tk.DoubleVar(value=float(self.settings.get('opacity',0.96)))
        tk.Scale(win,from_=0.60,to=1.0,resolution=0.05,orient='horizontal',
                 variable=alpha,bg=BG,fg=TEXT,highlightthickness=0,
                 troughcolor=PANEL,length=280).pack()
        tk.Label(win,text='装飾パターン',bg=BG,fg=TEXT).pack(pady=(3,0))
        pattern_var=tk.StringVar(value=self.settings.get('pattern','なし'))
        pm=tk.OptionMenu(win,pattern_var,*PATTERNS)
        pm.configure(bg=PANEL,fg=TEXT,highlightthickness=0,relief='flat')
        pm['menu'].configure(bg=PANEL,fg=TEXT)
        pm.pack()
        startup=tk.BooleanVar(value=self.startup_script_path().exists())
        tk.Checkbutton(win,text='Windowsログイン時に自動起動',variable=startup,
                       bg=BG,fg=TEXT,selectcolor=PANEL,
                       activebackground=BG,activeforeground=TEXT).pack(anchor='w',padx=35,pady=(7,1))
        def apply():
            try:
                mode=LAYOUTS[mode_var.get()]
                width,height=int(width_var.get()),int(height_var.get())
                minw,minh=MIN_SIZE[mode]
                if not (minw<=width<=3200 and minh<=height<=2000):
                    raise ValueError(f'このモードのサイズは横{minw}～3200、縦{minh}～2000 pxです')
                self.set_startup(startup.get())
                self.settings.update(pattern=pattern_var.get(),opacity=alpha.get(),
                                     borderless=border_var.get(),layout_mode=mode)
                self.layout_mode=mode
                self.root.minsize(*MIN_SIZE[mode])
                self.root.geometry(f'{width}x{height}+{self.root.winfo_x()}+{self.root.winfo_y()}')
                self.root.attributes('-alpha',alpha.get())
                if self.borderless != border_var.get():
                    self.borderless=border_var.get()
                    self.root.overrideredirect(self.borderless)
                save_settings(self.settings)
                self.build()
                win.destroy()
            except (ValueError,tk.TclError,OSError) as exc:
                messagebox.showerror('設定を確認してください',str(exc),parent=win)
        self.button(win,'保存して適用',apply).pack(pady=12)

    def change_theme(self, name):
        self.settings['theme']=name
        save_settings(self.settings)
        set_theme(name)
        self.build()
        if self.last_good:
            self.status.configure(text=f'{len(self.calendars)}個のカレンダー・{len(self.events)}件 / 更新 {self.last_good:%H:%M}')

    def move(self, delta):
        y=self.show_month.year; m=self.show_month.month+delta
        y+=(m-1)//12; m=(m-1)%12+1
        self.show_month=dt.date(y,m,1)
        self.draw()
        self.refresh()

    def today(self):
        self.show_month=dt.date.today().replace(day=1)
        self.draw()
        self.refresh()

    def draw(self):
        if self.gridframe is None:
            self.render_events()
            return
        for child in self.gridframe.winfo_children(): child.destroy()
        y,m=self.show_month.year,self.show_month.month
        self.month_label.configure(text=f'{y}年 {m}月')
        for col,name in enumerate(['月','火','水','木','金','土','日']):
            fg='#85befe' if col==5 else '#ffa0a4' if col==6 else SUB
            tk.Label(self.gridframe,text=name,bg=BG,fg=fg,font=('Yu Gothic UI',9),height=1).grid(row=0,column=col,sticky='nsew')
            self.gridframe.grid_columnconfigure(col,weight=1,uniform='days')
        today=dt.date.today()
        count={}
        selected=set(self.settings.get('selected',[]))
        for e in self.events:
            if selected and e['cal_id'] not in selected: continue
            start=e['start'].date(); end=e['end'].date()
            if e['all_day'] and end>start: end-=dt.timedelta(days=1)
            d=start
            while d<=end and (d-start).days<370:
                count[d]=count.get(d,0)+1; d+=dt.timedelta(days=1)
        for row,week in enumerate(calendar.Calendar(firstweekday=0).monthdatescalendar(y,m),start=1):
            for col,date in enumerate(week):
                current=(date.month==m)
                bg=TODAY_BG if date==today else PANEL if current else BG
                f=TEXT if current else INACTIVE
                cell=tk.Frame(self.gridframe,bg=bg,height=32 if self.layout_mode=='compact' else 40)
                cell.grid(row=row,column=col,sticky='nsew',padx=2,pady=2)
                cell.grid_propagate(False)
                tk.Label(cell,text=str(date.day),fg=f,bg=bg,font=('Yu Gothic UI',10,'bold' if date==today else 'normal')).pack(pady=(4,0))
                if count.get(date):
                    tk.Label(cell,text='●'*min(3,count[date]),fg=ACCENT,bg=bg,font=('Arial',7)).pack()
        self.render_events()

    def render_events(self):
        if self.listbox is None: return
        self.listbox.config(state='normal')
        self.listbox.delete('1.0','end')
        now=dt.datetime.now(JST)
        selected=set(self.settings.get('selected',[]))
        shown=[e for e in self.events if e['end']>=now and (not selected or e['cal_id'] in selected)]
        shown.sort(key=lambda e:e['start'])
        if not shown: self.listbox.insert('end','表示する予定がありません。\n','sub')
        previous=None
        for e in shown[:45]:
            day=e['start'].date()
            if day != previous:
                self.listbox.insert('end',f'\n{day.month}/{day.day}（{"月火水木金土日"[day.weekday()]}）\n','date')
                previous=day
            time='終日' if e['all_day'] else e['start'].strftime('%H:%M')
            self.listbox.insert('end',f'  {time}  {e["summary"]}\n')
            self.listbox.insert('end',f'          {e["cal_name"]}\n','sub')
        self.listbox.config(state='disabled')

    def check_updates_manual(self):
        self.check_updates(silent=False)

    def check_updates_silent(self):
        self.check_updates(silent=True)

    def check_updates(self, silent=False):
        repo = self.settings.get('update_repo', '').strip()
        if not repo:
            if not silent:
                self.configure_updates()
            return
        if not __import__('re').fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
            if not silent: messagebox.showerror('更新設定', 'owner/repository の形式で入力してください。')
            return
        def work():
            try:
                request=urllib.request.Request(UPDATE_API.format(repo=repo), headers={'User-Agent':f'iCloudDesktopWidget/{VERSION}','Accept':'application/vnd.github+json'})
                with urllib.request.urlopen(request, timeout=12) as response:
                    latest=json.load(response)
                version=latest.get('tag_name','').lstrip('v')
                def nums(s):
                    if not __import__('re').fullmatch(r'\d+(?:\.\d+){1,3}',s): return None
                    return tuple(int(x) for x in s.split('.'))
                if nums(version) is None: raise ValueError('GitHubのバージョン番号が不正です')
                if nums(version) <= nums(VERSION):
                    self.msgq.put(('up_to_date', silent))
                    return
                assets={a.get('name'):a for a in latest.get('assets', [])}
                asset=assets.get('icloud_widget.py')
                checksum=assets.get('icloud_widget.py.sha256')
                if not asset or not checksum: raise ValueError('必要な更新ファイルとSHA256ファイルがありません')
                self.msgq.put(('update_available', version, asset['browser_download_url'], checksum['browser_download_url']))
            except Exception as exc:
                self.msgq.put(('update_check_error', silent, str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def configure_updates(self):
        win=tk.Toplevel(self.root);win.title('自動アップデート設定');win.geometry('440x225');win.configure(bg=BG)
        tk.Label(win,text='更新配信元のGitHub（owner/repository）',bg=BG,fg=TEXT,font=('Yu Gothic UI',11)).pack(pady=(18,5))
        entry=tk.Entry(win,font=('Consolas',11));entry.insert(0,self.settings.get('update_repo',''));entry.pack(fill='x',padx=20)
        tk.Label(win,text='例: yourname/iCloudDesktopWidget',bg=BG,fg=SUB).pack(pady=5)
        auto_var=tk.BooleanVar(value=self.settings.get('auto_update',False))
        tk.Checkbutton(win,text='確認なしで更新を適用（自分のGitHubリポジトリのみ推奨）',variable=auto_var,bg=BG,fg=TEXT,selectcolor=PANEL,activebackground=BG,activeforeground=TEXT).pack(pady=4)
        def save():
            value=entry.get().strip()
            if value and not __import__('re').fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',value):
                messagebox.showerror('入力形式','owner/repository の形式にしてください。',parent=win);return
            self.settings['update_repo']=value;self.settings['auto_update']=auto_var.get();save_settings(self.settings);win.destroy()
            if value:self.check_updates(silent=False)
        self.button(win,'保存して確認',save).pack(pady=9)

    def install_update(self,version,program_url,sha_url):
        if not self.settings.get('auto_update', False):
            if not messagebox.askyesno('アップデート',f'バージョン {version} が公開されています。\n更新をダウンロードしますか？\n\n接続設定は引き継がれます。'):
                return
        def work():
            try:
                def fetch(url,limit):
                    if not url.startswith('https://github.com/'):
                        raise ValueError('GitHub以外からは取得できません')
                    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'iCloudDesktopWidget'}),timeout=30) as response:
                        content=response.read(limit+1)
                    if len(content)>limit:raise ValueError('更新ファイルのサイズが大きすぎます')
                    return content
                raw=fetch(program_url,1_000_000)
                expected=fetch(sha_url,1000).decode('utf-8').strip().split()[0].lower()
                if not __import__('re').fullmatch('[0-9a-f]{64}',expected):raise ValueError('ハッシュ形式が不正です')
                if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('SHA256が一致しません。更新を中止しました。')
                compile(raw.decode('utf-8'),'icloud_widget.py','exec')
                target=Path(__file__).resolve()
                staged=target.with_name('icloud_widget.pending.py')
                staged.write_bytes(raw)
                self.msgq.put(('update_ready',str(target),str(staged),version))
            except Exception as exc:
                self.msgq.put(('update_failure',str(exc)))
        threading.Thread(target=work,daemon=True).start()

    def apply_update(self,target,staged,version):
        # Run a tiny helper only after this process exits; it replaces the app file and starts the app again.
        launcher=Path(__file__).resolve().with_name('apply_update.cmd')
        launcher.write_text("""@echo off
setlocal
cd /d "%~dp0"
:wait
ping 127.0.0.1 -n 2 >nul
move /Y "icloud_widget.pending.py" "icloud_widget.py" >nul
if exist "icloud_widget.pending.py" goto wait
start "" "%~dp0start_calendar.bat"
""", encoding='ascii')
        subprocess.Popen(['cmd','/c',str(launcher)],cwd=str(Path(__file__).resolve().parent),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.close()

    def connect_dialog(self):
        win=tk.Toplevel(self.root); win.title('iCloud 接続設定');win.configure(bg=BG)
        win.geometry('390x270');win.resizable(False,False);win.transient(self.root)
        tk.Label(win,text='Apple Accountのメールアドレス',bg=BG,fg=TEXT).pack(anchor='w',padx=20,pady=(15,3))
        email=tk.Entry(win,font=('Yu Gothic UI',11)); email.insert(0,self.user);email.pack(fill='x',padx=20)
        tk.Label(win,text='アプリ用パスワード（通常のパスワードではありません）',bg=BG,fg=TEXT).pack(anchor='w',padx=20,pady=(12,3))
        pw=tk.Entry(win,font=('Yu Gothic UI',11),show='●');pw.pack(fill='x',padx=20)
        tk.Label(win,text='パスワードはWindowsの資格情報保管庫に保存。\nこのアプリはカレンダーの読み取りのみ実行します。',bg=BG,fg=SUB,justify='left').pack(anchor='w',padx=20,pady=9)
        def ok():
            username=email.get().strip(); secret=pw.get().strip().replace(' ','')
            if not username or (not secret and not (username==self.user and self.password)):
                messagebox.showwarning('入力不足','メールアドレスとアプリ用パスワードを入力してください。',parent=win);return
            if self.user and username!=self.user:
                keyring.delete_password(SERVICE,self.user) if keyring.get_password(SERVICE,self.user) else None
            self.user=username
            if secret:
                self.password=secret;keyring.set_password(SERVICE,username,secret)
            self.settings['email']=username;self.settings['selected']=[];save_settings(self.settings)
            win.destroy();self.refresh()
        self.button(win,'接続して予定を取得',ok).pack(pady=8)
        win.grab_set()

    def pick_calendars(self):
        if not self.calendars:
            messagebox.showinfo('カレンダー未取得','先にiCloudへ接続してください。');return
        win=tk.Toplevel(self.root);win.title('表示カレンダー');win.configure(bg=BG);win.geometry('350x370')
        tk.Label(win,text='表示するカレンダーを選択',bg=BG,fg=TEXT,font=('Yu Gothic UI',12,'bold')).pack(pady=13)
        current=set(self.settings.get('selected',[]))
        flags=[]
        for cal in self.calendars:
            var=tk.BooleanVar(value=(not current or cal['id'] in current))
            tk.Checkbutton(win,text=cal['name'],variable=var,bg=BG,fg=TEXT,selectcolor=PANEL,
                           activebackground=BG,activeforeground=TEXT,anchor='w').pack(fill='x',padx=20)
            flags.append((cal['id'],var))
        def apply():
            ids=[cid for cid,v in flags if v.get()]
            if not ids:messagebox.showwarning('選択が必要','1つ以上選択してください。',parent=win);return
            self.settings['selected']=ids;save_settings(self.settings);win.destroy();self.draw()
        self.button(win,'反映',apply).pack(pady=16)

    def refresh(self):
        if self.busy: return
        if not self.user or not self.password:
            self.status.configure(text='⚙ からiCloudに接続してください')
            self.root.after(200,self.connect_dialog)
            return
        self.busy=True
        self.status.configure(text='iCloudから取得中…')
        year,month=self.show_month.year,self.show_month.month
        start=dt.datetime(year,month,1,tzinfo=JST)
        end=start+dt.timedelta(days=75)
        # Events are fetched for previous week too, to catch longer multi-day entries
        start-=dt.timedelta(days=7)
        threading.Thread(target=self.worker,args=(self.user,self.password,start,end),daemon=True).start()

    def worker(self,username,password,start,end):
        try:
            calendars=[];events=[]
            with caldav.DAVClient(url='https://caldav.icloud.com/',username=username,password=password,timeout=25) as client:
                principal=client.principal()
                cals=principal.calendars()
                errors=[]
                for index,cal in enumerate(cals):
                    name=str(cal.name or f'カレンダー {index+1}')
                    cid=str(cal.url)
                    calendars.append({'id':cid,'name':name})
                    try:
                        results=cal.search(start=start,end=end,event=True,expand=True)
                        for result in results:
                            try:
                                # One VEVENT per expanded instance is typical; handle all VEVENTs.
                                ical=result.icalendar_instance
                                for component in ical.walk('VEVENT'):
                                    vstart=component.get('DTSTART');vend=component.get('DTEND')
                                    if not vstart:continue
                                    raw=vstart.dt;begin=event_time(raw)
                                    finish=event_time(vend.dt) if vend else begin+dt.timedelta(days=1 if isinstance(raw,dt.date) and not isinstance(raw,dt.datetime) else 0)
                                    if begin is None:continue
                                    if finish is None:finish=begin
                                    events.append({'cal_id':cid,'cal_name':name,'start':begin,'end':finish,
                                                   'all_day':isinstance(raw,dt.date) and not isinstance(raw,dt.datetime),
                                                   'summary':str(component.get('SUMMARY','（タイトルなし）'))})
                            except Exception: continue
                    except Exception as ex: errors.append(f'{name}: {str(ex)[:65]}')
            if not calendars: raise RuntimeError('iCloudからカレンダー一覧を取得できませんでした。')
            self.msgq.put(('data',calendars,events,errors))
        except Exception as exc:
            self.msgq.put(('error',str(exc)))

    def pump(self):
        try:
            while True:
                result=self.msgq.get_nowait()
                self.busy=False
                if result[0]=='update_available':
                    _,ver,url,sha=result
                    self.install_update(ver,url,sha)
                elif result[0]=='update_ready':
                    _,target,staged,ver=result
                    self.apply_update(target,staged,ver)
                elif result[0]=='up_to_date':
                    if not result[1]:messagebox.showinfo('アップデート',f'最新版です（v{VERSION}）。')
                elif result[0]=='update_check_error':
                    if not result[1]:messagebox.showwarning('更新確認に失敗',result[2])
                elif result[0]=='update_failure':
                    messagebox.showerror('更新失敗',result[1])
                elif result[0]=='data':
                    _,self.calendars,self.events,errors=result
                    if not self.settings.get('selected'):
                        self.settings['selected']=[x['id'] for x in self.calendars]
                        save_settings(self.settings)
                    self.draw()
                    self.last_good=dt.datetime.now(JST)
                    self.status.configure(text=f'{len(self.calendars)}個のカレンダー・{len(self.events)}件 / 更新 {self.last_good:%H:%M}'+(' / 一部取得失敗' if errors else ''))
                    if errors: messagebox.showwarning('一部取得できませんでした','\n'.join(errors[:3]))
                else:
                    self.status.configure(text='同期失敗（前回の表示を維持）')
                    messagebox.showerror('iCloud接続エラー',result[1]+'\n\nメールアドレス・アプリ用パスワードとネット接続を確認してください。')
        except queue.Empty: pass
        self.root.after(250,self.pump)

    def periodic(self):
        self.refresh()
        self.root.after(15*60*1000,self.periodic)

    def close(self):
        self.settings['geometry_v2']=self.root.geometry()
        save_settings(self.settings)
        self.root.destroy()

if __name__=='__main__':
    root=tk.Tk();Widget(root);root.mainloop()
