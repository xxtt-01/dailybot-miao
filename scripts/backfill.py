"""
DailyBot 历史日报补数据脚本

遍历过去 N 天，采集每天 Git 提交 → AI 总结 → 存入数据库（草稿模式）
不影响已有数据，不推送飞书，可反复执行（已有日报的日期自动跳过）

用法:
    python scripts/backfill.py                  # 默认补最近 30 天
    python scripts/backfill.py --days 7         # 只补最近 7 天
    python scripts/backfill.py --force          # 强制覆盖已有日报
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_TZ = timezone(timedelta(hours=8))


def parse_args() -> tuple:
    days = 30
    force = False
    for arg in sys.argv[1:]:
        if arg.startswith("--days="):
            days = int(arg.split("=")[1])
        elif arg == "--force":
            force = True
        elif arg == "--days" and len(sys.argv) > sys.argv.index(arg) + 1:
            days = int(sys.argv[sys.argv.index(arg) + 1])
    return days, force


async def main():
    days, force = parse_args()
    print(f"📋 历史日报补数据: 最近 {days} 天{' (强制覆盖)' if force else ''}")

    # 延迟导入（避免启动时加载全部模块）
    from common.database import db
    from common.config import config
    from providers import AIFactory
    import httpx

    platform = "github"
    token = config.get(f"crawler_sources.{platform}.token", "")
    target_user = config.get(f"crawler_sources.{platform}.target_user", "")
    if not token:
        print("❌ 未配置 GitHub token，无法采集")
        return

    # 获取 AI 模型
    platform_config = config.get_platform("feishu")
    provider_key = platform_config.get("ai_model")
    if not provider_key:
        print("❌ 未配置 AI 模型")
        return

    provider_name = config.get_provider_for_model(provider_key) or provider_key
    ai = AIFactory.get_ai(provider_name, model_id=provider_key)
    if not ai:
        print(f"❌ 无法创建 AI 实例: {provider_name}")
        return

    print(f"📡 AI 模型: {provider_key}")
    print(f"📡 GitHub 用户: {target_user}")
    print()

    headers = {"Authorization": f"Bearer {token}"} if token else {}

    # 获取所有仓库
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(
            f"https://api.github.com/users/{target_user}/repos",
            params={"per_page": 100, "sort": "pushed"},
            headers=headers, timeout=15,
        )
        if resp.status_code != 200:
            print(f"❌ 获取仓库列表失败: HTTP {resp.status_code}")
            return
        repos = resp.json()
        print(f"📦 发现 {len(repos)} 个仓库")
        repo_list = []
        for r in repos:
            repo_list.append({
                "owner": r["full_name"].split("/")[0],
                "name": r["full_name"].split("/")[1],
                "branch": r.get("default_branch", "main"),
                "full_name": r["full_name"],
            })

    # 遍历天数
    today = datetime.now(_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    success_count = 0
    skip_count = 0
    empty_count = 0

    for day_offset in range(days, 0, -1):  # 从最远到最近
        target_date = today - timedelta(days=day_offset)
        date_str = target_date.strftime("%Y-%m-%d")

        # 检查是否已有日报
        existing = db.get_reports(date_str, platform="feishu", limit=1)
        if existing and not force:
            print(f"  ⏭️  {date_str} (已有日报，跳过)")
            skip_count += 1
            continue

        # 采集当天提交
        since = target_date.isoformat()
        until = (target_date + timedelta(days=1)).isoformat()

        all_commits = []
        async with httpx.AsyncClient(verify=False) as client:
            for repo in repo_list:
                try:
                    resp = await client.get(
                        f"https://api.github.com/repos/{repo['full_name']}/commits",
                        params={"sha": repo["branch"], "since": since, "until": until, "per_page": 100},
                        headers=headers, timeout=15,
                    )
                    if resp.status_code != 200:
                        continue
                    commits = resp.json()
                    if isinstance(commits, list):
                        for c in commits:
                            msg = c.get("commit", {}).get("message", "").split("\n")[0]
                            author = c.get("commit", {}).get("author", {})
                            all_commits.append({
                                "repo": repo["full_name"],
                                "message": msg,
                                "author": author.get("name", ""),
                                "date": author.get("date", ""),
                            })
                except Exception as e:
                    print(f"    ⚠️  {repo['full_name']} 采集失败: {e}")

        if not all_commits:
            print(f"  📭  {date_str} — 无提交记录")
            empty_count += 1
            continue

        # 格式化原始报告
        raw_lines = [f"\n  平台: GITHUB\n    📦 [今日真实工作]"]
        for c in all_commits:
            raw_lines.append(f"      [{c['date'][:10]}] {c['repo']}: {c['message']}")
        raw_report = "\n".join(raw_lines)

        # AI 总结
        print(f"  🤖  {date_str} — {len(all_commits)} 条提交，正在 AI 总结...", end="", flush=True)
        try:
            summary = await ai.summarize(raw_report, is_camouflage=False)
            if not summary:
                print(" ❌ AI 返回空")
                continue
            # 保存到数据库（草稿模式，不推送）
            db.save_report(
                date=date_str,
                platform="feishu",
                summary=summary,
                raw_data=raw_report,
                is_camouflage=False,
                pushed=0,
            )
            db.log_run(date=date_str, status="success", platform="feishu", message="历史数据补录")
            print(f" ✅")
            success_count += 1
        except Exception as e:
            print(f" ❌ 失败: {e}")

    # 汇总
    print()
    print("=" * 50)
    print(f"📊 补数据完成:")
    print(f"   ✅ 成功: {success_count} 天")
    print(f"   ⏭️  跳过(已有): {skip_count} 天")
    print(f"   📭 无提交: {empty_count} 天")
    print(f"   📅 总计扫描: {days} 天")
    print("=" * 50)
    print("💡 已生成的日报在桌面端「日报历史」页查看，状态为「待推送」")
    print("   如需推送到飞书，在桌面端点击推送按钮")


if __name__ == "__main__":
    asyncio.run(main())
