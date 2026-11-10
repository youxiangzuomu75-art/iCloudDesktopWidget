// iCloud Lock Calendar for Scriptable - v1.6.0
// Minimal Black: monthly calendar and today/tomorrow appointments.
// Auto-loaded by LockCalendarLauncher.js; no credentials leave this iPhone.
const STYLE = {
  bg:"#000000", white:"#FFFFFF", gray:"#A7A7A7", accent:"#BCA77B",
  panel:"#202020", panelOpacity:0.94, maxEvents:8, displayedEvents:4
};
const now=new Date();
const today=new Date(now.getFullYear(),now.getMonth(),now.getDate());
const tomorrow=new Date(now.getFullYear(),now.getMonth(),now.getDate()+1);
const dayAfter=new Date(now.getFullYear(),now.getMonth(),now.getDate()+2);
const calendars=await Calendar.forEvents();
const events=(await CalendarEvent.between(today,dayAfter,calendars))
  .filter(e=>e.startDate<dayAfter && e.endDate>today)
  .sort((a,b)=>a.startDate-b.startDate);
const W=Math.min(Device.screenResolution().width,Device.screenResolution().height);
const H=Math.max(Device.screenResolution().width,Device.screenResolution().height);
const ctx=new DrawContext();
ctx.size=new Size(W,H);
ctx.opaque=true;
ctx.respectScreenScale=false;
const sx=v=>W*v/1000, sy=v=>H*v/2160;
function color(hex,alpha=1){return new Color(hex,alpha);}
function rect(x,y,w,h,fill,alpha=1){
  ctx.setFillColor(color(fill,alpha));
  ctx.fillRect(new Rect(sx(x),sy(y),sx(w),sy(h)));
}
function rounded(x,y,w,h,r,fill,alpha=1){
  const p=new Path();
  p.addRoundedRect(new Rect(sx(x),sy(y),sx(w),sy(h)),sx(r),sx(r));
  ctx.addPath(p); ctx.setFillColor(color(fill,alpha)); ctx.fillPath();
}
function text(value,x,y,w,h,size,fill,bold=false){
  ctx.setTextColor(color(fill));
  ctx.setFont(bold?Font.boldSystemFont(sx(size)):Font.systemFont(sx(size)));
  ctx.drawTextInRect(String(value),new Rect(sx(x),sy(y),sx(w),sy(h)));
}
function line(x,y,w,fill=STYLE.gray,alpha=.35){
  rect(x,y,w,1.5,fill,alpha);
}
function timeLabel(e){
  if(e.isAllDay)return "終日";
  const d=e.startDate;
  return String(d.getHours()).padStart(2,"0")+":"+String(d.getMinutes()).padStart(2,"0");
}
function shorten(name,limit=20){
  const c=Array.from(name||"（タイトルなし）");
  return c.length>limit?c.slice(0,limit-1).join("")+"…":c.join("");
}
// Render the black wallpaper; iOS supplies the clock independently.
rect(0,0,1000,2160,STYLE.bg);
// Keep the upper 25% entirely free for the native iPhone clock.
const top=570;
rect(76,top,42,4,STYLE.accent);
const daysOfWeek=["日","月","火","水","木","金","土"];
text((now.getMonth()+1)+"月"+now.getDate()+"日",
  76,top+44,690,110,78,STYLE.white,true);
text(daysOfWeek[now.getDay()]+"曜日",
  78,top+163,500,64,38,STYLE.gray);
line(76,top+255,848);
text(now.getFullYear()+" / "+String(now.getMonth()+1).padStart(2,"0"),
  76,top+305,640,66,39,STYLE.white,true);
const monthStart=new Date(now.getFullYear(),now.getMonth(),1);
const offset=(monthStart.getDay()+6)%7;
const countDays=new Date(now.getFullYear(),now.getMonth()+1,0).getDate();
const dayNames=["月","火","水","木","金","土","日"];
for(let col=0;col<7;col++){
  text(dayNames[col],98+col*125,top+412,75,44,27,STYLE.gray);
}
for(let day=1;day<=countDays;day++){
  const index=offset+day-1;
  const col=index%7,row=Math.floor(index/7);
  const x=98+col*125,y=top+477+row*64;
  if(day===now.getDate()) rounded(x-17,y-7,72,55,15,STYLE.accent);
  text(day,x,y,68,44,31,
       day===now.getDate()?STYLE.bg:STYLE.white,
       day===now.getDate());
}
// The separate subdued charcoal schedule card contains only today/tomorrow.
const cardY=1518,cardH=500;
rounded(48,cardY,904,cardH,36,STYLE.panel,STYLE.panelOpacity);
text("TODAY / TOMORROW",89,cardY+40,720,55,30,STYLE.accent,true);
line(90,cardY+112,820,STYLE.gray,.28);
const visible=events.slice(0,STYLE.displayedEvents);
if(visible.length===0){
  text("今日・明日の予定はありません",
       90,cardY+161,800,65,32,STYLE.white);
}
for(let i=0;i<visible.length;i++){
  const e=visible[i],y=cardY+143+i*83;
  // Multi-day events show the portion that falls within this two-day window.
  const labelDay=e.startDate<tomorrow?"今日":"明日";
  text(labelDay,90,y+5,103,44,27,STYLE.accent,true);
  text(timeLabel(e),200,y+5,145,44,27,STYLE.gray);
  text(shorten(e.title),355,y,545,54,31,STYLE.white);
  if(i<visible.length-1) line(90,y+68,820,STYLE.gray,.15);
}
const image=ctx.getImage();
// Preserve the established location used by the existing Shortcuts flow.
const fm=FileManager.iCloud();
const folder=fm.joinPath(fm.documentsDirectory(),"LockCalendar");
if(!fm.fileExists(folder))fm.createDirectory(folder,true);
const output=fm.joinPath(folder,"LockCalendar.png");
fm.writeImage(output,image);
// Launcher receives this return value; it handles Script.setShortcutOutput.
if(config.runsInApp && args.shortcutParameter!=="auto"){
  await QuickLook.present(image);
}
return output;
