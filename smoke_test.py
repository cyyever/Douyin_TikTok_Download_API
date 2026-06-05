# Smoke test: 验证抖音评论抓取链路是否可用（签名生成 + 接口请求 + 字段解析）
# 用法: .venv/bin/python smoke_test.py [aweme_id]
import asyncio
import sys

from crawlers.douyin.web.web_crawler import DouyinWebCrawler


async def main():
    aweme_id = sys.argv[1] if len(sys.argv) > 1 else "7334525738793618688"
    crawler = DouyinWebCrawler()

    print(f"[*] 测试视频评论抓取 aweme_id={aweme_id}")
    try:
        resp = await crawler.fetch_video_comments(aweme_id, cursor=0, count=20)
    except Exception as e:
        print(f"[FAIL] 请求异常: {type(e).__name__}: {e}")
        return

    status = resp.get("status_code")
    comments = resp.get("comments") or []
    total = resp.get("total")
    print(f"[*] status_code={status}  total={total}  本页评论数={len(comments)}")

    if not comments:
        print("[WARN] 无评论返回 —— 多半是 cookie 过期/失效或视频无评论。原始响应前 500 字:")
        print(str(resp)[:500])
        return

    print("[OK] 成功抓到评论，前 3 条样例（验证字段可得性）:")
    for c in comments[:3]:
        print("  -", {
            "cid": c.get("cid"),
            "text": (c.get("text") or "")[:40],
            "digg_count": c.get("digg_count"),
            "reply_comment_total": c.get("reply_comment_total"),
            "create_time": c.get("create_time"),
        })


if __name__ == "__main__":
    asyncio.run(main())
