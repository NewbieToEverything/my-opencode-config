# 浏览器自动化规则

## 通用规则

- 使用 agent-browser 处理网页交互任务（浏览页面、填写表单、点击按钮、截图、抓取动态内容、测试网页应用或自动化桌面应用），agent-browser 不适用时（如操作失败、验证码测试失败等），使用 curl/wget
- 使用内置 web 工具处理简单网页获取任务（读取静态内容、获取文档或搜索）
- agent-browser 通过容器运行时，只共享 `/tmp`、CLI 二进制和 `skill-data/`；需要让浏览器读取或写入宿主文件时，必须把文件放在 `/tmp` 下
- 常见文件读写命令：`agent-browser open file:///tmp/page.html`、`agent-browser screenshot /tmp/page.png`、`agent-browser pdf /tmp/page.pdf`、`agent-browser snapshot -i > /tmp/snapshot.txt`

## 网站特定规则

所有 GitHub 操作（搜索仓库、查看 issue、读取文件等）**必须**使用以下方式之一：

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
