// iCloud Lock Calendar for Scriptable - v1.7.0
// iPhone-local calendars and photographs only. No Apple credentials required.
// For automatic updates, run the LockCalendarLauncher in Scriptable.
const automatic = !config.runsInApp || args.shortcutParameter === "auto" || args.shortcutParameter === "AUTO";
const SETTINGS = {
  style: "midnight", maxEvents: 8, photo: true,
  shade: 0.42, excludedCalendars: []
};
const THEMES = {
 midnight: ["#121b2b","#dfeeff","#88c9ff","#29465f"],
 ocean: ["#083245","#e6faff","#67d9df","#176677"],
 forest: ["#133025","#e3ffeb","#8cdc9c","#32664c"],
 sakura: ["#40243a","#fff0f7","#ffacd4","#79415e"],
 ivory: ["#f8f1df","#353d49","#246b99","#e1d2ae"]
};
const theme=THEMES[SETTINGS.style]||THEMES.midnight;
const [bg,fg,accent,todayColor]=theme;
const fm=FileManager.local();
const folder=fm.joinPath(fm.documentsDirectory(),"LockCalendar");
if(!fm.fileExists(folder))fm.createDirectory(folder,true);
const photoPath=fm.joinPath(folder,"Background.jpg");
let photo=null;
if(SETTINGS.photo){
  if(config.runsInApp && !automatic && !fm.fileExists(photoPath)){
    const prompt=new Alert();
    prompt.title="ロック画面の背景写真";
    prompt.message="好きな写真を背景にできます。";
    prompt.addAction("保存済みの写真を使用");
    prompt.addAction("新しい写真を選択");
    const choice=await prompt.presentSheet();
    if(choice===1){
      photo=await Photos.fromLibrary();
      fm.writeImage(photoPath,photo);
    }
  }
  if(!photo && fm.fileExists(photoPath))photo=fm.readImage(photoPath);
}
const date=new Date();
const monthStart=new Date(date.getFullYear(),date.getMonth(),1);
const monthEnd=new Date(date.getFullYear(),date.getMonth()+2,1);
const calendars=(await Calendar.forEvents()).filter(c=>!SETTINGS.excludedCalendars.includes(c.title));
const events=(await CalendarEvent.between(monthStart,monthEnd,calendars)).sort((a,b)=>a.startDate-b.startDate);
// Today's and tomorrow's entries only; include all-day and multi-day events.
const todayStart=new Date(date.getFullYear(),date.getMonth(),date.getDate());
const afterTomorrow=new Date(date.getFullYear(),date.getMonth(),date.getDate()+2);
const relevant=events.filter(e=>e.startDate<afterTomorrow && (e.endDate>todayStart || (e.startDate>=todayStart && e.endDate.getTime()===e.startDate.getTime())));
const upcoming=relevant.slice(0,SETTINGS.maxEvents);
const resolution=Device.screenResolution();
const W=Math.min(resolution.width,resolution.height);
const H=Math.max(resolution.width,resolution.height);
const xx=n=>n*W/1000, yy=n=>n*H/2160;
const ctx=new DrawContext();
ctx.size=new Size(W,H);ctx.opaque=true;ctx.respectScreenScale=false;
function box(x,y,w,h,color,alpha=1){
  ctx.setFillColor(new Color(color,alpha));
  ctx.fillRect(new Rect(xx(x),yy(y),xx(w),yy(h)));
}
function label(t,x,y,w,h,size,color=fg,isBold=false){
  ctx.setFont(isBold?Font.boldSystemFont(xx(size)):Font.systemFont(xx(size)));
  ctx.setTextColor(new Color(color));
  ctx.drawTextInRect(String(t),new Rect(xx(x),yy(y),xx(w),yy(h)));
}
function formatTime(e){
  if(e.isAllDay)return "終日";
  let d=e.startDate;
  return String(d.getHours()).padStart(2,"0")+":"+String(d.getMinutes()).padStart(2,"0");
}
function title(s,n=18){
  let chars=Array.from(s||"（タイトルなし）");
  return chars.length>n?chars.slice(0,n-1).join("")+"…":chars.join("");
}
function rounded(x,y,w,h,r,color,alpha=1){
 const p=new Path();
 p.addRoundedRect(new Rect(xx(x),yy(y),xx(w),yy(h)),xx(r),yy(r));
 ctx.addPath(p);ctx.setFillColor(new Color(color,alpha));ctx.fillPath();
}
function ellipse(x,y,w,h,color,alpha=1){
 ctx.setFillColor(new Color(color,alpha));
 ctx.fillEllipse(new Rect(xx(x),yy(y),xx(w),yy(h)));
}
function rule(x,y,w,color="#FFFFFF",alpha=.15){
 box(x,y,w,2,color,alpha);
}
// Refined editorial layout – photo and native iPhone clock are preserved.
const ink="#111315",gold="#C7A86A",ivory="#F7F7F5",muted="#C8C5BE";
function elegant(value,x,y,w,h,size,hex,bold=false,align="left",light=false){
 ctx.setTextColor(new Color(hex));
 ctx.setFont(light?Font.lightSystemFont(xx(size)):bold?Font.boldSystemFont(xx(size)):Font.systemFont(xx(size)));
 if(align==="center")ctx.setTextAlignedCenter();
 else if(align==="right")ctx.setTextAlignedRight();
 else ctx.setTextAlignedLeft();
 ctx.drawTextInRect(String(value),new Rect(xx(x),yy(y),xx(w),yy(h)));
 ctx.setTextAlignedLeft();
}
box(0,0,1000,2160,bg);
if(photo){
 const scale=Math.max(W/photo.size.width,H/photo.size.height);
 const dw=photo.size.width*scale,dh=photo.size.height*scale;
 ctx.drawImageInRect(photo,new Rect((W-dw)/2,(H-dh)/2,dw,dh));
} 
// Gentle tint only below the real iPhone clock, no baked-in clock overlay.
box(0,540,1000,1510,"#071019",photo?.11:.05);
const now=date;
const counts=new Map();
for(const e of events){
 let d=new Date(e.startDate.getFullYear(),e.startDate.getMonth(),e.startDate.getDate());
 const end=new Date(e.endDate.getFullYear(),e.endDate.getMonth(),e.endDate.getDate());
 if(e.isAllDay && end>d)end.setDate(end.getDate()-1);
 for(let n=0;n<60&&d<=end;n++,d.setDate(d.getDate()+1)){
  const key=d.getFullYear()+"-"+d.getMonth()+"-"+d.getDate();
  counts.set(key,(counts.get(key)||0)+1);
 }
}
const calendarY=585;
rounded(58,calendarY,884,760,34,ink,photo?.50:.94);
box(86,calendarY+88,160,3,gold,.95);
elegant("C A L E N D A R",86,calendarY+31,410,48,24,gold);
elegant(now.getFullYear()+" / "+String(now.getMonth()+1).padStart(2,"0"),
  86,calendarY+109,600,83,51,ivory,false,"left",true);
const weekdayNames=["MON","TUE","WED","THU","FRI","SAT","SUN"];
for(let i=0;i<7;i++){
 elegant(weekdayNames[i],97+i*118,calendarY+212,86,37,19,muted,false,"center");
}
const offset=(monthStart.getDay()+6)%7;
const days=new Date(now.getFullYear(),now.getMonth()+1,0).getDate();
const weeks=Math.ceil((offset+days)/7);
const step=weeks===6?68:77;
for(let day=1;day<=days;day++){
 const position=offset+day-1,col=position%7,row=Math.floor(position/7);
 const x=97+col*118,y=calendarY+279+row*step;
 const isToday=day===now.getDate();
 if(isToday)rounded(x+9,y-5,61,54,15,ivory,.95);
 elegant(day,x,y,80,47,30,isToday?"#111315":ivory,isToday,"center",!isToday);
 const key=now.getFullYear()+"-"+now.getMonth()+"-"+day;
 const num=Math.min(3,counts.get(key)||0);
 for(let j=0;j<num;j++)ellipse(x+33+j*11,y+50,6,6,gold,.96);
}
const scheduleY=1385;
rounded(58,scheduleY,884,546,34,"#15181B",photo?.62:.95);
box(86,scheduleY+83,185,3,gold,.95);
elegant("T O D A Y  /  T O M O R R O W",86,scheduleY+30,720,54,24,gold);
const shown=upcoming.slice(0,4);
if(shown.length===0){
 elegant("今日・明日の予定はありません",90,scheduleY+150,760,72,31,ivory,false,"left",true);
} else {
 const todayStart=new Date(now.getFullYear(),now.getMonth(),now.getDate());
 const tomorrowStart=new Date(now.getFullYear(),now.getMonth(),now.getDate()+1);
 for(let i=0;i<shown.length;i++){
  const e=shown[i],y=scheduleY+128+i*92;
  if(i>0)box(88,y-15,814,2,"#FFFFFF",.11);
  const dayLabel=e.startDate<tomorrowStart?"TODAY":"TOMORROW";
  elegant(dayLabel,88,y+3,152,35,19,gold);
  elegant(e.isAllDay?"終日":formatTime(e),88,y+34,150,33,22,muted);
  elegant(title(e.title,24),253,y+10,625,58,30,ivory,false,"left",true);
 }
}
const image=ctx.getImage();
const cloud=FileManager.iCloud();
const dir=cloud.joinPath(cloud.documentsDirectory(),"LockCalendar");
if(!cloud.fileExists(dir))cloud.createDirectory(dir,true);
const output=cloud.joinPath(dir,"LockCalendar.png");
cloud.writeImage(output,image);
// Shortcuts receives the generated PNG as an iCloud file path.
if(config.runsInApp && !automatic){
  await Photos.save(image);
  await QuickLook.present(image);
}
return output;
