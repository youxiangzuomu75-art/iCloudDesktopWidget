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
VERSION = '2.1.0'
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
}

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
        root.minsize(640, 365)
        root.attributes('-topmost', False)
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
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill='x', padx=16, pady=(11, 8))
        tk.Label(header,text='iCloud カレンダー',bg=BG,fg=TEXT,
                 font=('Yu Gothic UI',14,'bold')).pack(side='left')
        self.button(header,'⚙ 接続',self.connect_dialog).pack(side='right',padx=(5,0))
        self.button(header,'更新確認',self.check_updates_manual).pack(side='right',padx=(5,0))
        self.button(header,'↻ 更新',self.refresh).pack(side='right',padx=(5,0))
        self.button(header,'選択',self.pick_calendars).pack(side='right',padx=(5,0))
        choices=list(THEMES.keys())
        self.theme_var=tk.StringVar(value=self.settings.get('theme','ダーク'))
        menu=tk.OptionMenu(header,self.theme_var,*choices,command=self.change_theme)
        menu.configure(bg=PANEL,fg=TEXT,activebackground=PANEL,activeforeground=TEXT,
                       highlightthickness=0,relief='flat',bd=0,font=('Yu Gothic UI',9))
        menu['menu'].configure(bg=PANEL,fg=TEXT)
        menu.pack(side='right',padx=(7,0))
        tk.Frame(self.root,bg=BORDER,height=1).pack(fill='x',padx=16)

        body=tk.Frame(self.root,bg=BG)
        body.pack(fill='both',expand=True,padx=13,pady=(8,4))
        left=tk.Frame(body,bg=BG,width=340)
        left.pack(side='left',fill='y',padx=(0,12))
        left.pack_propagate(False)
        right=tk.Frame(body,bg=BG)
        right.pack(side='left',fill='both',expand=True)

        nav=tk.Frame(left,bg=BG)
        nav.pack(fill='x',pady=(0,5))
        self.button(nav,'‹',lambda:self.move(-1),width=2).pack(side='left')
        self.month_label=tk.Label(nav,bg=BG,fg=TEXT,font=('Yu Gothic UI',12,'bold'))
        self.month_label.pack(side='left',expand=True)
        self.button(nav,'今日',self.today).pack(side='right')
        self.button(nav,'›',lambda:self.move(1),width=2).pack(side='right')
        self.gridframe=tk.Frame(left,bg=BG)
        self.gridframe.pack(fill='both',expand=True)

        tk.Label(right,text='今後の予定',bg=BG,fg=TEXT,
                 font=('Yu Gothic UI',12,'bold'),anchor='w').pack(fill='x',pady=(4,6))
        wrap=tk.Frame(right,bg=BG)
        wrap.pack(fill='both',expand=True)
        self.listbox=tk.Text(wrap,bg=BG,fg=TEXT,font=('Yu Gothic UI',10),wrap='word',
                     relief='flat',borderwidth=0,highlightthickness=0,spacing3=4,cursor='arrow')
        scroll=ttk.Scrollbar(wrap,orient='vertical',command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set,state='disabled')
        scroll.pack(side='right',fill='y')
        self.listbox.pack(side='left',fill='both',expand=True)
        self.listbox.tag_configure('date',foreground=ACCENT,font=('Yu Gothic UI',10,'bold'))
        self.listbox.tag_configure('sub',foreground=SUB)
        self.status=tk.Label(self.root,text='接続待機中',bg=BG,fg=SUB,anchor='w',font=('Yu Gothic UI',9))
        self.status.pack(fill='x',padx=17,pady=(1,7))
        self.draw()

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
                cell=tk.Frame(self.gridframe,bg=bg,height=40)
                cell.grid(row=row,column=col,sticky='nsew',padx=2,pady=2)
                cell.grid_propagate(False)
                tk.Label(cell,text=str(date.day),fg=f,bg=bg,font=('Yu Gothic UI',10,'bold' if date==today else 'normal')).pack(pady=(4,0))
                if count.get(date):
                    tk.Label(cell,text='●'*min(3,count[date]),fg=ACCENT,bg=bg,font=('Arial',7)).pack()
        self.render_events()

    def render_events(self):
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
