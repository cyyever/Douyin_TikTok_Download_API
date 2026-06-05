# 变更回归测试：覆盖本次现代化改动的各个面
# 用法: .venv314/bin/python test_changes.py
import asyncio
import importlib
import traceback

PASS, FAIL = "[PASS]", "[FAIL]"
results = []


def check(name, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"{PASS if ok else FAIL} {name}" + (f" — {detail}" if detail else ""))
    return ok


# ---------------------------------------------------------------------------
# 1. 模块导入：执行各平台类体（含 TokenManager 的 proxy 归一化、模型定义）
# ---------------------------------------------------------------------------
def test_imports():
    mods = [
        "crawlers.base_crawler",
        "crawlers.douyin.web.web_crawler",
        "crawlers.douyin.web.utils",
        "crawlers.douyin.web.models",
        "crawlers.tiktok.web.web_crawler",
        "crawlers.tiktok.web.utils",
        "crawlers.bilibili.web.web_crawler",
        "crawlers.utils.utils",
    ]
    for m in mods:
        try:
            importlib.import_module(m)
            check(f"import {m}", True)
        except Exception as e:
            check(f"import {m}", False, f"{type(e).__name__}: {e}")
            traceback.print_exc()


# ---------------------------------------------------------------------------
# 2. proxy 归一化（httpx 0.28 兼容改动）
# ---------------------------------------------------------------------------
def test_proxy_normalization():
    from crawlers.base_crawler import BaseCrawler

    cases = [
        (None, None, "None 透传"),
        ({"http://": None, "https://": None}, None, "空 dict → None"),
        ({"http://": "http://p:1", "https://": None}, "http://p:1", "取 http"),
        ({"http://": None, "https://": "http://p:2"}, "http://p:2", "回退 https"),
    ]
    for proxies, expected, desc in cases:
        c = BaseCrawler(proxies=proxies)
        check(f"proxy 归一化：{desc}", c.proxy == expected, f"得到 {c.proxy!r}")

    # TokenManager.proxy 是单值（非旧 dict），且 .proxies 已不存在
    from crawlers.douyin.web.utils import TokenManager
    check("douyin TokenManager.proxy 为单值/None",
          not isinstance(TokenManager.proxy, dict))
    check("douyin TokenManager 旧 .proxies 已移除",
          not hasattr(TokenManager, "proxies"))


# ---------------------------------------------------------------------------
# 3. match-case 状态码分发（base_crawler.handle_http_status_error）
# ---------------------------------------------------------------------------
def test_match_status_dispatch():
    import httpx
    from crawlers.base_crawler import BaseCrawler
    from crawlers.utils.api_exceptions import (
        APINotFoundError, APIUnavailableError, APITimeoutError,
        APIUnauthorizedError, APIRateLimitError, APIResponseError,
    )

    bc = BaseCrawler()

    def make_err(code):
        req = httpx.Request("GET", "https://x")
        resp = httpx.Response(code, request=req)
        return httpx.HTTPStatusError("e", request=req, response=resp)

    expect = {
        404: APINotFoundError, 503: APIUnavailableError, 408: APITimeoutError,
        401: APIUnauthorizedError, 429: APIRateLimitError, 500: APIResponseError,
    }
    for code, exc in expect.items():
        try:
            bc.handle_http_status_error(make_err(code), "https://x", 1)
            check(f"status {code} → {exc.__name__}", False, "未抛异常")
        except exc:
            check(f"status {code} → {exc.__name__}", True)
        except Exception as e:
            check(f"status {code} → {exc.__name__}", False, f"抛了 {type(e).__name__}")

    # 302 不抛异常
    try:
        bc.handle_http_status_error(make_err(302), "https://x", 1)
        check("status 302 → 不抛异常", True)
    except Exception as e:
        check("status 302 → 不抛异常", False, f"抛了 {type(e).__name__}")


# ---------------------------------------------------------------------------
# 4. 抖音真实接口：视频详情 / 评论 / 评论回复 / 翻页（model_dump + a_bogus 路径）
# ---------------------------------------------------------------------------
async def test_douyin_live():
    from crawlers.douyin.web.web_crawler import DouyinWebCrawler
    c = DouyinWebCrawler()
    aweme_id = "7334525738793618688"

    # 4a. 视频详情
    try:
        d = await c.fetch_one_video(aweme_id)
        detail = (d or {}).get("aweme_detail") or {}
        check("douyin 视频详情 fetch_one_video", bool(detail.get("aweme_id")),
              f"desc={str(detail.get('desc',''))[:20]!r}")
    except Exception as e:
        check("douyin 视频详情 fetch_one_video", False, f"{type(e).__name__}: {e}")

    # 4b. 评论第一页
    cid_for_reply = None
    item_for_reply = None
    try:
        r = await c.fetch_video_comments(aweme_id, cursor=0, count=20)
        comments = r.get("comments") or []
        check("douyin 评论第一页", len(comments) > 0, f"{len(comments)} 条")
        for cm in comments:
            if (cm.get("reply_comment_total") or 0) > 0:
                cid_for_reply = cm.get("cid")
                item_for_reply = cm.get("aweme_id") or aweme_id
                break
    except Exception as e:
        check("douyin 评论第一页", False, f"{type(e).__name__}: {e}")

    # 4c. 翻页（cursor 推进，应拿到不同评论）
    try:
        r1 = await c.fetch_video_comments(aweme_id, cursor=0, count=10)
        cur = r1.get("cursor")
        r2 = await c.fetch_video_comments(aweme_id, cursor=cur, count=10)
        ids1 = {x.get("cid") for x in (r1.get("comments") or [])}
        ids2 = {x.get("cid") for x in (r2.get("comments") or [])}
        check("douyin 评论翻页（第二页不同于第一页）",
              bool(ids2) and ids1 != ids2, f"cursor={cur}, 交集 {len(ids1 & ids2)}")
    except Exception as e:
        check("douyin 评论翻页", False, f"{type(e).__name__}: {e}")

    # 4d. 评论回复
    if cid_for_reply:
        try:
            rr = await c.fetch_video_comments_reply(item_for_reply, cid_for_reply, cursor=0, count=10)
            replies = rr.get("comments") or []
            check("douyin 评论回复 fetch_video_comments_reply", len(replies) > 0,
                  f"{len(replies)} 条")
        except Exception as e:
            check("douyin 评论回复", False, f"{type(e).__name__}: {e}")
    else:
        check("douyin 评论回复（跳过，无可回复评论）", True)


def main():
    print("=" * 60)
    print("1) 模块导入")
    test_imports()
    print("2) proxy 归一化（httpx 0.28 兼容）")
    test_proxy_normalization()
    print("3) match-case 状态码分发")
    test_match_status_dispatch()
    print("4) 抖音真实接口")
    asyncio.run(test_douyin_live())
    print("=" * 60)
    total, ok = len(results), sum(results)
    print(f"结果: {ok}/{total} 通过")
    raise SystemExit(0 if ok == total else 1)


if __name__ == "__main__":
    main()
