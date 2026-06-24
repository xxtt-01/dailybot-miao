"""Gitee API 声明层"""
from api import apis

apis.declare("repo_gitee", "get_commits", url="/repos/{owner}/{repo}/commits", method="GET")
apis.declare("repo_gitee", "get_user_repos", url="/users/{username}/repos", method="GET")
