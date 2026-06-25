"""
OpenAlex API 调用测试

测试论文搜索、作者查询和合作关系提取功能。
"""

import sys
import os
import json

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "third_party", "pyalex")
)

from academiconnection import OpenAlexClient, NetworkBuilder


def test_search_works():
    """测试论文搜索"""
    print("=" * 60)
    print("测试 1: OpenAlex 论文搜索 - 'recommendation system'")
    print("=" * 60)

    client = OpenAlexClient()
    results = client.search_works("recommendation system", max_results=5)

    print(f"\n找到 {len(results)} 篇论文:")
    for i, work in enumerate(results, 1):
        title = work.get("title", "N/A")
        year = work.get("publication_year", "N/A")
        cited = work.get("cited_by_count", 0)
        authors = [
            a.get("author", {}).get("display_name", "")
            for a in work.get("authorships", [])[:3]
        ]
        print(f"\n  [{i}] {title}")
        print(f"      年份: {year} | 引用: {cited}")
        print(f"      作者: {', '.join(authors)}")

    assert len(results) > 0, "未找到任何论文"
    print("\n✅ 论文搜索测试通过")
    return results


def test_search_authors():
    """测试作者搜索"""
    print("\n" + "=" * 60)
    print("测试 2: OpenAlex 作者搜索 - 'Hinton'")
    print("=" * 60)

    client = OpenAlexClient()
    results = client.search_authors("Geoffrey Hinton", max_results=5)

    print(f"\n找到 {len(results)} 位作者:")
    for i, author in enumerate(results, 1):
        name = author.get("display_name", "N/A")
        works_count = author.get("works_count", 0)
        cited = author.get("cited_by_count", 0)
        author_id = author.get("id", "").replace("https://openalex.org/", "")
        print(f"\n  [{i}] {name} (ID: {author_id})")
        print(f"      论文数: {works_count} | 被引: {cited}")

    assert len(results) > 0, "未找到任何作者"
    print("\n✅ 作者搜索测试通过")
    return results


def test_get_coauthors():
    """测试合作者关系提取"""
    print("\n" + "=" * 60)
    print("测试 3: OpenAlex 合作者关系 - 搜索 recommendation system 领域活跃作者")
    print("=" * 60)

    client = OpenAlexClient()

    # 先搜索领域内的论文，找到高影响力作者
    works = client.search_works("recommendation system embedding", max_results=10)

    if not works:
        print("⚠️ 未找到论文，跳过合作者测试")
        return

    # 取第一篇论文的第一作者
    first_work = works[0]
    authorships = first_work.get("authorships", [])
    if not authorships:
        print("⚠️ 论文无作者信息，跳过")
        return

    target_author_id = authorships[0].get("author", {}).get("id", "")
    target_author_name = authorships[0].get("author", {}).get("display_name", "")
    # 从完整 URL 提取 ID
    short_id = target_author_id.replace("https://openalex.org/", "")

    print(f"\n目标作者: {target_author_name} ({short_id})")
    print(f"来源论文: {first_work.get('title', 'N/A')}")

    # 获取合作者（限制检索论文数以加快测试）
    coauthors = client.get_coauthors(short_id, max_works=20)

    print(f"\n找到 {len(coauthors)} 位合作者，Top 10:")
    for i, co in enumerate(coauthors[:10], 1):
        print(f"  [{i}] {co['name']} - 合作 {co['collaboration_count']} 次")

    assert len(coauthors) > 0, "未找到合作者"
    print("\n✅ 合作者关系测试通过")
    return coauthors


def test_network_building():
    """测试网络构建"""
    print("\n" + "=" * 60)
    print("测试 4: 合作网络构建 - 'vector database recommendation'")
    print("=" * 60)

    client = OpenAlexClient()
    works = client.search_works("vector database recommendation", max_results=20)

    builder = NetworkBuilder()
    builder.build_from_works(works, source="openalex")

    stats = builder.get_statistics()
    print(f"\n网络统计:")
    print(f"  节点（作者）数: {stats['num_nodes']}")
    print(f"  边（合作关系）数: {stats['num_edges']}")
    print(f"  平均合作权重: {stats['avg_weight']:.2f}")
    print(f"  最大合作权重: {stats['max_weight']}")

    if stats.get("top_collaborators"):
        print(f"\n  Top 合作对:")
        for tc in stats["top_collaborators"][:5]:
            print(f"    {tc['author1']} <-> {tc['author2']} ({tc['collaborations']} 次)")

    assert stats["num_nodes"] > 0, "网络无节点"
    print("\n✅ 网络构建测试通过")
    return stats


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    print("🚀 OpenAlex API 调用测试")
    print("注意: 如无 API key，部分功能可能受限\n")

    try:
        test_search_works()
        test_search_authors()
        test_get_coauthors()
        test_network_building()
        print("\n" + "=" * 60)
        print("🎉 所有 OpenAlex 测试通过!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
