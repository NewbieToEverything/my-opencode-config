# OpenCode 全局配置统一管理

将 OpenCode 的配置文件集中到同一项目目录下管理，通过符号链接同步到 OpenCode 的默认路径，并通过 Git 版本控制并托管到 GitHub，便于跨设备同步和重装后快速恢复。针对 skills,借助 OpenCode 和 Codex 都会扫描 `~/.agents/skills` 目录的这一设定，实现 OpenCode 和 Codex 共享自定义全局 skill 的效果。

---

## 包含内容

| 文件/目录 | 说明 |
|---------|------|
| `skills/` | 自定义全局 Skill 源文件目录。存放在此的自定义 skill 通过软链接注入 `~/.agents/skills/<name>/`，供 OpenCode 和 Codex 按需加载 |
| `rules/` | 自定义规则文件，通过 `opencode.json` 的 `instructions` 字段引入，为 OpenCode 提供额外行为指导 |
| `AGENTS.md` | 全局指令文件，存放于 `~/.config/opencode/AGENTS.md`，在所有会话中生效 |
| `opencode.json` | 全局配置文件，存放于 `~/.config/opencode/opencode.json`，用于配置 LLM 提供商、Agents、MCP 等 |

通过 [skill-manager](https://github.com/NewbieToEverything/skills-manager) 容器安装的第三方全局 skill 自动安装在 `~/.agents/skills/` 目录下，OpenCode 和 Codex 都会扫描该目录。本仓库仅托管**自定义的全局 skill**，通过软链接注入 `.agents/skills/`，实现一处维护、双 agents 共享。

---

## 创建统一管理

### 场景 A：全新安装（从 GitHub 恢复）

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

ln -sf ~/projects/my-opencode-config/AGENTS.md ~/.config/opencode/AGENTS.md
ln -sf ~/projects/my-opencode-config/opencode.json ~/.config/opencode/opencode.json
ln -sf ~/projects/my-opencode-config/rules ~/.config/opencode/rules

# 4. 将自定义 skill 链接到 .agents/skills/
ln -sf ~/projects/my-opencode-config/skills/* ~/.agents/skills/

# 5. 验证
ls -la ~/.config/opencode/ | grep -E "^l"
ls -la ~/.agents/skills/ | grep -E "^l"
```

### 场景 B：现有配置迁移（首次执行）

```bash
# 1. 备份现有配置
cp ~/.config/opencode/AGENTS.md ~/.config/opencode/AGENTS.md.backup
cp ~/.config/opencode/opencode.json ~/.config/opencode/opencode.json.backup

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

ln -sf ~/projects/my-opencode-config/AGENTS.md ~/.config/opencode/AGENTS.md
ln -sf ~/projects/my-opencode-config/opencode.json ~/.config/opencode/opencode.json
ln -sf ~/projects/my-opencode-config/rules ~/.config/opencode/rules

# 4. 将自定义 skill 链接到 .agents/skills/
ln -sf ~/projects/my-opencode-config/skills/* ~/.agents/skills/
```

### 场景 C：新增自定义 Skill

```bash
# 1. 创建 skill 目录
mkdir -p ~/projects/my-opencode-config/skills/<skill-name>
# 2. 编辑 SKILL.md ...

# 3. 同步到 .agents/skills/
ln -sf ~/projects/my-opencode-config/skills/* ~/.agents/skills/

```

---

## 维护说明

### 自定义 Skill 文件结构

```
skills/<skill-name>/
└── SKILL.md
```

### 软链接总览

| 目标路径 | 源路径 |
|---------|--------|
| `~/.config/opencode/AGENTS.md` | `my-opencode-config/AGENTS.md` |
| `~/.config/opencode/opencode.json` | `my-opencode-config/opencode.json` |
| `~/.config/opencode/rules` | `my-opencode-config/rules` |
| `~/.agents/skills/<name>/` | `my-opencode-config/skills/<name>/` |

### 生命周期

- **新增自定义 skill** → 创建目录 → `ln -sf skills/* .agents/skills/` → git add → git commit
- **删除自定义 skill** → git rm → `rm .agents/skills/<name>` → git commit
- **CLI 安装的第三方 skill** → 通过 skill-manager 管理，本仓库不动
