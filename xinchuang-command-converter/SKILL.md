---
name: xinchuang-command-converter
description: 将 x86 架构 CentOS 系统的 Shell 命令、初始化脚本、定时任务脚本和 Docker 部署脚本，转换为鲲鹏 ARM + 统信 UOS / 银河麒麟等信创国产化环境可执行脚本，并输出变更日志、风险警告和国产化替代建议。当用户要求信创迁移、国产化适配、CentOS 转 UOS/麒麟、yum/dnf 转 apt、Docker ARM 架构适配、脚本迁移风险检测或生成可审计变更记录时使用；全程本地离线运行，脚本数据不发送到公网。
---

# 信创命令兼容转换器

将 CentOS/x86 脚本转换为国产信创环境脚本的离线转换器，输出可执行脚本、变更日志、风险警告与替代建议。

## 工作流程

1. 获取输入：接收 Shell 脚本文件路径或对话中的脚本文本。若脚本在对话中，先写入工作目录临时文件，或直接通过 stdin 传给转换脚本。
2. 确认目标环境：默认统信 UOS + 鲲鹏 ARM64；用户指定银河麒麟时传 `--target kylin`，指定其他架构时传 `--arch`。
3. 运行转换引擎：
   ```powershell
   python "C:\Users\16957\.codex\skills\xinchuang-command-converter\scripts\convert_xinchuang.py" <脚本路径> --output converted.sh --report report.json
   ```
   非 Windows 环境使用 `python3`。
4. 读取 `report.json`，向用户展示转换后的脚本全文、变更日志、风险警告和国产化替代建议。
5. 交付文件：将转换后脚本与 JSON 报告保存到用户指定位置，不修改原始文件。
6. 提醒复核：输出为工程辅助参考，复杂业务脚本必须由运维人员人工复核后再上线。

## 转换规则

引擎使用固定映射规则，保证结果稳定可复现：

- 包管理器：`yum` / `dnf` → `apt`
- 软件包名：`redis` → `redis-server`（apt 软件源）
- 服务命令：`service X start` → `systemctl start X`；`chkconfig X on` → `systemctl enable X`
- Docker：`docker run` / `docker create` / `docker build` 自动补齐 `--platform linux/arm64`
- 风险检测：x86 架构假设、强制 `linux/amd64` 平台、旧镜像、x86 rpm 包、`/usr/lib64` 路径、`firewall-cmd` / SELinux 差异等

详细规则见 `references/rule-library.md`；规则数据位于 `scripts/rules.json`，可按项目扩展。

## 转换脚本 CLI

```
python scripts/convert_xinchuang.py [INPUT] [--target uos|kylin] [--arch arm64|amd64] [--output FILE] [--report FILE]
```

- `INPUT`：脚本文件路径；省略时从 stdin 读取
- `--target`：目标系统，默认 `uos`
- `--arch`：目标架构，默认 `arm64`
- `--output`：转换后脚本输出文件；缺省输出到 stdout
- `--report`：JSON 报告文件（变更日志、风险、建议）；缺省时报告打印在 stdout 的 `---REPORT---` 之后

## 边界

- 仅适配 Shell 命令与 Docker 指令，不修改 Java/Python 等业务代码
- 不自动修复复杂脚本逻辑、自定义函数、嵌套管道报错
- 转换结果需人工复核，不替代专业运维工程师
- 全程本地离线运行，不把内网脚本发送到外部模型或公网服务
