# 番茄上班鼓励器

> 上班拒绝内耗 - 无所吊谓

一个跨平台桌面小工具，实时显示你"今天已经赚了多少钱"，每秒跳字，治愈上班痛苦。

## 功能

- 设置上班时间、下班时间、日薪 → 一键开工
- 工作中实时显示已赚金额（每秒刷新，4 位小数）
- 下班结算弹窗，告诉你今天"怒赚"多少
- 提前下班确认框（良心拷问）
- 置顶模式 / 三套主题色 / 自定义 slogan / 历史记录
- 月薪→日薪换算器（输入月薪，自动按 21.75 天算）

## 直接运行（需要 Python 3）

```bash
# Windows
py 番茄上班鼓励器.py

# macOS / Linux
python3 番茄上班鼓励器.py
```

零第三方依赖，tkinter 是 Python 标准库自带的。

## 打包为可执行文件

### 本地打包

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "番茄上班鼓励器" 番茄上班鼓励器.py
```

产物在 `dist/` 目录：Windows 得到 .exe，macOS 得到 .app。

> 注意：PyInstaller 不支持交叉编译。在 Windows 上只能打 exe，在 Mac 上只能打 .app。

### GitHub Actions 自动构建（无需本地有 Mac）

1. 将本目录推送到 GitHub 仓库
2. 等待 Actions 自动运行（push 到 main 分支触发）
3. 在 Actions 页面下载 Artifacts：
   - `番茄上班鼓励器-Windows` → .exe
   - `番茄上班鼓励器-macOS` → .app
4. 打 tag（如 `v1.0.0`）推送后会自动创建 GitHub Release 并附带安装包

手动触发：仓库页面 → Actions → Build Desktop App → Run workflow

## macOS 首次运行提示

由于没有 Apple 开发者签名，首次打开可能提示"无法验证开发者"。解决方式：

- 右键 .app → 打开 → 确认打开（只需一次）
- 或 系统设置 → 隐私与安全性 → 点击"仍要打开"

## 数据存储

程序运行后会在用户主目录生成 `~/.tomato_encourager/` 存放配置和历史记录。删除该目录即恢复出厂设置。
