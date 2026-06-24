"""GitHub API 声明层"""
from api import apis

apis.declare("repo_github", "get_commits", url="/repos/{owner}/{repo}/commits", method="GET")
apis.declare("repo_github", "get_user_repos", url="/users/{username}/repos", method="GET")
apis.declare("repo_github", "get_org_repos", url="/orgs/{org}/repos", method="GET")
