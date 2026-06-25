---
name: scholar-network
description: Query a scholar's complete academic connection network including coauthors, lab mates, advisors, and institutional collaborators. Use this skill whenever the user wants to find a researcher's academic relationships, collaboration graph, lab members, co-authors, advisor lineage, or academic social network. Trigger when the user mentions finding connections, collaborators, academic network, lab mates, or research group members for a specific scholar or professor.
---

# Scholar Network — 学者学术关系网络查询

查询单个学者的完整学术 connection 网络，包括合作者、导师、实验室同期成员（±1级）、跨机构合作者等。

## 工作流概述

整个查询分为 5 个阶段，依次执行：

1. **定位学者** — 通过 ORCID / 姓名 / OpenAlex ID / 个人主页确认唯一身份
2. **获取全部论文** — 拉取该学者的完整发表记录
3. **提取合作者网络** — 从论文 authorship 中构建合作者图谱
4. **追溯实验室同期成员** — 识别导师，查导师的其他学生/合作者，按机构+时间过滤同组成员
5. **整理输出** — 分层级汇总为结构化报告

## 阶段一：定位学者

学者的唯一标识有多种来源，优先级从高到低：

1. **OpenAlex ID**（如 `A5027479191`）— 直接查询，最可靠
2. **ORCID**（如 `0000-0002-1234-5678`）— 通过 `Authors()['https://orcid.org/xxxx']` 精确匹配
3. **个人主页** — 从主页提取 ORCID 或确认机构+研究方向来消歧
4. **姓名搜索** — 有重名风险，需结合机构/研究领域人工确认

当用户提供姓名时，应主动搜索其个人主页或 Google Scholar 来获取 ORCID 以消歧。使用 `web_search` 搜索 `"<scholar name>" ORCID site:orcid.org` 或 `"<scholar name>" homepage` 等。

确认后记录以下信息：

```python
scholar = {
    "name": "显示名",
    "openalex_id": "A5xxxxxxxxx",
    "orcid": "0000-xxxx-xxxx-xxxx",  # 可选
    "institutions": [...],  # 机构历史（含时间段）
    "works_count": N,
    "h_index": N,
}
```

## 阶段二：获取全部论文

使用项目中的 `OpenAlexClient` 或直接调用 pyalex：

```python
from pyalex import Works
all_works = []
for page in Works().filter(author={"id": author_id}).sort(publication_year="desc").paginate(per_page=200, n_max=500):
    all_works.extend(page)
```

对每篇论文提取：title, year, venue, cited_by_count, authorships（含 author id/name/institutions）。

## 阶段三：提取合作者网络

遍历全部论文的 authorships，构建合作者字典：

```python
coauthor_map = {}  # author_id -> {name, count, papers, institutions, years}
for work in all_works:
    for authorship in work["authorships"]:
        co_id = authorship["author"]["id"]
        # 排除目标学者自身
        # 累计合作次数、记录论文列表、机构、活跃年份
```

按合作频次降序排列。输出时分层：
- **核心合作者**（合作 ≥3 次）— 可能是导师、同实验室、长期合作方
- **一般合作者**（合作 1-2 次）— 按机构或时间分组

## 阶段四：追溯实验室同期成员

这是最关键的一步。策略如下：

### 4.1 识别导师

导师通常是合作频次最高的**资深学者**。结合以下线索判断：

- 合作频次最高（通常排前3）
- 个人主页 / 论文中明确标注 "advised by" 信息
- 该人在高校任教职（Professor / Associate Professor）
- 论文中通常为通讯作者（last author）

也可以通过 `web_search` 搜索 `"<scholar name>" "advised by"` 或查看其个人主页。

### 4.2 查询导师的合作者网络

获取导师（top N 核心合作者）的论文列表和合作者：

```python
advisor_works = []
for page in Works().filter(author={"id": advisor_id}).paginate(per_page=200, n_max=300):
    advisor_works.extend(page)

# 构建导师的合作者图谱
advisor_coauthors = {}  # 同上结构
```

### 4.3 过滤同组成员

同实验室/同组成员需要同时满足：

1. **同机构** — 其机构与目标学者的某段机构历史重叠
2. **时间重叠** — 活跃年份与目标学者在该机构的时间有交集（允许 ±1 年容差）
3. **与导师有多次合作** — `count >= 2`

```python
# 获取目标学者的机构名集合和活跃年份集合
xie_inst_names = {period["name"] for period in inst_periods}
xie_years = set()
for period in inst_periods:
    xie_years.update(range(period["start"] - 1, period["end"] + 2))  # ±1年容差

# 过滤
for co_id, co_info in advisor_coauthors.items():
    shared_inst = co_info["institutions"] & xie_inst_names
    year_overlap = co_info["years"] & xie_years
    if shared_inst and year_overlap and co_info["count"] >= 2:
        # 这是同组成员
```

### 4.4 补充：通过实验室官网

如果能找到实验室官网（`web_search` 搜索 `"<advisor name>" lab team members`），可以直接获取完整的在读学生和校友列表，这比 API 推断更准确。

## 阶段五：整理输出

最终报告结构如下：

```
## 学者基本信息
姓名、机构历史、论文数、H-index

## 一、导师
姓名、机构、合作论文数

## 二、实验室同期成员（±1级）
按入学年份排列，标注毕业去向（如有）

## 三、核心合作者（合作≥3次）
按合作频次降序，标注机构和代表性合作

## 四、现单位合作者
当前机构的合作者列表

## 五、工业界/跨机构合作者
按机构分组

## 六、connection 圈层总结
第一圈层（导师+核心）、第二圈层（同门）、第三圈层（现同事）、第四圈层（跨校/工业）
```

## 注意事项

- **重名问题**：OpenAlex 有时会将同名不同人的 profile 合并。如果发现某学者论文跨越不合理的时间跨度（如 1997 年有生物论文但 2020 年才开始计算机论文），需提醒用户可能存在 profile 合并错误。
- **Rate Limiting**：OpenAlex 免费 API 无严格限制但建议在请求间加 0.2s 延迟。如设置了 polite email（`pyalex.config.email`）可获得更好的速率。
- **数据完整性**：OpenAlex 覆盖 2.4 亿+ 论文但可能缺少部分中文期刊论文或最新预印本。
- **隐私**：输出报告时不要包含学者的私人联系方式，仅展示公开学术信息。

## 示例

**用户请求：** "帮我查一下 Yoshua Bengio 的学术网络"

**工作流执行：**

1. 搜索确认：OpenAlex ID = A5073352741, ORCID = 0000-0002-8168-6075, Mila / Université de Montréal
2. 拉取论文（~1000篇），提取合作者
3. 识别核心合作者：Aaron Courville (30+次), Ian Goodfellow (15+次), Pascal Vincent (40+次) 等
4. 追溯 Mila 同期成员：通过 Bengio 的合作网络过滤 Université de Montréal + 时间重叠的学者
5. 输出分层报告

**用户请求：** "查一下这个教授的 connections：https://some-professor.github.io/"

**工作流执行：**

1. 访问主页，提取姓名 + ORCID + 机构信息
2. 用 ORCID 在 OpenAlex 精确匹配
3. 后续同上

## 依赖

本 skill 依赖以下工具/库（通常在 AcademiConnection 项目中已配置）：

- `pyalex` — OpenAlex Python SDK
- `web_search` / `web_fetch` — 用于搜索个人主页和实验室网站
- Python 3.10+

如果当前工作区不是 AcademiConnection 项目，脚本 `scripts/query_scholar_network.py` 可以独立运行（会自动安装 pyalex）。
