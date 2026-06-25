---
name: scholar-network
description: Query a scholar's complete academic connection network including coauthors, lab mates, advisors, and institutional collaborators. Use this skill whenever the user wants to find a researcher's academic relationships, collaboration graph, lab members, co-authors, advisor lineage, or academic social network. Trigger when the user mentions finding connections, collaborators, academic network, lab mates, or research group members for a specific scholar or professor.
---

# Scholar Network — 学者学术关系网络查询

查询单个学者的完整学术 connection 网络，包括合作者、导师、实验室同期成员（±1级）、跨机构合作者等。

## 核心原则

**多源交叉验证，不依赖单一工具。** API 工具（如 OpenAlex/pyalex）的数据可能滞后、不完整、或存在 profile 合并错误。在每个阶段都应主动使用 `web_search` 进行 Google 搜索来补充和验证信息。具体而言：

- API 返回的结果作为 **初始线索**，而非最终结论
- 对每一个关键发现（导师关系、实验室归属、机构变动），都通过网页搜索进行交叉确认
- 当 API 数据与网页信息冲突时，优先信任一手来源（个人主页、实验室官网、学校公告）
- 对中文学者尤其需要 Google 搜索补充，因为中文期刊和国内数据在 OpenAlex 中覆盖不全

## 工作流概述

整个查询分为 5 个阶段，依次执行：

1. **定位学者** — 多渠道搜索确认唯一身份
2. **获取全部论文与合作者** — API + Google Scholar 结合
3. **识别导师与核心关系** — 搜索验证
4. **追溯实验室同期成员** — 实验室官网为主，API 推断为辅
5. **整理输出** — 分层级汇总为结构化报告

## 阶段一：定位学者

### 搜索策略（按可靠性排序）

1. **Google 搜索个人主页** — `web_search` 搜 `"<name>" homepage` 或 `"<name>" site:github.io`。个人主页通常有 ORCID、研究方向、导师信息、发表列表，是最可靠的一手来源。
2. **搜索大学官方页面** — 搜 `"<name>" <university> faculty` 或中文 `"<name>" 学院 教师`。官方页面有教育背景、研究方向。
3. **Google Scholar** — 搜 `"<name>" site:scholar.google.com`，可确认发表记录和机构。
4. **ORCID** — 如主页有 ORCID，记录下来用于后续 API 查询。
5. **OpenAlex / API 查询** — 最后用 API 做结构化数据拉取，但注意验证返回结果是否与搜索到的信息一致。

### 消歧

遇到常见中文名字（如 Wei Zhang, Jing Wang）时，必须结合机构、研究方向、时间线来确认。单纯依赖 API 搜索姓名极不可靠。

确认后记录：姓名、机构历史（含时间段）、研究方向、ORCID（如有）、OpenAlex ID（如有）。

## 阶段二：获取论文与合作者

### 主路径：API 批量拉取

如果项目中有 pyalex 可用，通过 API 批量获取论文和 authorship 数据：

```python
from pyalex import Works
all_works = []
for page in Works().filter(author={"id": author_id}).sort(publication_year="desc").paginate(per_page=200, n_max=500):
    all_works.extend(page)
```

从每篇论文的 authorships 字段提取合作者，构建合作者字典（含合作次数、论文列表、机构、年份）。

### 补充路径：Google 搜索验证

API 结果拿到后，**必须**通过搜索补充验证：

- `web_search` 搜索 `"<scholar name>" Google Scholar` 对比论文数是否接近
- 如果 API 返回的论文数明显偏少（如学者主页标注 50 篇但 API 只返回 20 篇），说明数据不全，需通过 Google Scholar 或 DBLP 补充
- 搜索 `"<scholar name>" DBLP` 对计算机领域学者特别有用
- 对于最近 1-2 年的论文，API 可能未收录，通过 `"<scholar name>" 2025 paper` 搜索补充

### 处理 API 不可用的情况

如果 pyalex 未安装或 API 不可达，完全依赖搜索也能完成任务：

- Google Scholar 页面可获取论文列表和合作者
- DBLP 可获取计算机领域的完整发表记录
- 个人主页的 publications 列表往往最完整

## 阶段三：识别导师与核心关系

### 判断导师的策略（多源结合）

**首选：直接搜索确认**

- `web_search` 搜 `"<scholar name>" "advised by"` 或 `"<scholar name>" advisor`
- 搜 `"<scholar name>" PhD thesis` — 博士论文通常标注导师
- 看个人主页的 Bio 或 About 页面，通常会写 "I am advised by Prof. X"
- 中文学者搜 `"<name>" 导师` 或看学校培养方案

**辅助：从合作数据推断**

- 合作频次最高的资深学者（通常排前 3）大概率是导师
- 合作时间跨越整个博士期间（如 2019-2024 持续合作）
- 通常为论文的最后一位作者（通讯作者）

**验证：交叉确认**

找到疑似导师后，搜索该导师的页面确认：`"<advisor name>" students` 或 `"<advisor name>" lab members`。如果导师的页面列出了目标学者，关系即确认。

### 核心合作者分类

按合作频次和性质分为：
- **导师**（合作最频繁的资深教授）
- **同实验室同学**（同机构、同时期、同导师）
- **工业界合作者**（来自企业，通常是联合项目）
- **跨校合作者**（不同机构的学者）

## 阶段四：追溯实验室同期成员

这一步信息来源的可靠性排序很重要：

### 4.1 最佳来源：实验室官网

`web_search` 搜索 `"<advisor name>" lab team` 或 `"<advisor name>" research group members`。大部分活跃的研究组都有官网，会列出当前学生和校友（Alumni）。这是最准确、最完整的来源。

从实验室官网可以直接获取：
- 在读学生列表（含入学年份）
- 校友列表（含毕业年份和去向）
- 博士后列表

### 4.2 辅助来源：API 推断

当实验室官网不可用时，通过 API 数据推断同期成员。逻辑是：查询导师的全部合作者，筛选同时满足以下条件的人：

1. **同机构** — 其机构与目标学者在该校的时期重叠
2. **时间重叠** — 活跃年份有交集（±1 年容差）
3. **与导师有多次合作** — 合作次数 ≥ 2

这种推断方式会有噪音（比如会混入导师的其他类型合作者），但和官网信息对比后可以过滤。

### 4.3 补充搜索

- 搜索 `"<lab name>" "PhD student"` 可能找到新闻、获奖公告中提到的组员
- 搜索目标学者的论文合作者主页，他们的 Bio 中可能提到共同的实验室
- LinkedIn 搜索（如果可访问）也是发现同组成员的渠道

## 阶段五：整理输出

最终报告结构：

```
## 学者基本信息
姓名、机构历史、研究方向、论文数、H-index

## 一、导师
姓名、机构、关系确认来源（主页/论文/搜索）

## 二、实验室同期成员（±1级）
按入学年份排列，标注毕业去向（如有）
信息来源标注（官网/推断）

## 三、核心合作者（合作≥3次）
按合作频次降序，标注机构和代表性合作

## 四、现单位合作者
当前机构的合作者列表

## 五、工业界/跨机构合作者
按机构分组

## 六、connection 圈层总结
第一圈层（导师+核心）→ 第二圈层（同门）→ 第三圈层（现同事）→ 第四圈层（跨校/工业）
```

## 注意事项

- **重名/Profile 合并**：OpenAlex 经常将同名不同人合并。如果发现论文跨越不合理的时间跨度或研究方向突变，提醒用户并通过搜索验证。
- **数据时效性**：API 数据通常滞后数周到数月。最近的论文和人事变动应通过搜索获取。
- **中文学者特殊处理**：中文期刊、国内会议在 OpenAlex 覆盖不全。对中文学者应额外搜索 CNKI、万方、或 Google Scholar 中文页面。
- **隐私**：仅展示公开学术信息，不输出私人联系方式。

## 示例

**用户请求：** "帮我查一下 Yoshua Bengio 的学术网络"

**工作流执行：**

1. `web_search` 搜索 "Yoshua Bengio homepage" → 找到 yoshuabengio.org，确认 Mila / Université de Montréal
2. 搜索 "Yoshua Bengio lab members Mila" → 找到 Mila 官网团队页面
3. 用 OpenAlex API 拉取论文列表，提取合作频次 top 20
4. 从 Mila 官网直接获取学生和校友列表，与 API 推断结果交叉验证
5. 对核心合作者逐一搜索确认角色（学生/同事/跨校合作）
6. 输出分层报告，标注每条信息的来源

**用户请求：** "查一下这个教授的 connections：https://some-professor.github.io/"

**工作流执行：**

1. `web_fetch` 访问主页，提取姓名、机构、ORCID、研究方向、导师信息
2. 从主页 Publications 列表获取论文和合作者第一手信息
3. 搜索该教授的实验室/研究组页面
4. 如有 ORCID/OpenAlex ID，用 API 补充批量数据
5. 搜索确认关键关系后输出报告

## 工具优先级

执行时遵循以下优先级：

1. **`web_search` (Google 搜索)** — 发现信息、交叉验证、获取最新动态
2. **`web_fetch` (访问网页)** — 获取个人主页/实验室官网/学校页面的详细内容
3. **pyalex / OpenAlex API** — 批量结构化数据拉取（论文列表、合作者统计）
4. **`scripts/query_scholar_network.py`** — 当需要一次性跑完全流程时可用，但其结果仍需搜索验证

记住：API 是加速器，搜索是验证器。两者结合才能产出可靠的结果。
