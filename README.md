# xinchuang-command-converter

将 x86 架构 CentOS 系统的 Shell 命令、初始化脚本、定时任务脚本和 Docker 部署脚本，转换为鲲鹏 ARM + 统信 UOS / 银河麒麟等信创国产化环境可执行脚本，并输出变更日志、风险警告和国产化替代建议。

全程本地离线运行，脚本数据不会发送到公网。

## 功能

- `yum` / `dnf` 转换为 `apt`，并自动选择 UOS / 麒麟适配包名
- `service` / `chkconfig` 转换为 `systemctl` 管理方式
- Docker 命令增加 ARM 架构兼容检查
- 输出变更日志（`report.json`）与风险警告
- 内置国产化替代建议（国产软件源、国产 Redis、信创镜像等）

## 安装

将 `xinchuang-command-converter` 目录放入 Codex 的 skills 目录：

```text
~/.codex/skills/xinchuang-command-converter/
├── SKILL.md
├── agents/openai.yaml
├── references/rule-library.md
└── scripts/
    ├── convert_xinchuang.py
    └── rules.json
```

然后在 Codex 中使用：

```text
使用 $xinchuang-command-converter 转换以下脚本：
<粘贴 CentOS 脚本>
```

## 命令行使用

```powershell
python scripts/convert_xinchuang.py input.sh -o converted.sh --report report.json
```

## 目录结构

```text
xinchuang-command-converter/
├── SKILL.md                      技能说明与调用方式
├── agents/openai.yaml            Codex agent 配置
├── references/rule-library.md    转换规则库说明
└── scripts/
    ├── convert_xinchuang.py      转换主程序
    └── rules.json                命令与软件包转换规则
```

## 说明

- 支持目标系统：统信 UOS、银河麒麟（鲲鹏 ARM）
- 支持输入：Shell 命令、初始化脚本、定时任务脚本、Docker 部署脚本
- 输出：转换后脚本、变更日志、风险警告、国产化替代建议
