import asyncio
from datetime import datetime, timedelta, timezone

from loguru import logger

from api import apis
from common.config import config
from crawlers.modules.base_crawler import BaseCrawler
from request.hooks.use_request import use_request

_TZ = timezone(timedelta(hours=8))


class GiteeCrawler(BaseCrawler):
    CRAWLER_NAME = "gitee"

    def __init__(self):
        super().__init__()
        self.gitee_api = use_request(apis.repo_gitee.get_commits)
        self._api_base_url = "https://gitee.com/api/v5"

    def get_platform_name(self) -> str:
        return "Gitee"

    def get_sources_config(self) -> list:
        return config.get("crawler_sources", {}).get("gitee", {}).get("repos", [])

    def get_api_token(self) -> str:
        return config.get("crawler_sources", {}).get("gitee", {}).get("token", "")

    async def fetch_activities(self, entity_config: dict, query_params: dict) -> list:
        owner_repo = entity_config.get("path", "")
        branch = entity_config.get("branch", "main")
        if "/" not in owner_repo:
            logger.warning(f"Gitee 仓库路径格式无效: {owner_repo}")
            return []
        owner, repo = owner_repo.split("/", 1)
        since = query_params.get("since")
        until = query_params.get("until")
        token = self.get_api_token()
        params = {"sha": branch, "since": since, "until": until, "per_page": 100}
        if token:
            params["access_token"] = token
        try:
            result = await self.gitee_api(owner=owner, repo=repo, params=params, base_url=self._api_base_url)
            if not result or not isinstance(result, list):
                return []
            if len(result) >= 100:
                logger.warning(f"Gitee [{owner_repo}] 返回{len(result)}条（达单页上限）")
            return result
        except Exception as e:
            logger.error(f"Gitee [{owner_repo}] 采集失败: {e}")
            return []

    def extract_activity_data(self, raw_data: dict) -> dict:
        commit = raw_data.get("commit", {})
        author = commit.get("author", {})
        return {"id": raw_data.get("sha", ""), "author_name": author.get("name", ""), "author_email": author.get("email", ""), "content": commit.get("message", "").split("\n")[0], "created_at": author.get("date", ""), "metadata": {"branch": raw_data.get("_branch_name", "main")}}

    async def collect_source(self, source: dict) -> str:
        owner_repo = source.get("path", "")
        branch = source.get("branch", "main")
        repo_name = source.get("name", owner_repo)
        if "/" not in owner_repo:
            return ""
        owner, repo = owner_repo.split("/", 1)
        since, until = self.get_crawl_dates()
        token = self.get_api_token()
        params = {"sha": branch, "since": since.isoformat(), "until": until.isoformat(), "per_page": 100}
        if token:
            params["access_token"] = token
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await self.gitee_api(owner=owner, repo=repo, params=params, base_url=self._api_base_url)
                if isinstance(result, list) and len(result) >= 100:
                    logger.warning(f"Gitee [{repo_name}] 返回{len(result)}条（达单页上限）")
                return self._format_commits(result, repo_name)
            except Exception as e:
                err_str = str(e).lower()
                if "rate limit" in err_str or "403" in err_str or "429" in err_str:
                    if attempt < max_retries - 1:
                        wait = 2 ** (attempt + 1)
                        logger.warning(f"Gitee API 限流，{wait}s 后重试")
                        await asyncio.sleep(wait)
                        continue
                logger.error(f"Gitee [{repo_name}] 采集失败: {e}")
                return ""
        return ""

    def get_crawl_dates(self):
        now = datetime.now(_TZ)
        return now.replace(hour=0, minute=0, second=0, microsecond=0), now.replace(hour=23, minute=59, second=59, microsecond=0)

    def _format_commits(self, commits, repo_name):
        if not commits:
            return ""
        lines = [f"仓库: {repo_name} (Gitee)", "-" * 40]
        for c in commits:
            commit = c.get("commit", {})
            author = commit.get("author", {})
            msg = commit.get("message", "").split("\n")[0]
            lines.append(f"[{author.get('name', 'unknown')}] {author.get('date', '')[:10]} - {msg}")
        return "\n".join(lines)
