// Lock Calendar Launcher - paste into Scriptable ONCE.
// Automatically fetches current code from your own GitHub repository.
// Nothing is uploaded; iCloud calendar access stays on the iPhone.
const SOURCE = "https://raw.githubusercontent.com/youxiangzuomu75-art/iCloudDesktopWidget/main/iphone/iCloud_LockCalendar.js";
const fm = FileManager.local();
const directory = fm.joinPath(fm.documentsDirectory(), "LockCalendar");
if (!fm.fileExists(directory)) fm.createDirectory(directory, true);
const cachedFile = fm.joinPath(directory, "cached_app.js");
let source = null;
try {
  const req = new Request(SOURCE);
  req.timeoutInterval = 15;
  const downloaded = await req.loadString();
  if (!downloaded.startsWith("// iCloud Lock Calendar for Scriptable") || downloaded.length < 4000 || downloaded.length > 250000) {
    throw Error("Unexpected update file");
  }
  source = downloaded;
  fm.writeString(cachedFile, source);
} catch (err) {
  if (fm.fileExists(cachedFile)) {
    source = fm.readString(cachedFile);
    if (config.runsInApp) console.warn("Offline: using last downloaded version. " + err);
  } else {
    const a = new Alert();
    a.title = "更新を取得できません";
    a.message = "インターネット接続を確認してください。\n" + err;
    a.addAction("OK");
    await a.presentAlert();
    source = null;
  }
}
// Execute the code as an async function, so Scriptable's calendar awaits work.
if (source) {
  const wallpaperFile = await eval("(async () => {\n" + source + "\n})()");
  if (!wallpaperFile || !String(wallpaperFile).endsWith(".png")) {
    throw new Error("カレンダー画像の生成結果を受け取れませんでした。");
  }
  // MUST be called in this top-level script, not in the dynamically loaded module.
  Script.setShortcutOutput(wallpaperFile);
}
Script.complete();
