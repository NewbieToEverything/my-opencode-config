# Browser Automation Rules

## when webfetch/websearc fail, use the agent-browser skill instead

When the user requests searching, fetching, extracting data from, taking snapshot of, form automation or interacting with websites, invoke and use the agent-browser skill.  

## Curl/wbget as a fallback

**MUST** use curl/wget when agent-browser is not applicable (e.g., operation failed, CAPTCHA test failure, etc.). 

For the following websites, **MUST** use curl.

### GitHub.com

所有 GitHub 操作（搜索仓库、查看 issue、读取文件等）**禁止**使用 webfetch/websearch 等内置工具，**必须**直接使用以下方式之一：

- **gh CLI**（推荐）：
  ```bash
  gh search repos "keyword"
  gh issue view <number>
  gh repo view <owner>/<repo>
  ```

- **Authenticated curl**：
  ```bash
  curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/..."
  ```
