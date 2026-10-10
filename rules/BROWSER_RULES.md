# 网页工具使用规则

- agent-browser
  - 工具可用时，优先使用 agent-browser 处理复杂网页交互和受支持的桌面应用自动化。
  - 使用 agent-browser 读取或写入文件时，必须把文件放在 `/tmp` 下
  - 静态获取失败可使用 curl/wget；交互失败时使用能完成同一操作的其他已授权工具，无法完成则说明阻塞；安装新工具仍须确认。
- 使用内置 web 工具处理简单的一次性网页获取任务（读取静态内容、获取文档或搜索）

## 网站特定规则
GitHub 网页/API 的搜索与读取（如查仓库、issue、文件）必须使用以下方式之一；仓库 fetch、pull、push 使用 Git CLI：
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

认证操作不得打印凭据、输出认证头，或将敏感信息写入报告。
