# 推荐系统存储（Embedding Table Infrastructure）领域课题组调研报告

> 生成时间：2025-06-25  
> 调研范围：2020–2025年，CCF-A级别会议/期刊  
> 关键词：embedding table, recommendation storage, parameter server, DLRM infrastructure

---

## 一、领域概述

推荐系统是互联网公司最核心的AI应用之一，其模型参数量已达TB级别（以embedding table为主）。与CV/NLP模型不同，推荐模型的参数主要是稀疏的embedding表，带来独特的存储、通信和服务挑战。本领域关注：

- **训练阶段**：如何高效存储和更新TB级embedding表（分布式训练、异构存储层次）
- **服务阶段**：如何低延迟地查询和更新在线serving的embedding参数
- **同步阶段**：如何在训练和推理之间快速同步模型更新

---

## 二、主要课题组详情

### 1. 清华大学存储研究组 (THU Storage Lab)

| 项目 | 信息 |
|------|------|
| **PI** | 陆游游（长聘副教授）、舒继武（长聘教授、IEEE Fellow） |
| **机构** | 清华大学计算机系，高性能计算研究所 |
| **主页** | https://storage.cs.tsinghua.edu.cn |
| **方向定位** | 从存储系统视角解决推荐系统的内存/存储瓶颈 |

**核心学生：**

- **谢旻晖**（博士2019-2024，现中国人民大学讲师）— 该方向绝对核心，6篇顶会第一/核心作者
- **范如文**（在读博士2023级）— MaxEmbed第一作者
- **蒋浩迪**（在读博士2024级）— MaxEmbed、GustANN合著
- **曾少勋**（在读博士2021级）— Medusa第一作者，FAST'26杰出技术贡献奖
- **汪庆**（已毕业，现南京大学教职）— Fleche、PetPS合著

**CCF-A论文（Embedding/推荐存储方向）：**

| 年份 | 会议 | 论文 | 引用 |
|------|------|------|------|
| 2020 | SC | Kraken: Memory-Efficient Continual Learning for Large-Scale Real-Time Recommendations | ~100+ |
| 2022 | EuroSys | Fleche: An Efficient GPU Embedding Cache for Personalized Recommendations | ~30+ |
| 2023 | ASPLOS | Mobius: Fine Tuning Large-Scale Models on Commodity GPU Servers | ~20+ |
| 2023 | VLDB | PetPS: Supporting Huge Embedding Models with Persistent Memory | 11 |
| 2024 | ASPLOS | MaxEmbed: Maximizing SSD Bandwidth Utilization for Huge Embedding Models Serving | ~5+ |
| 2025 | ASPLOS | Medusa: Accelerating Serverless LLM Inference with Materialization | New |

**技术脉络**：训练(Kraken) → GPU缓存(Fleche) → 异构训练(Mobius) → 持久内存服务(PetPS) → SSD服务(MaxEmbed) → LLM推理(Medusa)

**产业合作**：快手（Kraken/PetPS工业部署）

---

### 2. 北京大学 PKU-DAIR

| 项目 | 信息 |
|------|------|
| **PI** | 崔斌（教授、IEEE Fellow、CCF Fellow、长江学者） |
| **机构** | 北京大学计算机学院，数据与智能实验室 |
| **主页** | https://pkudair.github.io/ |
| **方向定位** | 分布式ML系统、Embedding训练优化 |

**核心学生：**

- **苗旭鹏**（博士毕业，现北京大学助理教授）— HET第一作者，多篇OSDI/SOSP/ASPLOS
- **张海林**（博士2020-2025，现小米MiMo团队）— HET共同一作、CAFE第一作者，优博论文
- **符芳诚** — 分布式训练核心，SOSP'24
- **聂小楠** — HET合著，Angel-PTM (VLDB'23)

**CCF-A论文（Embedding/推荐方向）：**

| 年份 | 会议 | 论文 | 备注 |
|------|------|------|------|
| 2022 | VLDB | HET: Scaling out Huge Embedding Model Training via Cache-enabled Distributed Framework | **Best Paper** |
| 2022 | SIGMOD | HET-GMP: A Graph-based System Approach to Scaling Large Embedding Model Training | |
| 2024 | SIGMOD | CAFE: Towards Compact, Adaptive, and Fast Embedding for Large-scale Recommendation Models | **Best Artifact** |
| 2024 | VLDB | Experimental Analysis of Large-scale Learnable Vector Storage Compression | |
| 2025 | SIGMOD | PQCache: Product Quantization-based KVCache for Long Context LLM Inference | |

**旗舰项目**：Hetu（河图）分布式深度学习系统，GitHub开源

**产业合作**：腾讯（HET联合研发）、百川智能、小米

---

### 3. 腾讯微信 + 爱丁堡大学

| 项目 | 信息 |
|------|------|
| **学术PI** | Luo Mai（麦骆，爱丁堡大学Reader/副教授） |
| **工业负责人** | 腾讯微信推荐团队 |
| **方向定位** | 大规模推荐模型在线参数同步 |

**核心贡献者：**

- **司马驰骏 (Chijun Sima)** — 腾讯微信Senior SDE，Ekko第一作者
- **符尧 (Yao Fu)** — 共同一作

**代表作：**

| 年份 | 会议 | 论文 | 备注 |
|------|------|------|------|
| 2022 | OSDI | Ekko: A Large-Scale Deep Learning Recommender System with Low-Latency Model Update | 腾讯首篇OSDI一作 |

**核心贡献**：将40TB推荐模型的参数同步延迟从数十分钟降低至2.4秒，部署于微信视频号、看一看等。

---

### 4. Meta/Facebook DLRM基础设施

| 项目 | 信息 |
|------|------|
| **核心负责人** | Carole-Jean Wu（Meta FAIR Systems团队负责人） |
| **学术合作** | Stanford (Kozyrakis), CMU (Zhihao Jia), Harvard (Udit Gupta) |
| **方向定位** | 工业级推荐模型训练/推理基础设施 |

**关键研究者：**

- **Dheevatsa Mudigere** — Neo系统第一作者
- **Geet Sethi** — RecShard第一作者（Stanford博士生）
- **Bilge Acun** — Meta/FAIR Research Scientist
- **Udit Gupta** — DeepRecSys第一作者（Harvard博士，导师David Brooks）

**CCF-A论文：**

| 年份 | 会议 | 论文 |
|------|------|------|
| 2020 | ISCA | DeepRecSys: A System for Optimizing End-To-End At-Scale Neural Recommendation Inference |
| 2021 | HPCA | Understanding Training Efficiency of Deep Learning Recommendation Models at Scale |
| 2022 | ASPLOS | RecShard: Statistical Feature-Based Memory Optimization for Industry-Scale Neural Recommendation |
| 2022 | ISCA | Neo: Software-Hardware Co-design for Fast and Scalable Training of Deep Learning Recommendation Models |
| 2023 | ISCA | MTrainS: Improving DLRM Training Efficiency Using Heterogeneous Memories |
| 2023 | ISCA | MTIA: First Generation Silicon Targeting Meta's Recommendation Systems |

**特色**：业界最大规模推荐系统（消耗Meta超50%训练算力），Neo首创4D并行。

---

### 5. University of Michigan + Meta — AdaEmbed

| 项目 | 信息 |
|------|------|
| **学术PI** | Fan Lai（赖凡，现UIUC助理教授）、Mosharaf Chowdhury（UMich教授） |
| **工业方** | Meta AI |
| **方向定位** | 自适应Embedding表剪枝 |

**代表作：**

| 年份 | 会议 | 论文 |
|------|------|------|
| 2023 | OSDI | AdaEmbed: Adaptive Embedding for Large-Scale Recommendation Models |

**核心贡献**：训练中自动剪枝embedding行，动态优化每个特征的embedding大小。

---

### 6. UChicago UCARE — EVStore

| 项目 | 信息 |
|------|------|
| **PI** | Haryadi S. Gunawi（UChicago教授） |
| **方向定位** | 面向推荐系统embedding的存储/缓存层 |

**核心贡献者：**

- **Daniar H. Kurniawan** — 第一作者，UChicago博士生

**代表作：**

| 年份 | 会议 | 论文 |
|------|------|------|
| 2023 | ASPLOS | EVStore: Storage and Caching Capabilities for Scaling Embedding Tables in Deep Recommendation Systems |

**核心贡献**：通过缓存替换策略+低精度存储+surrogate caching，实现内存减少94%、吞吐提升4x。

---

## 三、对比总结

| 课题组 | PI | 机构 | CCF-A数量(2020-2025) | 核心方向 | 产业落地 |
|--------|-----|------|---------------------|----------|----------|
| THU Storage | 陆游游/舒继武 | 清华 | 6篇 | 全栈(训练→服务) | 快手 |
| PKU-DAIR | 崔斌 | 北大 | 5篇 | 训练系统+压缩 | 腾讯/小米 |
| Tencent+Edinburgh | Luo Mai | 微信/爱丁堡 | 1篇 | 在线同步 | 微信视频号 |
| Meta | Carole-Jean Wu | Meta | 6篇 | 端到端训练/推理 | Meta全球 |
| UMich+Meta | Fan Lai | UIUC/UMich | 1篇 | Embedding剪枝 | Meta |
| UChicago UCARE | Gunawi | UChicago | 1篇 | 存储缓存 | — |

---

## 四、趋势观察

1. **从训练到服务的全栈研究**：清华存储组最具系统性，从Kraken(训练)到MaxEmbed(服务)覆盖完整链路
2. **存储层次化**：从DRAM→PM(PetPS)→SSD(MaxEmbed)→远端存储，逐步下推embedding数据
3. **自适应压缩**：CAFE的热度感知、AdaEmbed的自动剪枝代表embedding压缩的主流思路
4. **工业驱动学术**：Meta和腾讯的论文直接来自生产环境需求
5. **中国团队主导**：该细分领域中，清华和北大占据学术研究的核心地位

---

## 五、辅助工具使用说明

本报告使用 `scripts/survey_domain_groups.py` 辅助生成，用法示例：

```bash
# 按关键词批量搜索
python scripts/survey_domain_groups.py \
    --keywords "embedding table" "recommendation storage" "parameter server" \
    --venues OSDI ASPLOS VLDB SIGMOD SC EuroSys ISCA HPCA \
    --years 5 --output reports/output.json

# 按特定PI查询
python scripts/survey_domain_groups.py \
    --author "Youyou Lu" \
    --venues OSDI ASPLOS VLDB SIGMOD EuroSys SC FAST \
    --years 6

# 查询北大崔斌老师
python scripts/survey_domain_groups.py \
    --author "Bin Cui" \
    --venues VLDB SIGMOD OSDI SOSP ASPLOS \
    --years 5
```
