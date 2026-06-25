---
name: domain-survey
description: Survey research groups in a specific academic domain. Given a research topic, find all active groups, their PIs, outstanding students, CCF-A publications (last 5 years), citation counts, and representative works. Trigger when the user asks to investigate, survey, or compare research groups/labs in a field, or wants to know "who is working on X", "which groups publish at top venues in Y domain".
---

# Domain Survey — 领域课题组调研

给定一个研究方向，系统调研该领域内活跃的课题组：PI、优秀学生、近5年顶会发表、引用、代表作。

## 核心原则

- **搜索优先，API 辅助。** 用 Google 搜索发现课题组和代表作，用 OpenAlex API 批量拉取结构化发表数据做交叉验证。
- **以论文找人，以人找组。** 先搜代表性论文/survey → 追溯作者 → 聚合为课题组。
- **会议驱动。** 用户通常关注 CCF-A 级别顶会，以会议论文为核心衡量标准。

## 工作流（5 步）

### 1. 确定领域边界

明确领域关键词、子方向和目标会议列表。搜索 `"<topic>" survey` 或 `"<topic>" CCF-A` 找到已有综述，快速了解领域全貌。与用户确认范围后再深入。

### 2. 发现代表性论文和课题组

搜索 `"<keyword>" <venue> <year>` 找到近5年该领域的核心论文。每找到一篇论文，记录第一作者和通讯作者（通常为最后作者/PI）。自然聚类出主要课题组。

辅助手段：用 `scripts/survey_domain_groups.py --keywords "..." --venues ...` 批量检索 OpenAlex 数据。

### 3. 逐组深入调研

对每个课题组，搜索：
- PI 主页（`"<PI name>" homepage`）→ 获取 lab 成员列表、研究方向
- 实验室主页 → 学生名单、Alumni 去向
- 搜索 `"<PI name>" <venue> <year>` → 补充论文列表

记录：PI 信息、核心学生（已毕业+在读）、各年份顶会论文数、代表作及引用。

### 4. 交叉验证

用 API 查询 PI 的发表记录（`--author "<PI name>"`），对比搜索结果。注意 API 可能遗漏近期论文或会议匹配不准，以 DBLP/Google Scholar 为准。

### 5. 输出报告

按以下结构组织：

```
领域概述 → 各课题组详情（PI/学生/论文表/技术脉络）→ 对比总结表 → 趋势观察
```

每个课题组包含：PI及头衔、核心学生及去向、CCF-A论文列表（年份/会议/标题/引用/备注）、产业合作情况。

## 注意事项

- 领域边界需灵活把控——有些论文跨多个方向，按核心贡献归类。
- 工业界组（如 Meta、Google）的论文作者常流动，按发表时的 affiliation 归属。
- 引用数从 Google Scholar 获取更准确，OpenAlex 引用通常偏低。
- `scripts/survey_domain_groups.py` 适合批量起步，但精细调研必须靠搜索。
