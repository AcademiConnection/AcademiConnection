---
name: lab-profile
description: Deep-dive profile of a single research lab/group. Query the lab's PIs, all students (current + alumni), each member's publications, research directions, internships, collaborations, awards, and alumni career paths. Also discover inter-lab collaborations and PI-to-PI relationships. Trigger when the user asks to profile a specific lab, investigate a research group's composition, or wants detailed info about every member of a lab.
---

# Lab Profile — 实验室全景画像

对单个实验室进行深度画像：负责人、全部成员、每人的论文/方向/实习/合作/荣誉/去向，以及实验室间合作关系。

## 核心原则

- **搜索驱动。** 实验室信息高度依赖官网、个人主页、LinkedIn、新闻稿等非结构化来源，必须以 `web_search` 为主。
- **逐人展开。** 实验室画像 = 每个成员画像的聚合。先获取成员名单，再逐一搜索。
- **关系需验证。** 合作关系、实习经历不能靠推断，必须搜索到明确来源（论文共著、主页声明、新闻报道）。

## 工作流（6 步）

### 1. 定位实验室

搜索实验室官网，确认：实验室全称、所属机构、主页URL、研究方向概述。搜索 `"<lab name>" <university>` 或 `"<PI name>" lab members`。

### 2. 获取成员名单

从官网获取完整名单（PI、副教授/博后、在读学生、已毕业Alumni）。官网信息不全时，搜索 `"<PI name>" students` 或通过 API 合作者数据反推。将成员分为：

- **PI / 教师**（教授、副教授、博后）
- **在读学生**（博士、硕士）
- **已毕业 Alumni**

### 3. PI / 教师画像

对每位老师搜索：

- 个人主页 → 研究方向、代表作、荣誉
- `"<name>" collaboration` / DBLP → 外部合作者、合作实验室
- API 拉取发表记录 → 论文数、引用、h-index
- 搜索 `"<name>" <other PI name>` → 判断与其他实验室是否有合作关系

输出：姓名、职称、方向、代表作(3-5篇)、h-index、外部核心合作者、合作实验室列表。

### 4. 学生画像（逐人）

对每位学生（在读+毕业）搜索：

- 个人主页 / Google Scholar → 论文列表、方向、引用
- `"<name>" intern` / LinkedIn → 实习经历（公司、时间）
- `"<name>" award` / `"<name>" fellowship` → 获得荣誉
- 论文合作关系 → 与实验室外哪些人/组合作
- （仅 Alumni）`"<name>" now at` / LinkedIn → 毕业去向（学术 or 工业、具体单位）

输出：姓名、入学/毕业年份、方向、论文数及代表作、实习经历、合作情况、荣誉、毕业去向。

### 5. 实验室间合作分析

汇总所有成员的外部合作信息，聚合出实验室层面的合作网络：

- 哪些外部实验室/公司与本组合作最密切？
- 合作形式是什么（联合论文、学生互访、企业实习）？
- PI 之间是否有直接合作关系？

搜索 `"<PI name>" "<other PI name>"` 验证 PI 间合作。

### 6. 输出报告

```
实验室概况（名称/机构/方向/规模）
→ PI/教师画像表
→ 在读学生画像表
→ Alumni画像表（含去向）
→ 实验室合作网络图
→ 总结与亮点
```

## 辅助工具

`scripts/query_lab_profile.py` 可批量拉取多位成员的 API 数据（论文、引用、合作者），减少手动操作。但学生实习、荣誉、去向等信息必须靠搜索获取。

## 注意事项

- 学生信息变动频繁（毕业、转组），以最新搜索结果为准。
- 实习信息可能来自 LinkedIn，注意隐私——只报告公开信息。
- 小型实验室（<10人）可逐一深入；大型实验室（>20人）先覆盖核心成员，再按用户需求扩展。
- 国内实验室的学生信息常需搜索中文（`"<中文名>" 实习`、`"<中文名>" 获奖`）。
