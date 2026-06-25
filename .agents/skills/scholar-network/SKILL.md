---
name: scholar-network
description: Query a scholar's complete academic connection network including coauthors, lab mates, advisors, and institutional collaborators. Use this skill whenever the user wants to find a researcher's academic relationships, collaboration graph, lab members, co-authors, advisor lineage, or academic social network. Trigger when the user mentions finding connections, collaborators, academic network, lab mates, or research group members for a specific scholar or professor.
---

# Scholar Network — 学者学术关系网络查询

查询单个学者的完整学术 connection 网络：合作者、导师、实验室同期成员（±1级）、跨机构合作者。

## 核心原则

- **搜索优先，API 辅助。** Google 搜索（`web_search`）是发现和验证信息的主要手段。API（pyalex/OpenAlex）用于批量拉取结构化数据，但其结果可能滞后、不全、或存在 profile 合并错误，必须通过搜索交叉验证。
- **一手来源优先。** 个人主页、实验室官网、学校教师页 > API 数据 > 推断。
- **中文学者需额外搜索。** 中文期刊/国内会议在 OpenAlex 覆盖不全。

## 工作流（5 步）

### 1. 定位学者

通过 Google 搜索找到个人主页/学校页面，确认身份、机构、ORCID。搜索 `"<name>" homepage` 或 `"<name>" <university>`。如有 ORCID 或 OpenAlex ID 可直接用 API 查询。注意重名消歧。

### 2. 获取论文与合作者

用 API 批量拉取论文列表和 authorship，构建合作者频次图谱。对比 Google Scholar / DBLP 验证论文数是否合理；API 缺失的近期论文通过搜索补充。

### 3. 识别导师

首选搜索确认（`"<name>" advised by`、个人主页 Bio、博士论文）。辅助判断：合作频次最高的资深教授，合作跨越整个博士期间。找到后搜索导师页面验证（`"<advisor>" students`）。

### 4. 追溯实验室同期成员

**最佳路径：** 搜索实验室官网（`"<advisor>" lab team members`），直接获取在读学生和 Alumni 列表。

**备选路径：** 查询导师的 API 合作者数据，筛选同时满足以下条件的人：同机构 + 时间重叠（±1年容差）+ 与导师合作 ≥2 次。

### 5. 输出报告

分层汇总：

```
基本信息 → 导师 → 同期成员（±1级）→ 核心合作者 → 现单位合作者 → 跨机构/工业合作 → 圈层总结
```

## 注意事项

- OpenAlex 常将同名不同人合并——如果论文时间跨度或方向不合理，提醒用户。
- 仅展示公开学术信息，不输出私人联系方式。
- `scripts/query_scholar_network.py` 可一键跑完 API 部分流程，但结果仍需搜索验证。
