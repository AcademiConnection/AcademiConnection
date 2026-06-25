"""
OpenAlex API 客户端封装

基于 pyalex 库，提供论文搜索、作者查询、合作关系提取等功能。
"""

import os
import sys
from typing import Optional
from itertools import chain

# 将 submodule 路径加入 sys.path
_PYALEX_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "third_party", "pyalex"
)
if os.path.isdir(_PYALEX_PATH) and _PYALEX_PATH not in sys.path:
    sys.path.insert(0, os.path.abspath(_PYALEX_PATH))

import pyalex
from pyalex import Works, Authors, Institutions


class OpenAlexClient:
    """OpenAlex API 统一客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        email: Optional[str] = None,
    ):
        """
        初始化 OpenAlex 客户端。

        Args:
            api_key: OpenAlex API key（免费申请）。若未提供，从环境变量 OPENALEX_API_KEY 读取。
            email: 联系邮箱，用于 polite pool。若未提供，从环境变量 OPENALEX_EMAIL 读取。
        """
        self.api_key = api_key or os.getenv("OPENALEX_API_KEY", "")
        self.email = email or os.getenv("OPENALEX_EMAIL", "")

        if self.api_key:
            pyalex.config.api_key = self.api_key
        if self.email:
            pyalex.config.email = self.email

        pyalex.config.max_retries = 3
        pyalex.config.retry_backoff_factor = 0.5
        pyalex.config.retry_http_codes = [429, 500, 503]

    def search_works(
        self,
        query: str,
        year: Optional[str] = None,
        per_page: int = 25,
        max_results: int = 100,
    ) -> list[dict]:
        """
        搜索论文/作品。

        Args:
            query: 搜索关键词
            year: 出版年份过滤，如 "2023" 或 None
            per_page: 每页结果数（最大 200）
            max_results: 最大返回结果数

        Returns:
            论文信息列表
        """
        search = Works().search(query)
        if year:
            search = search.filter(publication_year=int(year))

        results = []
        for page in search.paginate(per_page=min(per_page, 200), n_max=max_results):
            results.extend(page)

        return results

    def search_works_by_topic(
        self,
        query: str,
        per_page: int = 25,
        max_results: int = 100,
    ) -> list[dict]:
        """
        通过语义搜索查找相关论文。

        Args:
            query: 自然语言描述的研究主题
            per_page: 每页结果数
            max_results: 最大返回结果数

        Returns:
            论文信息列表
        """
        results = []
        for page in Works().search(query).paginate(
            per_page=min(per_page, 200), n_max=max_results
        ):
            results.extend(page)
        return results

    def get_author(self, author_id: str) -> dict:
        """
        获取作者详细信息。

        Args:
            author_id: OpenAlex 作者 ID（如 "A5027479191"）或 ORCID URL

        Returns:
            作者信息字典
        """
        return Authors()[author_id]

    def search_authors(self, query: str, max_results: int = 25) -> list[dict]:
        """
        搜索作者。

        Args:
            query: 作者名搜索词
            max_results: 最大返回结果数

        Returns:
            作者信息列表
        """
        results = []
        for page in Authors().search(query).paginate(per_page=25, n_max=max_results):
            results.extend(page)
        return results

    def get_author_works(
        self, author_id: str, max_results: int = 200
    ) -> list[dict]:
        """
        获取某作者的所有论文。

        Args:
            author_id: OpenAlex 作者 ID
            max_results: 最大返回结果数

        Returns:
            论文列表
        """
        results = []
        for page in Works().filter(author={"id": author_id}).paginate(
            per_page=200, n_max=max_results
        ):
            results.extend(page)
        return results

    def get_coauthors(self, author_id: str, max_works: int = 200) -> list[dict]:
        """
        获取某作者的合作者列表（通过共著关系推导）。

        Args:
            author_id: OpenAlex 作者 ID
            max_works: 检索该作者的最大论文数

        Returns:
            合作者列表，每项包含 author_id, name, collaboration_count
        """
        works = self.get_author_works(author_id, max_results=max_works)

        coauthor_count: dict[str, dict] = {}
        for work in works:
            for authorship in work.get("authorships", []):
                co_id = authorship.get("author", {}).get("id", "")
                co_name = authorship.get("author", {}).get("display_name", "")
                if co_id and co_id != f"https://openalex.org/{author_id}":
                    if co_id not in coauthor_count:
                        coauthor_count[co_id] = {
                            "author_id": co_id,
                            "name": co_name,
                            "collaboration_count": 0,
                        }
                    coauthor_count[co_id]["collaboration_count"] += 1

        # 按合作次数降序排列
        return sorted(
            coauthor_count.values(),
            key=lambda x: x["collaboration_count"],
            reverse=True,
        )

    def search_institutions(self, query: str, max_results: int = 10) -> list[dict]:
        """
        搜索机构。

        Args:
            query: 机构名搜索词
            max_results: 最大返回结果数

        Returns:
            机构信息列表
        """
        results = []
        for page in Institutions().search(query).paginate(
            per_page=25, n_max=max_results
        ):
            results.extend(page)
        return results

    def get_works_by_institution(
        self, institution_id: str, query: Optional[str] = None, max_results: int = 100
    ) -> list[dict]:
        """
        获取某机构的论文。

        Args:
            institution_id: OpenAlex 机构 ID
            query: 可选的搜索关键词
            max_results: 最大返回结果数

        Returns:
            论文列表
        """
        search = Works().filter(
            authorships={"institutions": {"id": institution_id}}
        )
        if query:
            search = search.search(query)

        results = []
        for page in search.paginate(per_page=200, n_max=max_results):
            results.extend(page)
        return results
