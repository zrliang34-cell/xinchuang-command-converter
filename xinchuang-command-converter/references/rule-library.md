# 信创命令转换规则库

本文件是 `xinchuang-command-converter` 的详细规则说明，供需要人工复核、扩展规则或处理复杂脚本时查阅。规则数据本体在 `../scripts/rules.json`。

## 目录

- [安全约束](#安全约束)
- [包管理器与软件包](#包管理器与软件包)
- [系统服务命令](#系统服务命令)
- [Docker 架构适配](#docker-架构适配)
- [风险检测规则](#风险检测规则)
- [国产化替代建议](#国产化替代建议)
- [规则扩展方法](#规则扩展方法)

## 安全约束

- 本工具只做静态文本解析与字符串替换，绝不执行、运行或求值用户传入的 Shell 脚本，不调用 subprocess 执行用户输入内容。
- 跳过 `#` 注释行，注释内关键字不做替换；行内注释（`#` 之后部分）同样原样保留。
- 审计变更日志会对疑似密码、密钥字符串做掩码脱敏（password、token、api_key、private key 块、URL 凭据等）。
- 转换结果仅供工程评估参考，转换完成脚本务必人工复测后上生产环境。

## 包管理器与软件包

CentOS 使用 `yum` / `dnf`，统信 UOS、银河麒麟、欧拉 OS 的软件源基于 Debian 体系，使用 `apt`：

| 原命令 | 转换后 | 说明 |
| --- | --- | --- |
| `yum install nginx -y` | `apt install nginx -y` | 直接替换包管理器关键字 |
| `dnf install redis -y` | `apt install redis-server -y` | 同时修正包名 |
| `yum update` / `dnf update` | `apt update` | 更新软件源索引 |
| `yum upgrade` / `dnf upgrade` | `apt upgrade` | 升级已安装软件包 |
| `yum remove <pkg>` / `dnf remove <pkg>` | `apt remove <pkg>` | 卸载软件包 |
| `yum clean all` / `dnf clean all` | `apt clean` | 清理缓存 |

自动修正的软件包名：

| 原包名 | 转换后 | 说明 |
| --- | --- | --- |
| `redis` | `redis-server` | Debian/统信/麒麟/欧拉软件源中的 Redis 服务包 |

其他常见差异包名（不自动替换，需用 `apt-cache search` 或 `apt show` 在目标环境确认）：

- `httpd` → `apache2`
- `mysql-server` → `mariadb-server` / `default-mysql-server`
- `docker-ce` → `docker.io` 或国产软件源中的 Docker 包
- `libstdc++-devel` → 目标系统对应 dev 包

## 系统服务命令

国产系统普遍使用 systemd：

| 原命令 | 转换后 |
| --- | --- |
| `service nginx start` | `systemctl start nginx` |
| `service nginx stop` | `systemctl stop nginx` |
| `service nginx restart` | `systemctl restart nginx` |
| `service nginx status` | `systemctl status nginx` |
| `chkconfig nginx on` | `systemctl enable nginx` |
| `chkconfig nginx off` | `systemctl disable nginx` |
| `chkconfig --add nginx` | `systemctl enable nginx` |

`systemctl` 系列命令本身在国产系统通用，不需要转换。

## Docker 架构适配

鲲鹏为 ARM 架构，Docker 运行命令需要显式声明平台：

| 原命令 | 转换后 |
| --- | --- |
| `docker run -d --name redis redis:6` | `docker run --platform linux/arm64 -d --name redis redis:6` |
| `docker create ...` | 同样在子命令后插入 `--platform linux/arm64` |
| `docker build -t app .` | `docker build --platform linux/arm64 -t app .` |

规则说明：

- 仅当该命令未包含 `--platform` 时插入，避免重复参数。
- 若已存在 `--platform linux/amd64`，保留原参数并输出 high 级风险警告。
- 所有 `docker run` / `docker create` / `docker build` / `docker pull` 都会触发 `docker-arm-check` 风险，提示确认镜像是否存在 ARM 架构版本。
- `docker-compose.yml` 或 `docker compose` 服务配置不是逐行 Shell 命令，需检查服务级 `platform: linux/arm64` 字段，转换器会给出通用提示，不自动改写 YAML。
- 转换器只处理单行命令；多行续行（`\`）场景在人工复核时确认参数位置。

## 风险检测规则

风险按严重程度分级：`high` 会导致运行失败，`medium` 大概率需要调整，`low` 为需确认项。

| 风险 ID | 检测内容 | 级别 |
| --- | --- | --- |
| `docker-arm-check` | Docker run/create/build/pull 镜像 ARM 兼容性 | medium |
| `forced-amd64` | Docker 强制 `--platform linux/amd64` | high |
| `x86-rpm` | 引用 `.x86_64.rpm` 包 | high |
| `x86_64-literal` | 脚本硬编码 `x86_64` 架构字符串 | medium |
| `arch-probe` | 使用 `uname -m` / `uname -p` 探测架构 | medium |
| `rpm-install` | 直接使用 `rpm -U/-i/-v/-h` 安装 | medium |
| `lib64-path` | 硬编码 `/usr/lib64` 库路径 | medium |
| `firewalld` | 使用 `firewall-cmd` | medium |
| `selinux` | 使用 SELinux 命令或配置 | low |
| `yum-remnant` | 转换后仍残留 `yum` / `dnf` | low |

镜像风险（针对旧镜像）：

| 风险 ID | 检测内容 | 级别 |
| --- | --- | --- |
| `redis-6-image` | `redis:6` 等旧 tag | medium |
| `mysql-57-image` | `mysql:5.x` | medium |
| `mysql-80-image` | `mysql:8.0.x` | low |

## 国产化替代建议

替代方案仅作为工程评估方向，任何数据库或中间件替换都必须在目标环境完成兼容性验证：

- Redis：优先官方多架构高版本镜像（如 `redis:7-alpine`），或使用统信/麒麟/欧拉软件源中的 Redis 包。
- 数据库：可评估 openGauss、GreatSQL、OceanBase 社区版等国产方案；不建议未验证直接切换。
- 软件包来源：优先目标系统官方软件源，避免使用来源不明的第三方包。

## 规则扩展方法

规则全部集中在 `../scripts/rules.json`：

1. `package_manager`、`commands`、`package_names` 为对象数组，每项字段：`pattern`（正则）、`replacement`（替换串）、`description`（变更说明）、`note`（风险备注）。
2. 在 `risk_patterns` 中追加风险模式，字段：`id`、`pattern`、`severity`、`message`、`suggestion`。
3. 在 `image_risks` 中追加镜像风险，可关联 `recommendation`。
4. 在 `recommendations` 中追加替代建议，用 `id` 关联镜像风险。
5. 顶层 `notice` 为每次转换输出的人工复测告警。

新增规则后运行 `python xinchuang-command-converter/main.py <样例脚本> --target-env "统信UOS ARM"` 验证输出与报告。
