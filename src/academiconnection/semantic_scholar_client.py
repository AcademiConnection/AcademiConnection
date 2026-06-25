"""
Semantic Scholar API 客户端封装

基于 semanticscholar 库，提供论文搜索、作者查询、引用关系和合作关系提取。
"""

import os
import sys
from typing import Optional

# 将 submodule 路径加入 sys.path
_S2_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "third_party", "semanticscholar"
)
if os.path.isdir(_S2_PATH) and _S2_PATH not in sys.path:
    sys.path.insert(0, os.path.abspath(_S2_PATH))

from semanticscholar import SemanticScholar


class SemanticScholarClient:
    """Semantic Scholar API 统一客户端"""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        """
        初始化 Semantic Scholar 客户端。

        Args:
            api_key: S2 API key（可选，无 key 时有速率限制）。
                     若未提供，从环境变量 S2_API_KEY 读取。
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key or os.getenv("S2_API_KEY")
        self.sch = SemanticScholar(api_key=self.api_key, timeout=timeout)

    def search_papers(
        self,
        query: str,
        year: Optional[str] = None,
        fields_of_study: Optional[list[str]] = None,
        min_citation_count: Optional[int] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        搜索论文。

        Args:
            query: 搜索关键词
            year: 年份范围，如 "2020-2023"
            fields_of_study: 学科领域列表，如 ["Computer Science"]
            min_citation_count: 最小引用数
            limit: 每页最大结果数（<=100）

        Returns:
            论文信息列表
        """
        kwargs = {"limit": min(limit, 100)}
        if year:
            kwargs["year"] = year
        if fields_of_study:
            kwargs["fields_of_study"] = fields_of_study
        if min_citation_count:
            kwargs["min_citation_count"] = min_citation_count

        results = self.sch.search_paper(query, **kwargs)

        papers = []
        for paper in results:
            papers.append(self._paper_to_dict(paper))
            if len(papers) >= limit:
                break
        return papers

    def get_paper(self, paper_id: str) -> dict:
        """
        获取论文详细信息。

        Args:
            paper_id: 论文 ID（S2 paper ID、DOI、ArXiv ID 等）

        Returns:
            论文信息字典
        """
        paper = self.sch.get_paper(paper_id)
        return self._paper_to_dict(paper)

    def get_author(self, author_id: str) -> dict:
        """
        获取作者详细信息。

        Args:
            author_id: Semantic Scholar 作者 ID

        Returns:
            作者信息字典
        """
        author = self.sch.get_author(author_id)
        return self._author_to_dict(author)

    def search_authors(self, query: str, limit: int = 20) -> list[dict]:
        """
        搜索作者。

        Args:
            query: 作者名搜索词
            limit: 最大返回结果数

        Returns:
            作者信息列表
        """
        results = self.sch.search_author(query)
        authors = []
        for author in results:
            authors.append(self._author_to_dict(author))
            if len(authors) >= limit:
                break
        return authors

    def get_author_papers(self, author_id: str, limit: int = 100) -> list[dict]:
        """
        获取某作者的论文列表。

        Args:
            author_id: Semantic Scholar 作者 ID
            limit: 最大返回结果数

        Returns:
            论文信息列表
        """
        results = self.sch.get_author_papers(author_id, limit=limit)
        papers = []
        for paper in results:
            papers.append(self._paper_to_dict(paper))
            if len(papers) >= limit:
                break
        return papers

    def get_coauthors(self, author_id: str, max_papers: int = 100) -> list[dict]:
        """
        获取某作者的合作者列表（通过共著关系推导）。

        Args:
            author_id: Semantic Scholar 作者 ID
            max_papers: 检索该作者的最大论文数

        Returns:
            合作者列表，每项包含 author_id, name, collaboration_count
        """
        papers = self.get_author_papers(author_id, limit=max_papers)

        coauthor_count: dict[str, dict] = {}
        for paper in papers:
            for author in paper.get("authors", []):
                co_id = author.get("authorId")
                co_name = author.get("name", "")
                if co_id and co_id != author_id:
                    if co_id not in coauthor_count:
                        coauthor_count[co_id] = {
                            "author_id": co_id,
                            "name": co_name,
                            "collaboration_count": 0,
                        }
                    coauthor_count[co_id]["collaboration_count"] += 1

        return sorted(
            coauthor_count.values(),
            key=lambda x: x["collaboration_count"],
            reverse=True,
        )

    def get_paper_citations(self, paper_id: str, limit: int = 100) -> list[dict]:
        """
        获取引用了某论文的文献列表。

        Args:
            paper_id: 论文 ID
            limit: 最大返回结果数

        Returns:
            引用论文列表
        """
        results = self.sch.get_paper_citations(paper_id, limit=limit)
        citations = []
        for citation in results:
            if hasattr(citation, "paper") and citation.paper:
                citations.append(self._paper_to_dict(citation.paper))
            if len(citations) >= limit:
                break
        return citations

    def get_paper_references(self, paper_id: str, limit: int = 100) -> list[dict]:
        """
        获取某论文的参考文献列表。

        Args:
            paper_id: 论文 ID
            limit: 最大返回结果数

        Returns:
            参考文献列表
        """
        results = self.sch.get_paper_references(paper_id, limit=limit)
        references = []
        for ref in results:
            if hasattr(ref, "paper") and ref.paper:
                references.append(self._paper_to_dict(ref.paper))
            if len(references) >= limit:
                break
        return references

    def get_recommended_papers(self, paper_id: str) -> list[dict]:
        """
        获取推荐论文。

        Args:
            paper_id: 种子论文 ID

        Returns:
            推荐论文列表
        """
        results = self.sch.get_recommended_papers(paper_id)
        return [self._paper_to_dict(p) for p in results]

    @staticmethod
    def _paper_to_dict(paper) -> dict:
        """将 Paper 对象转为字典"""
        if isinstance(paper, dict):
            return paper
        return {
            "paperId": getattr(paper, "paperId", None),
            "title": getattr(paper, "title", None),
            "year": getattr(paper, "year", None),
            "citationCount": getattr(paper, "citationCount", None),
            "authors": [
                {"authorId": getattr(a, "authorId", None), "name": getattr(a, "name", None)}
                for a in (getattr(paper, "authors", None) or [])
            ],
            "abstract": getattr(paper, "abstract", None),
            "venue": getattr(paper, "venue", None),
            "externalIds": getattr(paper, "externalIds", None),
            "url": getattr(paper, "url", None),
            "fieldsOfStudy": getattr(paper, "fieldsOfStudy", None),
        }

    @staticmethod
    def _author_to_dict(author) -> dict:
        """将 Author 对象转为字典"""
        if isinstance(author, dict):
            return author
        return {
            "authorId": getattr(author, "authorId", None),
            "name": getattr(author, "name", None),
            "hIndex": getattr(author, "hIndex", None),
            "citationCount": getattr(author, "citationCount", None),
            "paperCount": getattr(author, "paperCount", None),
            "affiliations": getattr(author, "affiliations", None),
            "url": getattr(author, "url", None),
        }
