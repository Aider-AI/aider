---
parent: More info
nav_order: 110
description: 查看 git 提交历史并获取每次提交的详细信息。
---

# 查看 git 提交历史

Aider 使用 git 来跟踪所有代码变更。通过浏览提交记录，可以了解项目的演进过程。

## 查看提交列表

使用 `git log --oneline` 可以看到提交哈希值和每条提交信息：

```bash
git log --oneline | head
```

示例输出：

```bash
b2592267 lint
29874f12 feat: validation and errors for copilot requests
```

## 查看单次提交详情

要查看某次提交的详细差异与描述，可使用 `git show` 并提供提交哈希值：

```bash
git show 29874f12
```

这会展示该提交的完整信息和对应的代码改动。
