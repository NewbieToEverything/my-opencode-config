# 网页工具使用规则

- agent-browser
  - 使用 agent-browser 处理复杂的网页交互任务（获取网页数据、填写表单、点击按钮、截图、抓取动态内容、测试网页应用或自动化桌面应用）
  - 使用 agent-browser 读取或写入文件时，必须把文件放在 `/tmp` 下
  - agent-browser 不适用时（如操作失败、验证码测试失败等），使用 curl/wget
- 使用内置 web 工具处理简单的一次性网页获取任务（读取静态内容、获取文档或搜索）

## 网站特定规则
所有 GitHub.com 操作（搜索仓库、查看 issue、读取文件等）**必须**使用以下方式之一：
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
