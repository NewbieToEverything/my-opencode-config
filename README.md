# OpenCode 全局配置统一管理

将 OpenCode 的全局 skills、AGENTS.md 和配置文件集中到同一项目目录下管理，通过符号链接同步到 OpenCode 的默认路径，并通过 Git 版本控制并托管到 GitHub，便于跨设备同步和重装后快速恢复。

---

## 包含内容

| 文件/目录 | 说明 |
|---------|------|
| `skills/` | 自定义全局 Skills，存放于 `~/.config/opencode/skills/*/SKILL.md`，供 agents 按需加载 |
| `AGENTS.md` | 全局指令文件，存放于 `~/.config/opencode/AGENTS.md`，在所有会话中生效 |
| `opencode.json` | 全局配置文件，存放于 `~/.config/opencode/opencode.json`，用于配置 LLM 提供商、Agents、MCP 等 |

注：我个人习惯在 `~/.config/opencode/skills/` 目录下只放置自定义的全局 skill。从 GitHub repo 或通过其他方式安装的第三方全局 skill 通过 [skill-manager](https://github.com/NewbieToEverything/skills-manager) 容器统一管理并安装在`~/.agents/skills/` 目录下， OpenCode 默认会扫描并加载该目录内的 skill 为全局 skill。

---

## 创建统一管理

### 场景 A：全新安装（从 GitHub 恢复）

适用于：针对全新安装的 OpenCode，从 GitHub 拉取已有配置

```bash
# 1. 创建项目目录
cd ~/projects
mkdir my-opencode-config

# 2. 克隆仓库（替换 <username> 为你的 GitHub 用户名）
git clone git@github.com:<username>/my-opencode-config.git ~/projects/my-opencode-config
cd ~/projects/my-opencode-config

# 3. 创建符号链接（先删除原文件/目录）
rm -f ~/.config/opencode/AGENTS.md
rm -f ~/.config/opencode/opencode.json
rm -rf ~/.config/opencode/skills

ln -sf ~/projects/my-opencode-config/AGENTS.md ~/.config/opencode/AGENTS.md
ln -sf ~/projects/my-opencode-config/opencode.json ~/.config/opencode/opencode.json
ln -sf ~/projects/my-opencode-config/skills ~/.config/opencode/skills
ln -sf ~/projects/my-opencode-config/rules ~/.config/opencode/rules

# 3. 验证
ls -la ~/.config/opencode/ | grep -E "^l"
```

## 场景 B：现有配置迁移（首次执行）

适用于：已有本地配置，但并未集中到同一项目目录下使用 git 统一管理

```bash
# 1. 备份现有配置
cp ~/.config/opencode/AGENTS.md ~/.config/opencode/AGENTS.md.backup
cp ~/.config/opencode/opencode.json ~/.config/opencode/opencode.json.backup

# 2. 初始化仓库
mkdir -p ~/projects/my-opencode-config
cd ~/projects/my-opencode-config
git init
git branch -m main

# 3. 复制现有配置到仓库
cp ~/.config/opencode/AGENTS.md ./
cp ~/.config/opencode/opencode.json ./
[ -d ~/.config/opencode/skills ] && cp -r ~/.config/opencode/skills/ ./

# 4. 创建 .gitignore
echo "auth.json" > .gitignore

# 5. 提交
git add -A
git commit -m "统一管理 OpenCode 全局配置"

# 6. 推送到 GitHub（替换 <username> 为你的 GitHub 用户名）
git remote add origin git@github.com:<username>/my-opencode-config.git
git branch -M main
git push -u origin main

# 7. 创建符号链接（先删除原文件/目录）
rm -f ~/.config/opencode/AGENTS.md
rm -f ~/.config/opencode/opencode.json
rm -rf ~/.config/opencode/skills

ln -sf ~/projects/my-opencode-config/AGENTS.md ~/.config/opencode/AGENTS.md
ln -sf ~/projects/my-opencode-config/opencode.json ~/.config/opencode/opencode.json
ln -sf ~/projects/my-opencode-config/skills ~/.config/opencode/skills
```
