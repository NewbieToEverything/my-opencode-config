# OpenCode 全局配置统一管理

将 OpenCode 的配置文件集中到同一项目目录下管理，通过符号链接同步到 OpenCode 和 Codex 的默认路径，实现一套配置， OpenCode 和 Codex 共享。

## 管理内容

| 文件/目录 | 说明 |
|---------|------|
| `skills/` | 自定义全局 Skill 源文件目录。存放在此的自定义 skill 通过软链接注入 `~/.agents/skills/<name>/`（OpenCode 和 Codex 均扫描） |
| `AGENTS.md` | 全局指令文件，存放于 `~/.config/opencode/AGENTS.md`|
| `opencode.json` | 全局配置文件（仅适用于 OpenCode），存放于 `~/.config/opencode/opencode.json`|
| `rules/` | 自定义规则文件，通过 `opencode.json` 的 `instructions` 字段引入|

软链接总览：
| 目标路径 | 源路径 |
|---------|--------|
| `~/.agents/skills/<name>/` | `my-opencode-config/skills/<name>/` |
| `~/.config/opencode/AGENTS.md` | `my-opencode-config/AGENTS.md` |
| `~/.codex/AGENTS.md` | `my-opencode-config/AGENTS.md` |
| `~/.config/opencode/opencode.json` | `my-opencode-config/opencode.json` |
| `~/.config/opencode/rules` | `my-opencode-config/rules` |


## 管理方式

### 场景 A：从 GitHub 恢复

```bash
# 1. 创建项目目录
cd ~/projects
mkdir my-opencode-config

# 2. 克隆仓库
git clone git@github.com:<username>/my-opencode-config.git ~/projects/my-opencode-config
cd ~/projects/my-opencode-config

# 3. 创建符号链接（配置文件）
rm -f ~/.config/opencode/AGENTS.md
rm -f ~/.config/opencode/opencode.json
rm -rf ~/.config/opencode/rules
rm -f ~/.codex/AGENTS.md

ln -sf ~/projects/my-opencode-config/AGENTS.md ~/.config/opencode/AGENTS.md
ln -sf ~/projects/my-opencode-config/opencode.json ~/.config/opencode/opencode.json
ln -sf ~/projects/my-opencode-config/rules ~/.config/opencode/rules
ln -sf ~/projects/my-opencode-config/AGENTS.md ~/.codex/AGENTS.md

# 4. 将自定义 skill 链接到 .agents/skills/
ln -sf ~/projects/my-opencode-config/skills/* ~/.agents/skills/

# 5. 验证
ls -la ~/.config/opencode/ | grep -E "^l"
ls -la ~/.codex/ | grep -E "^l"
ls -la ~/.agents/skills/ | grep -E "^l"
```

### 场景 B：现有配置迁移（首次执行）

```bash
# 1. 备份现有配置
cp ~/.config/opencode/AGENTS.md ~/.config/opencode/AGENTS.md.backup
cp ~/.config/opencode/opencode.json ~/.config/opencode/opencode.json.backup
cp ~/.codex/AGENTS.md ~/.codex/AGENTS.md.backup

# 2. 创建项目目录并复制配置
mkdir -p ~/projects/my-opencode-config
cd ~/projects/my-opencode-config
cp ~/.config/opencode/AGENTS.md ./
cp ~/.config/opencode/opencode.json ./
[ -d ~/.config/opencode/rules ] && cp -r ~/.config/opencode/rules/ ./
[ -d ~/projects/my-opencode-config/skills ] || mkdir -p skills

# 3. 创建符号链接（配置文件）
rm -f ~/.config/opencode/AGENTS.md
rm -f ~/.config/opencode/opencode.json
rm -rf ~/.config/opencode/rules
rm -f ~/.codex/AGENTS.md

ln -sf ~/projects/my-opencode-config/AGENTS.md ~/.config/opencode/AGENTS.md
ln -sf ~/projects/my-opencode-config/opencode.json ~/.config/opencode/opencode.json
ln -sf ~/projects/my-opencode-config/rules ~/.config/opencode/rules
ln -sf ~/projects/my-opencode-config/AGENTS.md ~/.codex/AGENTS.md

# 4. 将自定义 skill 链接到 .agents/skills/
ln -sf ~/projects/my-opencode-config/skills/* ~/.agents/skills/
```

### 场景 C：新增自定义全局 Skill

```bash
# 1. 创建 skill 目录
mkdir -p ~/projects/my-opencode-config/skills/<skill-name>
# 2. 编辑 SKILL.md ...

# 3. 同步到 .agents/skills/
ln -sf ~/projects/my-opencode-config/skills/* ~/.agents/skills/

```
