# 🗓️ 我的自动签到工具（云端版）

一套**免费、不用开电脑**的自动签到工具：任务跑在 GitHub 的免费云端（GitHub Actions），
每天自动帮你在 **什么值得买** 和 **吾爱破解** 签到；你用手机或电脑打开一个网页，
就能看到签到结果、连签天数和历史记录。

> ⚠️ **请先读这段**
> - 自动签到可能违反部分平台的服务条款，**账号风险请自行承担**，建议只签自己的号、每天只签一次。
> - 你的登录凭证（cookie）只保存在**你自己私有仓库的 Secrets** 里，不会写进代码，也不会出现在网页上。
> - 淘宝 / 拼多多 / 京东 / Kuyo 这类平台**无法用本方案**（原因见文末“关于购物平台”）。

---

## 这套东西由哪几部分组成？

| 文件 | 作用（大白话） |
|---|---|
| `checkin.py` | 真正干活的签到脚本，每天被云端叫醒去签到 |
| `.github/workflows/checkin.yml` | “闹钟 + 流水线”，规定每天几点跑、跑完把结果存下来 |
| `data/status.json` | 签到结果记录本，网页控制台读它来显示 |
| `index.html` | 你手机/电脑打开的**签到控制台网页** |
| `requirements.txt` | 告诉云端需要装哪个工具包 |

---

## 部署步骤（照着做，约 20 分钟）

### 第 0 步：注册一个 GitHub 账号
打开 https://github.com 注册（免费）。已有账号就跳过。

### 第 1 步：新建一个仓库，把这些文件传上去
1. 登录后点右上角 **＋ → New repository**。
2. Repository name 随便起，比如 `auto-checkin`。
3. **一定选 `Private`（私有）** —— 因为里面会用到你的签到信息，私有更安全。
4. 点 **Create repository**。
5. 在新仓库页面点 **uploading an existing file**（或 Add file → Upload files）。
6. 把我给你的 **整个 `auto-checkin` 文件夹里的所有内容**（包括 `.github`、`data` 这些子文件夹）
   **一起拖进上传框**。GitHub 会自动保留文件夹结构。
7. 拉到底点 **Commit changes**。

> 💡 拖拽时请确保 `.github` 文件夹也被拖进去了（它是隐藏文件夹，以点开头）。
> 上传完成后，仓库里应该能看到 `checkin.py`、`index.html`、`data/`、`.github/` 这些。

### 第 2 步：获取你的“签到凭证”（cookie）
cookie 就像一张“已登录的门禁卡”，脚本靠它冒充你去签到。**两个网站各弄一次**：

**什么值得买：**
1. 电脑浏览器打开 https://zhiyou.smzdm.com/ 并**登录**你的账号。
2. 按键盘 **F12**（或右键 → 检查），打开开发者工具。
3. 点顶部的 **Network（网络）** 标签 → 然后按 **F5 刷新页面**。
4. 在左边请求列表点**第一个**（一般叫 `zhiyou.smzdm.com` 或 `checkin`）。
5. 右边找到 **Request Headers（请求标头）** → 找到 **`Cookie:`** 那一行 →
   **把 `Cookie:` 后面的一整串文字全部复制**（很长，别漏）。

**吾爱破解：**
1. 电脑浏览器打开 https://www.52pojie.cn/ 并**登录**。
2. 同样按 F12 → Network → 刷新 → 点第一个请求 → 复制 `Cookie:` 后面一整串。

### 第 3 步：把 cookie 存进仓库的“保险箱”（Secrets）
1. 回到你的 GitHub 仓库页面，点顶部 **Settings（设置）**。
2. 左侧最下面 **Secrets and variables → Actions**。
3. 点 **New repository secret**，添加下面两条（名字必须一模一样，注意大小写）：

   | Name（名字） | Secret（值，粘贴你复制的 cookie） |
   |---|---|
   | `SMZDM_COOKIE` | 什么值得买那一整串 cookie |
   | `POJIE_COOKIE` | 吾爱破解那一整串 cookie |

4.（可选）想每天把结果推送到手机，可再加一条：
   - `BARK_KEY`：iOS 用 Bark App 的 key（https://bark.day.app ）
   - `SCT_SENDKEY`：微信用 Server 酱的 SendKey（https://sct.ftqq.com ）
   - `PUSHPLUS_TOKEN`：微信用 PushPlus 的 token（https://www.pushplus.plus ）

   > 不配也能正常签到，只是不会主动推送通知。默认只在**签到出问题时**才推送，不打扰你。

### 第 4 步：打开 Actions 开关，手动跑一次
1. 点仓库顶部的 **Actions** 标签。
2. 如果看到一句提示要你启用，点 **I understand my workflows, go ahead and enable them**。
3. 左边点 **自动签到** → 右边点 **Run workflow → Run workflow**（绿色按钮）。
4. 等 1~2 分钟，刷新页面。出现 ✅ 绿色对勾就成功了。
   点进去能看到每个平台的签到结果文字。

### 第 5 步：开启网页控制台（GitHub Pages）
1. 仓库 **Settings → 左侧 Pages**。
2. “Build and deployment” 里，Source 选 **Deploy from a branch**，
   Branch 选 **`main`**、文件夹选 **`/ (root)`**，点 **Save**。
3. 等 1~2 分钟后刷新这个页面，顶部会出现一行网址：
   `https://你的用户名.github.io/auto-checkin/`
4. **用这个网址在手机浏览器打开，就是你的签到控制台**。
   （可以“添加到主屏幕”，以后像 App 一样点开。）

> ⚠️ 注意：私有仓库开 GitHub Pages 需要 GitHub Pro（付费）。
> 如果你不想付费，有两个免费办法：
> - **办法 A（推荐）**：把仓库改成 **Public（公开）**。因为 cookie 只存在 Secrets 里、
>   `data/status.json` 里也没有任何敏感信息，公开是安全的。改法：Settings → 最下面 Danger Zone → Change visibility → Public。
> - **办法 B**：不开网页，只靠 Actions 每天跑 + 手机推送通知看结果（第 3 步配一个推送 key 即可）。

---

## 完成后，日常怎么用？
- **平时什么都不用做**，云端每天早上 08:10 自动签，晚上 22:00 再检查一次（早上漏了就补）。
- 想看结果 → 手机打开第 5 步的网址。
- 想立刻签一次 → 控制台点“立即签到”按钮，或去 Actions 点 Run workflow。

---

## 常见问题

**Q：过一段时间签到失败了 / 显示“凭证失效”？**
cookie 会过期（什么值得买大约几个月，吾爱破解更久）。解决办法：重复**第 2 步**重新复制一次 cookie，
再到**第 3 步**把对应的 Secret 更新成新值即可，不用改代码。

**Q：定时会不会不准？**
GitHub 的定时器在高峰期可能延迟几分钟到几十分钟，属正常现象。所以脚本设了**早晚两次**，
并且**幂等**（已签到就跳过），基本不会漏签。

**Q：会不会跑一段时间就自己停了？**
GitHub 规定仓库 60 天没有任何动静会自动停用定时任务。本工具**每次签到都会更新结果文件并留下记录**，
所以只要每天在签，就不会被停。若你长期没签（比如 cookie 失效没管），记得偶尔手动跑一次。

**Q：怎么再加一个新网站？**
在 `checkin.py` 里照抄一个平台的函数、在 `PLATFORMS` 和 `CHECKIN_FUNCS` 里登记，
再到 Secrets 加对应的 cookie 即可。也可以直接叫我帮你加。

---

## 关于购物平台（淘宝 / 拼多多 / 京东）和 Kuyo
这几个**用不了本方案**，不是偷懒，是技术限制：
- 它们**没有网页签到入口**，只能在手机 App 里签；
- 它们的接口需要 App 级别的加密签名 / 设备指纹 / 验证码风控，云端“裸请求”会被秒拦；
- 京东风控极严容易封号，且此类脚本有法律纠纷历史；拼多多风控最狠，异常会导致提现冻结。

要做它们，唯一的现实路径是**在安卓手机上装“模拟点击”工具**（AutoJs6 / Hamibot），
让手机自己每天点屏幕签到 —— 那是另一套方案（需要一台安卓机常开、要额外授权、同样有封号风险）。
如果你需要，可以让我单独给你出一份手机端模拟点击的教程。
