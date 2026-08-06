# 信创命令转换器

将 x86 架构 CentOS 系统的 Shell 命令、初始化脚本、定时任务脚本和 Docker 部署脚本，转换为鲲鹏 ARM + 统信 UOS / 银河麒麟 / 欧拉 OS 等信创国产化环境可执行脚本，并输出变更日志、风险警告和国产化替代建议。

全程本地离线运行，脚本数据不会发送到公网。

## 功能

- `yum` / `dnf` 转换为 `apt`，并自动选择 UOS / 麒麟 / 欧拉适配包名
- `service` / `chkconfig` 转换为 `systemctl` 管理方式
- Docker 命令自动补齐 `--platform linux/arm64`，并检查镜像 ARM 兼容性
- 跳过 `#` 注释行与行内注释，避免误改注释
- 输出变更日志（`report.json`）与风险警告，审计日志对密码、密钥脱敏
- 内置国产化替代建议（国产软件源、国产 Redis、信创镜像等）

## 安全说明

- 本工具只做静态文本解析与字符串替换，绝不执行、运行或求值用户传入的 Shell 脚本。
- 转换结果仅供工程评估参考，转换完成脚本务必人工复测后上生产环境。
- 详细安全约定见 [SECURITY.md](SECURITY.md)。

## 使用示例

输入（CentOS/x86）：

```bash
yum install nginx -y
yum install redis -y
service nginx start
chkconfig nginx on
docker run -d --name redis redis:6
```

转换命令：

```powershell
python xinchuang-command-converter/main.py input.sh --target-env "统信UOS ARM" --output converted.sh --report report.json
```

输出（转换后脚本）：

```bash
apt install nginx -y
apt install redis-server -y
systemctl start nginx
systemctl enable nginx
docker run --platform linux/arm64 -d --name redis redis:6
```

同时生成包含变更日志、风险警告、国产化替代建议和人工复测告警的 `report.json`。

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
python xinchuang-command-converter/main.py input.sh --target-env "银河麒麟ARM" -o converted.sh --report report.json
```

可选目标环境：`银河麒麟ARM`、`统信UOS ARM`、`欧拉OS ARM`；同时兼容旧参数 `--target uos|kylin|euler` 与 `--arch arm64|amd64`。

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

- 支持目标系统：统信 UOS、银河麒麟、欧拉 OS（鲲鹏 ARM）
- 支持输入：Shell 命令、初始化脚本、定时任务脚本、Docker 部署脚本
- 输出：转换后脚本、变更日志、风险警告、国产化替代建议
- 开源许可：MIT，见 [LICENSE](LICENSE)
