# face_bot — 自动"拍照认证"喂图工具

监控屏幕,检测 H5 网页弹出的"拍照识别"窗口,自动点击拍照按钮并上传本地照片。

## 原理

- **模板匹配**定位屏幕上的弹窗头部和拍照按钮(无需 OCR)
- **WinAPI** 直接操控鼠标,在文件对话框中双击照片完成上传
- 纯本地运行,不上传任何数据

## 文件结构

```
├── face_bot.py          # 主程序源码
├── build.bat            # PyInstaller 打包脚本
├── templates/           # 屏幕识别模板(必填)
│   ├── popup_header.png     # 弹窗头部截图
│   ├── capture_button.png   # "拍照"按钮截图
│   └── file_thumb_name.png  # 文件框缩略图(自动生成)
├── faces/               # 放人脸照片(1-5 张,文件名随意)
└── logs/                # 运行日志(自动生成)
```

## 快速开始

### 1. 准备模板图

在微信内置浏览器中打开目标 H5 页面,等待"请确认由本人亲自操作"弹窗:

- **第 1 张**: 用 Win+Shift+S 框选弹窗头部人像 → 存为 `templates/popup_header.png`
- **第 2 张**: 滚到底部,框选红色"拍照"按钮 → 存为 `templates/capture_button.png`

### 2. 放照片

把 1-5 张正脸照片复制到 `faces/` 文件夹,文件名随意(如 `me.jpg`)。

### 3. 运行

```bash
pip install pyautogui Pillow
python face_bot.py
```

或使用打包好的 `face_bot.exe`(Release 页面下载),双击即可,无需装 Python。

**中止**: 鼠标移到屏幕左上角 或 `Ctrl+C`

## 给朋友用

把发布包(zip)发给朋友,他只需要:
1. 放自己的人脸照片到 `faces/`
2. 双击 `face_bot.exe`

模板图已包含在发布包内,无需重新截图。

## 构建

```bash
pip install pyinstaller pyautogui Pillow
python -m PyInstaller --noconfirm --onefile --name face_bot --add-data "templates;templates" --add-data "faces;faces" face_bot.py
```

输出在 `dist/face_bot.exe`

## 常见问题

### 双击 exe 没反应 / 报错"找不到 VCRUNTIME140.dll"

安装 Visual C++ Redistributable:

```
https://aka.ms/vs/17/release/vc_redist.x64.exe
```

大部分 Win10/11 已自带,少数精简版系统需要手动装。

### 弹窗出现了但脚本没反应

可能是模板图不适配当前屏幕分辨率。重新在自己电脑上截图替换 `templates/` 里的两个文件即可。

### 文件对话框里没双击到照片

看 `logs/` 里最新的 `file_dialog_match_*.png` 截图,检查脚本认为的双击位置是否在照片上。如果偏移超过 50px,联系开发者调整。

## 限制

- Windows 10/11 专用
- 不涉及活体检测(仅适用于只传静态图片的认证流程)
- UI 变动后需要重新截模板图
