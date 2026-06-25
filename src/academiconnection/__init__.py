"""
AcademiConnection - 科研人员关系网络构建工具

通过 OpenAlex 和 Semantic Scholar API 搜索指定领域的科研信息，
构建作者合作关系网络图谱。
"""

__version__ = "0.1.0"

from .openalex_client import OpenAlexClient
from .semantic_scholar_client import SemanticScholarClient
from .network_builder import NetworkBuilder
from .relationship_finder import RelationshipFinder

__all__ = [
    "OpenAlexClient",
    "SemanticScholarClient",
    "NetworkBuilder",
    "RelationshipFinder",
]
