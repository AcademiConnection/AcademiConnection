"""
科研合作网络构建器

从 OpenAlex 或 Semantic Scholar 数据构建合作关系网络图谱。
"""

from typing import Optional
from collections import defaultdict


class NetworkBuilder:
    """科研合作网络构建器"""

    def __init__(self):
        """初始化网络构建器"""
        self.nodes: dict[str, dict] = {}  # node_id -> node_attrs
        self.edges: dict[tuple[str, str], dict] = {}  # (src, dst) -> edge_attrs

    def add_author_node(
        self,
        author_id: str,
        name: str,
        institution: Optional[str] = None,
        h_index: Optional[int] = None,
        paper_count: Optional[int] = None,
        **kwargs,
    ):
        """
        添加作者节点。

        Args:
            author_id: 作者 ID
            name: 作者姓名
            institution: 所属机构
            h_index: h 指数
            paper_count: 论文总数
        """
        self.nodes[author_id] = {
            "id": author_id,
            "name": name,
            "type": "author",
            "institution": institution,
            "h_index": h_index,
            "paper_count": paper_count,
            **kwargs,
        }

    def add_collaboration_edge(
        self,
        author1_id: str,
        author2_id: str,
        weight: int = 1,
        papers: Optional[list[str]] = None,
    ):
        """
        添加合作关系边。

        Args:
            author1_id: 作者 1 的 ID
            author2_id: 作者 2 的 ID
            weight: 合作次数/权重
            papers: 合作论文 ID 列表
        """
        # 确保无向边的唯一性（较小 ID 在前）
        edge_key = tuple(sorted([author1_id, author2_id]))

        if edge_key in self.edges:
            self.edges[edge_key]["weight"] += weight
            if papers:
                self.edges[edge_key].setdefault("papers", []).extend(papers)
        else:
            self.edges[edge_key] = {
                "source": edge_key[0],
                "target": edge_key[1],
                "weight": weight,
                "papers": papers or [],
            }

    def build_from_works(self, works: list[dict], source: str = "openalex"):
        """
        从论文列表构建合作网络。

        Args:
            works: 论文数据列表（来自 OpenAlex 或 Semantic Scholar）
            source: 数据来源标识，"openalex" 或 "s2"
        """
        for work in works:
            if source == "openalex":
                self._process_openalex_work(work)
            elif source == "s2":
                self._process_s2_work(work)

    def _process_openalex_work(self, work: dict):
        """处理 OpenAlex 格式的论文数据"""
        authorships = work.get("authorships", [])
        work_id = work.get("id", "")

        authors_in_paper = []
        for authorship in authorships:
            author_info = authorship.get("author", {})
            author_id = author_info.get("id", "")
            author_name = author_info.get("display_name", "")

            if not author_id:
                continue

            # 提取机构信息
            institutions = authorship.get("institutions", [])
            inst_name = institutions[0].get("display_name", "") if institutions else None

            # 添加节点
            if author_id not in self.nodes:
                self.add_author_node(
                    author_id=author_id,
                    name=author_name,
                    institution=inst_name,
                )

            authors_in_paper.append(author_id)

        # 添加合作边（所有共著者两两之间）
        for i in range(len(authors_in_paper)):
            for j in range(i + 1, len(authors_in_paper)):
                self.add_collaboration_edge(
                    authors_in_paper[i],
                    authors_in_paper[j],
                    weight=1,
                    papers=[work_id],
                )

    def _process_s2_work(self, work: dict):
        """处理 Semantic Scholar 格式的论文数据"""
        authors = work.get("authors", [])
        paper_id = work.get("paperId", "")

        authors_in_paper = []
        for author in authors:
            author_id = author.get("authorId")
            author_name = author.get("name", "")

            if not author_id:
                continue

            if author_id not in self.nodes:
                self.add_author_node(
                    author_id=author_id,
                    name=author_name,
                )

            authors_in_paper.append(author_id)

        # 添加合作边
        for i in range(len(authors_in_paper)):
            for j in range(i + 1, len(authors_in_paper)):
                self.add_collaboration_edge(
                    authors_in_paper[i],
                    authors_in_paper[j],
                    weight=1,
                    papers=[paper_id],
                )

    def get_statistics(self) -> dict:
        """获取网络统计信息"""
        if not self.edges:
            return {
                "num_nodes": len(self.nodes),
                "num_edges": 0,
                "avg_weight": 0,
                "max_weight": 0,
            }

        weights = [e["weight"] for e in self.edges.values()]
        return {
            "num_nodes": len(self.nodes),
            "num_edges": len(self.edges),
            "avg_weight": sum(weights) / len(weights) if weights else 0,
            "max_weight": max(weights) if weights else 0,
            "top_collaborators": self._get_top_collaborators(10),
        }

    def _get_top_collaborators(self, n: int = 10) -> list[dict]:
        """获取合作最频繁的作者对"""
        sorted_edges = sorted(
            self.edges.values(), key=lambda x: x["weight"], reverse=True
        )[:n]

        result = []
        for edge in sorted_edges:
            src_name = self.nodes.get(edge["source"], {}).get("name", edge["source"])
            tgt_name = self.nodes.get(edge["target"], {}).get("name", edge["target"])
            result.append({
                "author1": src_name,
                "author2": tgt_name,
                "collaborations": edge["weight"],
            })
        return result

    def to_networkx(self):
        """
        转换为 NetworkX 图对象。

        Returns:
            networkx.Graph 对象
        """
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("请安装 networkx: pip install networkx")

        G = nx.Graph()

        for node_id, attrs in self.nodes.items():
            G.add_node(node_id, **attrs)

        for edge_key, attrs in self.edges.items():
            G.add_edge(edge_key[0], edge_key[1], **attrs)

        return G

    def to_dict(self) -> dict:
        """导出为字典格式（方便序列化）"""
        return {
            "nodes": list(self.nodes.values()),
            "edges": list(self.edges.values()),
            "statistics": self.get_statistics(),
        }
