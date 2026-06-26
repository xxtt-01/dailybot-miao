import asyncio
import warnings
from datetime import datetime, timedelta, timezone

import httpx
from loguru import logger

from common.config import config
from crawlers.modules.base_crawler import BaseCrawler

# 关闭 httpx SSL 警告（企业代理环境）
warnings.filterwarnings("ignore", message=".*verify.*", category=UserWarning, module="httpx")

_TZ = timezone(timedelta(hours=8))


class GithubCrawler(BaseCrawler):
    CRAWLER_NAME = "github"

    def __init__(self):
        super().__init__()
        self._api_base_url = "https://api.github.com"

    def get_platform_name(self) -> str:
        return "GitHub"

    def get_sources_config(self) -> list:
        cfg = config.get("crawler_sources", {}).get("github", {})
        # 自动发现模式：只要 auto_discover=true，就动态拉取仓库列表
        if cfg.get("auto_discover") and cfg.get("target_user"):
            return [{"path": "__auto_discover__", "branch": "main"}]
        return cfg.get("repos", [])

    async def _fetch_commits(self, owner: str, repo: str, params: dict, headers: dict) -> list:
        """直接使用 httpx 调用 GitHub Commits API，HTTP 异常向上传播"""
        url = f"{self._api_base_url}/repos/{owner}/{repo}/commits"
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(url, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            return result if isinstance(result, list) else []

    async def fetch_activities(self, entity_config: dict, query_params: dict) -> list:
        # 自动发现模式：先拉取所有仓库，再采集全部 commits
        if entity_config.get("path") == "__auto_discover__":
            return await self._fetch_all_commits(query_params)

        owner_repo = entity_config.get("path", "")
        branch = entity_config.get("branch", "main")
        if "/" not in owner_repo:
            logger.warning(f"GitHub 仓库路径格式无效: {owner_repo}")
            return []
        owner, repo = owner_repo.split("/", 1)
        token = self.get_api_token()
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        params = {"sha": branch, "since": query_params.get("since"), "until": query_params.get("until"), "per_page": 100}
        try:
            result = await self._fetch_commits(owner, repo, params, headers)
            if len(result) >= 100:
                logger.warning(f"GitHub [{owner_repo}] 返回{len(result)}条（达单页上限）")
            return result
        except Exception as e:
            logger.error(f"GitHub [{owner_repo}] 采集失败: {e}")
            return []

    async def _fetch_all_repos(self) -> list:
        """从 GitHub API 自动发现用户的所有仓库（使用 /user/repos 端点）"""
        token = self.get_api_token()
        repos = []
        page = 1
        max_pages = 10  # 安全上限：最多 1000 个仓库
        async with httpx.AsyncClient(verify=False) as client:
            while page <= max_pages:
                try:
                    headers = {"Authorization": f"Bearer {token}"} if token else {}
                    resp = await client.get(
                        f"{self._api_base_url}/user/repos",
                        params={"per_page": 100, "page": page, "type": "all", "sort": "pushed"},
                        headers=headers, timeout=30,
                    )
                    if resp.status_code != 200:
                        logger.error(f"GitHub 获取仓库列表失败: HTTP {resp.status_code}")
                        break
                    page_repos = resp.json()
                    if not isinstance(page_repos, list) or not page_repos:
                        break
                    for r in page_repos:
                        full_name = r.get("full_name", "")
                        default_branch = r.get("default_branch", "main")
                        repos.append({"name": full_name, "path": full_name, "branch": default_branch})
                    if len(page_repos) < 100:
                        break
                    page += 1
                except Exception as e:
                    logger.error(f"GitHub 自动发现仓库失败: {e}")
                    break
        logger.info(f"GitHub 自动发现 {len(repos)} 个仓库")
        return repos

    async def _fetch_all_commits(self, query_params: dict) -> list:
        """自动发现模式下：遍历所有仓库采集 commits"""
        token = self.get_api_token()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        since, until = query_params.get("since"), query_params.get("until")

        repos = await self._fetch_all_repos()
        if not repos:
            return []
        logger.info(f"GitHub 自动发现 {len(repos)} 个仓库，开始采集...")

        all_commits = []
        for repo_info in repos:
            owner_repo = repo_info.get("path", "")
            branch = repo_info.get("branch", "main")
            if "/" not in owner_repo:
                continue
            owner, repo_name = owner_repo.split("/", 1)
            params = {"sha": branch, "since": since, "until": until, "per_page": 100}
            try:
                result = await self._fetch_commits(owner, repo_name, params, headers)
                if result:
                    for c in result:
                        c["_repo_name"] = owner_repo
                        c["_branch_name"] = branch
                    all_commits.extend(result)
            except Exception as e:
                logger.debug(f"GitHub [{owner_repo}] 跳过: {e}")
        return all_commits

    def get_api_token(self) -> str:
        return config.get("crawler_sources.github.token", "")

    def extract_activity_data(self, raw_data: dict) -> dict:
        commit = raw_data.get("commit", {})
        author = commit.get("author", {})
        return {
            "id": raw_data.get("sha", ""),
            "author_name": author.get("name", ""),
            "author_email": author.get("email", ""),
            "content": commit.get("message", "").split("\n")[0],
            "created_at": author.get("date", ""),
            "metadata": {"branch": raw_data.get("_branch_name", "main")},
        }

    async def collect_source(self, source: dict) -> str:
        owner_repo = source.get("path", "")
        branch = source.get("branch", "main")
        repo_name = source.get("name", owner_repo)
        if "/" not in owner_repo:
            return ""
        owner, repo = owner_repo.split("/", 1)
        since, until = self.get_crawl_dates()
        token = self.get_api_token()
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        params = {"sha": branch, "since": since.isoformat(), "until": until.isoformat(), "per_page": 100}
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await self._fetch_commits(owner, repo, params, headers)
                if len(result) >= 100:
                    logger.warning(f"GitHub [{repo_name}] 返回{len(result)}条（达单页上限）")
                return self._format_commits(result, repo_name)
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (403, 429) and attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"GitHub API 限流，{wait}s 后重试")
                    await asyncio.sleep(wait)
                    continue
                logger.error(f"GitHub [{repo_name}] HTTP {e.response.status_code}")
                return ""
            except Exception as e:
                logger.error(f"GitHub [{repo_name}] 采集失败: {e}")
                return ""
        return ""

    def get_crawl_dates(self):
        now = datetime.now(_TZ)
        return now.replace(hour=0, minute=0, second=0, microsecond=0), now.replace(hour=23, minute=59, second=59, microsecond=0)

    def _format_commits(self, commits, repo_name):
        if not commits:
            return ""
        lines = [f"仓库: {repo_name} (GitHub)", "-" * 40]
        for c in commits:
            commit = c.get("commit", {})
            author = commit.get("author", {})
            msg = commit.get("message", "").split("\n")[0]
            lines.append(f"[{author.get('name', 'unknown')}] {author.get('date', '')[:10]} - {msg}")
        return "\n".join(lines)
