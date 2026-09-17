# AgentSentinel 运行环境与依赖配置

本指南用于运行仓库中的 `AgentSentinel/run_demo.py`。项目是入门研究原型：默认只进行本地离线工具检查，只有显式传入 `--live` 才调用真实模型 API。

## 1. 环境要求

| 项目 | 要求 |
| --- | --- |
| Python | 建议 Python 3.11；本地核验版本为 3.11.9。源码使用 Python 3.10+ 的类型语法，其他版本未全面验证 |
| 操作系统 | 提供 Windows PowerShell 与 Linux/macOS shell 命令；此次环境核验在 Windows 完成 |
| GPU / CUDA | 不需要；模型通过远程 API 调用 |
| Docker / 数据库 / Web 服务 | 不需要 |
| 文件权限 | 离线 demo 需要读取 `AgentSentinel/sandbox/`；使用写入或模拟发送工具时需要该目录写权限 |
| 网络 | 安装依赖时需要访问包源；离线 demo 不需要网络；live 模式需要访问所选 API 服务 |

依赖以 **`AgentSentinel/requirements.txt`** 为准，不要误用仓库根目录的同名文件：

```text
openai>=1.0.0
pytest>=8.0.0
```

- `openai`：live 模式所需的 OpenAI-compatible SDK。
- `pytest`：运行测试所需，demo 本身不依赖 pytest。
- 离线 demo 本身只使用 Python 标准库；下述安装命令用于一次准备完整项目环境。
- 本地现有环境核验版本：`openai 3.13.0`、`pytest 9.1.1`。这不是锁定依赖，新安装可能获得其他版本。

## 2. 获取代码与准备 Python 环境

以下命令假定已安装 Git 和 Python 3.11。已经有仓库时跳过 clone，并进入现有仓库根目录。

```text
git clone https://github.com/Infinity-hub-cloud/AgentSentinel_self_exploring.git
cd AgentSentinel_self_exploring
```

### Windows PowerShell

```powershell
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r .\AgentSentinel\requirements.txt
.\venv\Scripts\python.exe --version
cd AgentSentinel
..\venv\Scripts\python.exe run_demo.py
```

如果没有 `py` 启动器，先用 `python --version` 确认版本，再用 `python -m venv venv`。已有可用虚拟环境时复用即可，不必重复创建或安装。

上述写法直接调用虚拟环境中的 Python，不需要运行 `Activate.ps1`，也不需要修改 PowerShell 执行策略。

### Linux / macOS

```bash
python3.11 -m venv venv
./venv/bin/python -m pip install -r ./AgentSentinel/requirements.txt
./venv/bin/python --version
cd AgentSentinel
../venv/bin/python run_demo.py
```

`python3.11` 不存在时，应先安装 Python 3.11，或确认系统 `python3` 的版本适用再替换命令。部分 Linux 发行版需要另行安装与 Python 版本匹配的 venv 系统包。

## 3. 默认离线 demo：无需密钥

不传 `--live` 时，demo 列出 sandbox 内文件，读取 `sandbox/files/hello.txt`，随后退出。成功输出包含：

```text
Offline tool check: Hello from the AgentSentinel sandbox.
Offline mode: no API call was made. Use --live to opt in.
```

这只能证明本地工具检查能运行，不代表已经验证模型 tool-use、runtime defense 或攻击实验效果。默认运行不保存实验结果 JSON。

## 4. 可选：人工启用真实 API

**评委如果只检查本地启动，可以跳过本节。** live 模式可能产生费用，并将任务消息及后续工具返回内容发送给所选模型服务。仅使用人工准备的非敏感 sandbox 内容。

模型服务必须支持 OpenAI-compatible **Chat Completions 与 function/tool calling**；仅兼容普通文本聊天不够。

| 环境变量 | 含义 | 当前代码默认值 |
| --- | --- | --- |
| `OPENAI_API_KEY` | 所选服务的 API Key，live 模式必填 | 无；缺失时报错 |
| `OPENAI_BASE_URL` | 服务的 API 根地址，通常包含 `/v1`；不是完整 `/chat/completions` 地址 | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 服务实际提供且支持 tool calling 的模型 ID | `gpt-4o-mini` |

**当前代码通过 `os.getenv()` 读取环境变量，不会自动加载 `.env`。仅创建或填写 `.env` 文件不会生效。** 下述变量只在当前 shell 会话中设置；不要将真实密钥写入仓库、截图或输出记录。

在 `AgentSentinel` 目录内执行，先将占位内容替换为所选服务的实际值：

```powershell
# Windows PowerShell
$env:OPENAI_API_KEY = "YOUR_API_KEY"
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"
$env:OPENAI_MODEL = "YOUR_TOOL_CALLING_MODEL_ID"
..\venv\Scripts\python.exe run_demo.py --live --prompt "List the files in the sandbox." --max-steps 5 --defense on
```

```bash
# Linux / macOS
export OPENAI_API_KEY="YOUR_API_KEY"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="YOUR_TOOL_CALLING_MODEL_ID"
../venv/bin/python run_demo.py --live --prompt "List the files in the sandbox." --max-steps 5 --defense on
```

`--defense off` 关闭 runtime policy，`--defense on` 开启；默认关闭。不加 `--live` 时不会进入 Agent 循环，因此仅传 `--defense on` 不会执行防御检查。`--max-steps` 必须至少为 1，限制模型交互轮次而非工具调用总数。

文件与邮件工具受 sandbox 路径限制；`send_email` 只写本地模拟邮件，不真正发送邮件。这个路径限制不是操作系统级沙箱。runtime policy 也不阻止将上下文发送到模型 API，不能用于保护真实密钥或隐私数据。

## 5. 常见问题

| 现象 | 排查方法 |
| --- | --- |
| 找不到 `run_demo.py` | 先进入仓库内的 `AgentSentinel` 子目录 |
| 找不到 Python / venv 路径 | 检查 Python 安装，以及 `venv` 是否位于仓库根目录；使用自己的虚拟环境时替换命令路径 |
| `No module named openai` | 用运行 demo 的同一个 Python 执行 `-m pip install -r requirements.txt`（此时位于 `AgentSentinel` 目录） |
| `OPENAI_API_KEY is required` | live 模式未获得环境变量；在同一个 shell 中设置，不能只填写 `.env` |
| 401 / 403 | 检查服务密钥和访问权限，不要公开密钥求助 |
| 404 / model not found | 检查 Base URL 与所选服务实际支持的模型 ID |
| 不支持 tools / function calling | 更换为支持 Chat Completions tool calling 的模型及服务 |
| 连接失败 / 超时 | 检查网络、代理和服务可达性；离线检查不依赖 API 网络 |
| `files/hello.txt` 找不到 | 确认仓库完整，`AgentSentinel/sandbox/files/hello.txt` 没有被删除 |
| 只看到 Offline mode | 这是默认行为；确需真实模型调用时才显式传入 `--live` |

本指南依据当前源码与现有本地环境编写，未执行真实 API、攻击实验或新建环境安装验证；不承诺所有 OpenAI-compatible 服务均兼容。
