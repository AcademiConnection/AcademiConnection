"""
学者关系查询工具

查询两位学者之间的学术关系，包括：
1. 直接合作（共著论文）
2. 共同合作者（间接关系）
3. 引用关系
4. 同机构关系
"""

import sys
import os
from typing import Optional
from dataclasses import dataclass, field

# 添加 submodule 路径
_PYALEX_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "third_party", "pyalex"
)
if os.path.isdir(_PYALEX_PATH) and _PYALEX_PATH not in sys.path:
    sys.path.insert(0, os.path.abspath(_PYALEX_PATH))

from pyalex import Works, Authors

from .openalex_client import OpenAlexClient


@dataclass
class ScholarProfile:
    """学者资料"""
    openalex_id: str
    name: str
    institutions: list[str] = field(default_factory=list)
    works_count: int = 0
    cited_by_count: int = 0
    orcid: Optional[str] = None


@dataclass
class RelationshipResult:
    """关系查询结果"""
    scholar_a: ScholarProfile
    scholar_b: ScholarProfile
    direct_collaborations: list[dict] = field(default_factory=list)
    common_coauthors: list[dict] = field(default_factory=list)
    citation_links: list[dict] = field(default_factory=list)
    shared_institutions: list[str] = field(default_factory=list)
    relationship_summary: str = ""


class RelationshipFinder:
    """学者关系查询器"""

    def __init__(self, client: Optional[OpenAlexClient] = None):
        self.client = client or OpenAlexClient()

    def find_scholar(
        self,
        name: Optional[str] = None,
        orcid: Optional[str] = None,
        openalex_id: Optional[str] = None,
    ) -> Optional[ScholarProfile]:
        """
        查找学者资料。优先使用 ORCID 或 OpenAlex ID 精确匹配。

        Args:
            name: 学者姓名（用于搜索）
            orcid: ORCID（精确匹配）
            openalex_id: OpenAlex ID（精确匹配）

        Returns:
            ScholarProfile 或 None
        """
        author_data = None

        if openalex_id:
            try:
                author_data = Authors()[openalex_id]
            except Exception:
                pass

        if not author_data and orcid:
            try:
                orcid_url = orcid if orcid.startswith("http") else f"https://orcid.org/{orcid}"
                author_data = Authors()[orcid_url]
            except Exception:
                pass

        if not author_data and name:
            results = self.client.search_authors(name, max_results=5)
            if results:
                # 取第一个结果
                author_data = results[0]

        if not author_data:
            return None

        insts = author_data.get("last_known_institutions") or []
        return ScholarProfile(
            openalex_id=author_data.get("id", "").replace("https://openalex.org/", ""),
            name=author_data.get("display_name", ""),
            institutions=[i.get("display_name", "") for i in insts],
            works_count=author_data.get("works_count", 0),
            cited_by_count=author_data.get("cited_by_count", 0),
            orcid=author_data.get("orcid"),
        )

    def find_relationship(
        self,
        scholar_a: ScholarProfile,
        scholar_b: ScholarProfile,
        max_works: int = 200,
    ) -> RelationshipResult:
        """
        查询两位学者之间的学术关系。

        Args:
            scholar_a: 学者 A 的资料
            scholar_b: 学者 B 的资料
            max_works: 每位学者检索的最大论文数

        Returns:
            RelationshipResult 包含所有关系信息
        """
        result = RelationshipResult(
            scholar_a=scholar_a,
            scholar_b=scholar_b,
        )

        # 1. 检查直接合作（共著论文）
        result.direct_collaborations = self._find_coauthored_papers(
            scholar_a.openalex_id, scholar_b.openalex_id
        )

        # 2. 查找共同合作者
        result.common_coauthors = self._find_common_coauthors(
            scholar_a.openalex_id, scholar_b.openalex_id, max_works
        )

        # 3. 检查引用关系
        result.citation_links = self._find_citation_links(
            scholar_a.openalex_id, scholar_b.openalex_id
        )

        # 4. 检查同机构关系
        result.shared_institutions = self._find_shared_institutions(
            scholar_a, scholar_b
        )

        # 5. 生成总结
        result.relationship_summary = self._generate_summary(result)

        return result

    def _find_coauthored_papers(self, id_a: str, id_b: str) -> list[dict]:
        """查找两人共著的论文"""
        try:
            results = []
            for page in Works().filter(
                author={"id": id_a}
            ).filter(
                author={"id": id_b}
            ).paginate(per_page=25, n_max=100):
                results.extend(page)

            papers = []
            for w in results:
                papers.append({
                    "title": w.get("title", ""),
                    "year": w.get("publication_year"),
                    "id": w.get("id", ""),
                    "cited_by_count": w.get("cited_by_count", 0),
                    "authors": [
                        a.get("author", {}).get("display_name", "")
                        for a in w.get("authorships", [])
                    ],
                })
            return papers
        except Exception:
            return []

    def _find_common_coauthors(
        self, id_a: str, id_b: str, max_works: int = 200
    ) -> list[dict]:
        """查找共同合作者"""
        coauthors_a = self.client.get_coauthors(id_a, max_works=max_works)
        coauthors_b = self.client.get_coauthors(id_b, max_works=max_works)

        ids_a = {c["author_id"]: c for c in coauthors_a}
        ids_b = {c["author_id"]: c for c in coauthors_b}

        common_ids = set(ids_a.keys()) & set(ids_b.keys())

        common = []
        for cid in common_ids:
            info_a = ids_a[cid]
            info_b = ids_b[cid]
            common.append({
                "author_id": cid,
                "name": info_a["name"],
                "collaborations_with_a": info_a["collaboration_count"],
                "collaborations_with_b": info_b["collaboration_count"],
            })

        return sorted(
            common,
            key=lambda x: x["collaborations_with_a"] + x["collaborations_with_b"],
            reverse=True,
        )

    def _find_citation_links(self, id_a: str, id_b: str) -> list[dict]:
        """查找引用关系（A 引用 B 或 B 引用 A）"""
        links = []

        # 获取 A 的论文
        works_a = self.client.get_author_works(id_a, max_results=50)

        for w in works_a[:20]:
            work_id = w.get("id", "").replace("https://openalex.org/", "")
            if not work_id:
                continue
            try:
                # 检查 B 的论文是否引用了 A 的这篇
                citing = []
                for page in Works().filter(cites=work_id).filter(
                    author={"id": id_b}
                ).paginate(per_page=10, n_max=10):
                    citing.extend(page)

                for c in citing:
                    links.append({
                        "type": "B_cites_A",
                        "cited_paper": w.get("title", ""),
                        "cited_year": w.get("publication_year"),
                        "citing_paper": c.get("title", ""),
                        "citing_year": c.get("publication_year"),
                    })
            except Exception:
                continue

        return links

    def _find_shared_institutions(
        self, scholar_a: ScholarProfile, scholar_b: ScholarProfile
    ) -> list[str]:
        """查找共同机构"""
        set_a = set(scholar_a.institutions)
        set_b = set(scholar_b.institutions)
        return list(set_a & set_b)

    def _generate_summary(self, result: RelationshipResult) -> str:
        """生成关系总结"""
        parts = []
        a_name = result.scholar_a.name
        b_name = result.scholar_b.name

        if result.direct_collaborations:
            n = len(result.direct_collaborations)
            parts.append(f"直接合作：{a_name} 和 {b_name} 共发表 {n} 篇论文")

        if result.common_coauthors:
            n = len(result.common_coauthors)
            top3 = ", ".join(c["name"] for c in result.common_coauthors[:3])
            parts.append(f"共同合作者：{n} 位（如 {top3}）")

        if result.citation_links:
            n = len(result.citation_links)
            parts.append(f"引用关系：存在 {n} 条引用链接")

        if result.shared_institutions:
            insts = ", ".join(result.shared_institutions)
            parts.append(f"同机构：{insts}")

        if not parts:
            parts.append(
                f"未发现 {a_name} 和 {b_name} 之间的直接学术关系"
                f"（无共著论文、无共同合作者、无引用关系、无同机构）"
            )

        return "\n".join(parts)

    def print_report(self, result: RelationshipResult):
        """打印关系查询报告"""
        a = result.scholar_a
        b = result.scholar_b

        print("=" * 70)
        print("学术关系查询报告")
        print("=" * 70)
        print(f"\n学者 A: {a.name}")
        print(f"  机构: {', '.join(a.institutions) if a.institutions else 'N/A'}")
        print(f"  论文数: {a.works_count} | 被引: {a.cited_by_count}")
        print(f"  OpenAlex ID: {a.openalex_id}")

        print(f"\n学者 B: {b.name}")
        print(f"  机构: {', '.join(b.institutions) if b.institutions else 'N/A'}")
        print(f"  论文数: {b.works_count} | 被引: {b.cited_by_count}")
        print(f"  OpenAlex ID: {b.openalex_id}")

        print(f"\n{'─' * 70}")
        print("关系总结:")
        print(f"{'─' * 70}")
        print(result.relationship_summary)

        if result.direct_collaborations:
            print(f"\n{'─' * 70}")
            print(f"共著论文 ({len(result.direct_collaborations)} 篇):")
            print(f"{'─' * 70}")
            for p in result.direct_collaborations:
                print(f"  [{p['year']}] {p['title']}")
                print(f"       引用: {p['cited_by_count']}")

        if result.common_coauthors:
            print(f"\n{'─' * 70}")
            print(f"共同合作者 ({len(result.common_coauthors)} 位):")
            print(f"{'─' * 70}")
            for c in result.common_coauthors[:15]:
                print(
                    f"  {c['name']}: "
                    f"与 {a.name} 合作 {c['collaborations_with_a']} 次, "
                    f"与 {b.name} 合作 {c['collaborations_with_b']} 次"
                )

        if result.citation_links:
            print(f"\n{'─' * 70}")
            print(f"引用关系 ({len(result.citation_links)} 条):")
            print(f"{'─' * 70}")
            for link in result.citation_links[:10]:
                if link["type"] == "B_cites_A":
                    print(f"  {b.name} [{link['citing_year']}] \"{link['citing_paper']}\"")
                    print(f"    → 引用了 {a.name} [{link['cited_year']}] \"{link['cited_paper']}\"")

        if result.shared_institutions:
            print(f"\n{'─' * 70}")
            print(f"共同机构: {', '.join(result.shared_institutions)}")

        print("\n" + "=" * 70)
