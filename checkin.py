#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多平台自动签到脚本
==================
运行环境：GitHub Actions（云端自带 Python 3.11）
支持平台：什么值得买(smzdm)、吾爱破解(52pojie)
设计原则：
  1. 幂等 —— 今天已经签到成功的平台，第二次运行会自动跳过，不重复请求（降低风控）
  2. 容错 —— 一个平台出错不影响其它平台
  3. 结果落地 —— 每次签到结果写进 data/status.json，由网页控制台读取展示
  4. 通知可选 —— 配了推送 key 才推送，没配也不报错

凭据（cookie）从环境变量读取，环境变量由 GitHub Secrets 注入，永远不进代码、不进仓库。
"""

import os
import re
import json
import datetime
import traceback

try:
    import requests
except ImportError:  # 本地没装 requests 时给个友好提示
    requests = None

# ---------------------------------------------------------------------------
# 基础配置
# ---------------------------------------------------------------------------

# 北京时间（GitHub Actions 默认是 UTC，必须显式指定，否则日期会错一天）
try:
    from zoneinfo import ZoneInfo
    BJT = ZoneInfo("Asia/Shanghai")
except Exception:  # 极端兜底
    BJT = datetime.timezone(datetime.timedelta(hours=8))

NOW = datetime.datetime.now(BJT)
TODAY = NOW.date().isoformat()          # 例如 2026-09-16
NOW_HM = NOW.strftime("%H:%M")          # 例如 08:10

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
STATUS_FILE = os.path.join(DATA_DIR, "status.json")

# 伪装成正常浏览器，降低被识别为脚本的概率
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

# 平台清单：key = 环境变量前缀 / 展示名
PLATFORMS = {
    "smzdm":   "什么值得买",
    "52pojie": "吾爱破解",
}


# ---------------------------------------------------------------------------
# 状态文件读写
# ---------------------------------------------------------------------------

def load_status():
    """读取历史记录文件，不存在或损坏就返回空结构。"""
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "history" in data:
                    return data
        except Exception:
            pass
    return {"updated_at": None, "platforms": list(PLATFORMS.keys()), "history": {}}


def save_status(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    data["updated_at"] = NOW.isoformat(timespec="seconds")
    data["platforms"] = list(PLATFORMS.keys())
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def already_done_today(history, platform):
    """判断某平台今天是否已经签到成功/已签到，用于幂等跳过。"""
    rec = history.get(TODAY, {}).get(platform)
    return bool(rec) and rec.get("status") in ("success", "duplicate")


# ---------------------------------------------------------------------------
# 平台一：什么值得买
# ---------------------------------------------------------------------------

def checkin_smzdm(cookie):
    """什么值得买：2026 年现行接口为 jsonp_checkin（GET），旧 ajax_checkin 已 404。"""
    if not cookie:
        return {"status": "not_configured", "message": "未配置 SMZDM_COOKIE"}
    url = "https://zhiyou.smzdm.com/user/checkin/jsonp_checkin"
    headers = {
        # 用 iPhone 版 UA + 主站 Referer，与现行开源脚本一致
        "User-Agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) "
                       "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 "
                       "Mobile/15E148 Safari/604.1"),
        "Host": "zhiyou.smzdm.com",
        "Referer": "https://www.smzdm.com/",
        "Accept": "*/*",
        "Cookie": cookie,
    }
    try:
        r = requests.get(url, headers=headers, timeout=25)
    except Exception as e:
        return {"status": "failed", "message": "网络请求异常：%s" % e}

    text = (r.text or "").strip()
    # 可能被 JSONP 回调包裹：jQueryxxx({...}) → 取出括号内 JSON
    if not text.startswith("{"):
        m = re.search(r"\((.*)\)\s*;?\s*$", text, re.S)
        if m:
            text = m.group(1)
    try:
        j = json.loads(text)
    except Exception:
        return {"status": "failed",
                "message": "返回异常(HTTP %s)，可能被风控或 cookie 失效" % r.status_code}

    code = j.get("error_code")
    msg = str(j.get("error_msg", ""))
    if code == 0:
        data = j.get("data") or {}
        days = data.get("continue_checkin_days") or data.get("checkin_num")
        extra = ("，连签 %s 天" % days) if days else ""
        if "已" in msg and "签" in msg:
            return {"status": "duplicate", "message": (msg or "今日已签到") + extra}
        return {"status": "success", "message": (msg or "签到成功") + extra}
    if code == -1:
        return {"status": "failed", "message": "网络繁忙(error_code=-1)，可稍后重试"}
    if "登录" in msg:
        return {"status": "expired", "message": "cookie 可能已失效：%s" % msg}
    if "已" in msg and "签" in msg:
        return {"status": "duplicate", "message": msg or "今日已签到"}
    return {"status": "failed", "message": msg or ("返回码 %s" % code)}


# ---------------------------------------------------------------------------
# 平台二：吾爱破解
# ---------------------------------------------------------------------------

# 全套真实浏览器指纹头：吾爱 2025-2026 上了"安域防护"WAF，头不全极易被拦
POJIE_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,image/apng,*/*;q=0.8"),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def _decode_pojie(resp):
    """Discuz 页面是 gbk，WAF 挑战页是 utf-8，按实际 charset 解码。"""
    head = resp.content[:2000].lower()
    resp.encoding = "gbk" if b"charset=gbk" in head else "utf-8"
    return resp.text or ""


def _pojie_waf_blocked(text):
    """识别'安域防护'JS 挑战页（utf-8 空壳 / 含挑战变量）。"""
    if "安域防护" in text:
        return True
    if "LZ='" in text or "LJ='" in text or "waf_zw_verify" in text:
        return True
    low = text.strip().lower()
    return (low.startswith("<!doctype html") and "messagetext" not in text
            and len(text) < 2000)


def checkin_52pojie(cookie):
    if not cookie:
        return {"status": "not_configured", "message": "未配置 POJIE_COOKIE"}
    s = requests.Session()
    s.headers.update(POJIE_HEADERS)
    s.headers["Cookie"] = cookie

    home = "https://www.52pojie.cn/"
    apply_url = "https://www.52pojie.cn/home.php?mod=task&do=apply&id=2&referer=%2F"
    draw_url = "https://www.52pojie.cn/home.php?mod=task&do=draw&id=2"

    def get(url, referer):
        h = dict(s.headers)
        h["Referer"] = referer
        return s.get(url, headers=h, timeout=25)

    try:
        get(home, home)                      # 先访问首页建立会话
        r_apply = get(apply_url, home)       # 领取任务
        t_apply = _decode_pojie(r_apply)
        if _pojie_waf_blocked(t_apply):
            return {"status": "failed",
                    "message": "被吾爱'安域防护'JS 盾拦截（云端 IP 触发），本次未签到"}
        r_draw = get(draw_url, apply_url)    # 真正签到
    except Exception as e:
        return {"status": "failed", "message": "网络请求异常：%s" % e}

    text = _decode_pojie(r_draw)
    if _pojie_waf_blocked(text):
        return {"status": "failed",
                "message": "被吾爱'安域防护'JS 盾拦截（云端 IP 触发），本次未签到"}
    if "您需要先登录" in text or "请先登录" in text:
        return {"status": "expired", "message": "cookie 可能已失效，请重新登录获取"}
    if "恭喜" in text or "签到成功" in text or "领取成功" in text:
        return {"status": "success", "message": "签到成功"}
    if ("不是进行中的任务" in text or "已完成" in text or "已经签到" in text
            or "已签到" in text or "已领取" in text):
        return {"status": "duplicate", "message": "今日已签到"}
    snippet = "".join(ch for ch in text if ch.isprintable())[:60]
    return {"status": "failed", "message": "未识别到签到结果：%s" % (snippet or "空响应")}


CHECKIN_FUNCS = {
    "smzdm":   (checkin_smzdm,   "SMZDM_COOKIE"),
    "52pojie": (checkin_52pojie, "POJIE_COOKIE"),
}


# ---------------------------------------------------------------------------
# 通知推送（全部可选）
# ---------------------------------------------------------------------------

def notify(title, content):
    """把签到结果推送到手机。配了哪个 key 就推哪个，都没配就静默跳过。"""
    if requests is None:
        return
    content = content or title

    # Bark（iOS 好用）
    bark = os.environ.get("BARK_KEY", "").strip()
    if bark:
        try:
            requests.get("https://api.day.app/%s/%s/%s" % (bark, title, content), timeout=15)
        except Exception:
            pass

    # Server 酱（推送到微信）
    sct = os.environ.get("SCT_SENDKEY", "").strip()
    if sct:
        try:
            requests.post("https://sctapi.ftqq.com/%s.send" % sct,
                          data={"title": title, "desp": content}, timeout=15)
        except Exception:
            pass

    # PushPlus（推送到微信）
    pp = os.environ.get("PUSHPLUS_TOKEN", "").strip()
    if pp:
        try:
            requests.post("http://www.pushplus.plus/send",
                          json={"token": pp, "title": title,
                                "content": content.replace("\n", "<br>")},
                          timeout=15)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    if requests is None:
        print("[错误] 没有安装 requests 库，请先执行 pip install -r requirements.txt")
        return

    status = load_status()
    history = status.setdefault("history", {})
    today_rec = history.setdefault(TODAY, {})

    lines = []
    for key, name in PLATFORMS.items():
        func, env_name = CHECKIN_FUNCS[key]

        # 幂等：今天已成功就跳过，不重复请求
        if already_done_today(history, key):
            prev = today_rec.get(key, {})
            result = {"status": prev.get("status", "success"),
                      "message": prev.get("message", "今日已签到（跳过重复请求）"),
                      "skipped": True}
        else:
            cookie = os.environ.get(env_name, "").strip()
            try:
                result = func(cookie)
            except Exception as e:
                result = {"status": "failed", "message": "脚本异常：%s" % e}
                traceback.print_exc()

        result["time"] = NOW_HM
        today_rec[key] = result

        icon = {"success": "✅", "duplicate": "🟢", "expired": "🔑",
                "not_configured": "⚪", "failed": "❌"}.get(result["status"], "❓")
        line = "%s %s：%s" % (icon, name, result["message"])
        lines.append(line)
        print(line)

    # 计算连签天数
    streaks = {k: compute_streak(history, k) for k in PLATFORMS}
    for k, name in PLATFORMS.items():
        if streaks[k] > 0:
            print("   └ %s 已连签 %d 天" % (name, streaks[k]))

    save_status(status)

    # 只在有“需要关注”的情况时才推送，避免每天打扰
    need_alert = any(today_rec[k]["status"] in ("failed", "expired")
                     for k in PLATFORMS
                     if today_rec[k]["status"] != "not_configured")
    summary = "\n".join(lines)
    if need_alert:
        notify("⚠️ 自动签到有异常", summary)
    elif os.environ.get("NOTIFY_ON_SUCCESS", "").strip().lower() in ("1", "true", "yes"):
        notify("✅ 今日自动签到完成", summary)

    print("\n[完成] 结果已写入 data/status.json")


def compute_streak(history, platform):
    """从今天（或昨天）往前数，连续签到成功/已签到的天数。"""
    streak = 0
    day = NOW.date()
    # 如果今天还没记录，从昨天开始数（比如凌晨运行）
    if platform not in history.get(TODAY, {}):
        day = day - datetime.timedelta(days=1)
    for _ in range(3650):
        rec = history.get(day.isoformat(), {}).get(platform)
        if rec and rec.get("status") in ("success", "duplicate"):
            streak += 1
            day = day - datetime.timedelta(days=1)
        else:
            break
    return streak


if __name__ == "__main__":
    main()
