// iCloud Lock Calendar for Scriptable - v1.5.0
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
box(0,0,1000,2160,bg);
if(photo){
 const iw=photo.size.width,ih=photo.size.height;
 const scale=Math.max(W/iw,H/ih);
 const dw=iw*scale,dh=ih*scale;
 ctx.drawImageInRect(photo,new Rect((W-dw)/2,(H-dh)/2,dw,dh));
 // Preserve the full photograph, with a subtle contrast layer below the iPhone clock.
 box(0,520,1000,1640,"#07121B",.17);
}
const textColor=photo?"#F7FAFF":fg;
const mutedColor=photo?"#D8E5EF":fg;
const now=date;
const counts=new Map();
for(const e of events){
 let d=new Date(e.startDate.getFullYear(),e.startDate.getMonth(),e.startDate.getDate());
 const end=new Date(e.endDate.getFullYear(),e.endDate.getMonth(),e.endDate.getDate());
 if(e.isAllDay && end>d)end.setDate(end.getDate()-1);
 for(let n=0;n<60&&d<=end;n++,d.setDate(d.getDate()+1)){
  const k=d.getFullYear()+"-"+d.getMonth()+"-"+d.getDate();
  counts.set(k,(counts.get(k)||0)+1);
 }
}
// Both panels sit safely below the native iPhone clock.
rounded(34,555,932,790,36,"#09182C",photo?.79:.98);
rounded(34,1370,932,745,36,"#09182C",photo?.81:.98);
// A translucent rim gives the panels a soft, native iOS feel.
rounded(50,568,900,3,1,"#77C9FF",.55);
rounded(50,1383,900,3,1,"#77C9FF",.48);
label("CALENDAR",80,607,390,55,27,"#8ACFFF",true);
label(now.getFullYear()+"  /  "+String(now.getMonth()+1).padStart(2,"0"),80,682,700,75,54,textColor,false);
rule(80,773,840);
const weekdays=["月","火","水","木","金","土","日"];
for(let i=0;i<7;i++)label(weekdays[i],94+i*120,812,87,46,25,mutedColor,false);
const offset=(monthStart.getDay()+6)%7;
const days=new Date(now.getFullYear(),now.getMonth()+1,0).getDate();
for(let n=1;n<=days;n++){
 const c=n-1+offset;
 const row=Math.floor(c/7),col=c%7;
 const x=91+col*120,y=896+row*70;
 if(n===now.getDate())rounded(x-12,y-5,69,64,17,"#2D75BC",.95);
 label(n,x,y,65,45,31,textColor,n===now.getDate());
 const k=now.getFullYear()+"-"+now.getMonth()+"-"+n;
 const num=Math.min(3,counts.get(k)||0);
 for(let j=0;j<num;j++)
  ellipse(x+j*13,y+47,7,7,"#76C7FF",.95);
}
label("今日・明日の予定",80,1414,470,54,29,"#8ACFFF",true);
label(upcoming.length+" 件",764,1416,170,50,24,mutedColor,false);
rule(80,1482,840);
if(upcoming.length===0)label("今日と明日の予定はありません",84,1545,825,70,32,textColor);
const rowHeight=74;
for(let i=0;i<upcoming.length;i++){
 const e=upcoming[i],d=e.startDate,y=1516+i*rowHeight;
 if(i%2===0)rounded(68,y-4,864,66,15,"#2C5D8C",.18);
 const actualDay=e.startDate<todayStart?todayStart:d;
 const dateText=actualDay.toDateString()===todayStart.toDateString()?"今日":"明日";
 label(dateText,87,y+7,110,49,29,"#8ACFFF",true);
 label(formatTime(e),202,y+8,130,48,28,mutedColor,false);
 label(title(e.title,20),345,y+7,575,52,30,textColor,i===0);
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
