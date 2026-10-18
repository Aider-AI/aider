# Aider 的 Ace Data Cloud 原生接入候选

这是 Ace Data Cloud 维护的候选源码，不是 Aider 官方发行或官方认可。原生目标是用 `acedatacloud/模型名` 选择 Ace、读取专用 Key 并自动配置地址。当前正式包 0.86.2 尚不包含这项功能；正式安装入口仍是 [Aider 官方安装页](https://aider.chat/docs/install.html)，当前用户继续使用 [Ace 手动指南](https://platform.acedata.cloud/documents/aider-cli-integration?utm_source=github&utm_medium=referral&utm_campaign=evergreen&utm_content=aider_readme_zh_setup)。

## 注册、通用应用与专用 Token

1. 打开 [Ace Applications](https://platform.acedata.cloud/console/applications?utm_source=github&utm_medium=referral&utm_campaign=evergreen&utm_content=aider_readme_zh_signup) 注册并登录。
2. 进入通用应用（General application），没有则先初始化。复制现有 API Token，或点击管理密钥→创建，命名为 `Aider`。
3. 核对所选聊天模型的 API 权限、用量限制、过期时间、余额和 [当前价格](https://platform.acedata.cloud/models?utm_source=github&utm_medium=referral&utm_campaign=evergreen&utm_content=aider_readme_zh_pricing)。不要用平台管理 Token，也不加 `Bearer `。

![复制Key或进入管理密钥，真实值已遮挡](https://raw.githubusercontent.com/AceDataCloud/SunoDify/8d3d03570e73324220f111f7fe343da0792a8071/_assets/tutorial/get-api-key-en.png)

![创建独立Token](https://raw.githubusercontent.com/AceDataCloud/SunoDify/8d3d03570e73324220f111f7fe343da0792a8071/_assets/tutorial/create-api-key-en.png)

两图为 Ace 通用应用原图，来自 2026-10-08 SunoDify 源提交；图中 Dify tutorial 只是名称例子，此处填 Aider。允许 API 应按所选 Chat Completions 模型设置，不照抄 Suno 生成/查询接口。图片不是 Aider 设置界面，不证明调用成功。

## 在候选源码选择 Ace

由自己的密钥管理方式给启动 shell 提供 `ACEDATACLOUD_API_KEY` 的值，再执行：

```bash
export ACEDATACLOUD_API_KEY
aider --list-models acedatacloud/
aider --model acedatacloud/gpt-4.1
```

`export` 本身不会生成密钥值。候选已内置 Ace 地址，不借用其他平台的 Key 或自动切模型；仍需明确选择账户允许的模型。首次只加一个临时文件、提小修改、运行固定测试，检查文件实际变更和测试通过。聊天回复不代替文件结果；失败修复与重试也产生用量。

[英文完整说明](README.md) 包含源码审查、错误码、依赖问题和 CLA 门槛。本地模拟改文件/测试修复已做，但不是生产模型和账单验收。官方截图改编只作交互参考，尚无原生 Ace 界面或正式发行截图。

Aider 当前没有正式媒体插件目录，Suno、Seedance、HappyHorse、GPT Image、Nano Banana 不适合作为代码模型添加。没有为这些服务创建无用 Aider 空包；应使用支持现有单服务集成的客户端。后续如官方合入 MCP，再评估复用既有服务仓。
