"""
Semantic Scholar API 调用测试

测试论文搜索、作者查询、引用关系和合作关系提取功能。
注意：无 API key 时 S2 有严格的速率限制（每分钟约 1 请求），
测试之间需要加延迟。
"""

import sys
import os
import json
import time

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "third_party", "semanticscholar"),
)

from academiconnection import SemanticScholarClient, NetworkBuilder

# 无 API key 时请求间隔（秒）
REQUEST_DELAY = 3


def wait():
    """请求间延迟，避免触发速率限制"""
    print(f"  (等待 {REQUEST_DELAY}s 避免速率限制...)")
    time.sleep(REQUEST_DELAY)


def test_search_papers():
    """测试论文搜索"""
    print("=" * 60)
    print("测试 1: Semantic Scholar 论文搜索 - 'recommendation system'")
    print("=" * 60)

    client = SemanticScholarClient()
    results = client.search_papers(
        "recommendation system",
        year="2022-2025",
        fields_of_study=["Computer Science"],
        limit=5,
    )

    print(f"\n找到 {len(results)} 篇论文:")
    for i, paper in enumerate(results, 1):
        title = paper.get("title", "N/A")
        year = paper.get("year", "N/A")
        cited = paper.get("citationCount", 0)
        authors = [a.get("name", "") for a in paper.get("authors", [])[:3]]
        print(f"\n  [{i}] {title}")
        print(f"      年份: {year} | 引用: {cited}")
        print(f"      作者: {', '.join(authors)}")

    assert len(results) > 0, "未找到任何论文"
    print("\n✅ 论文搜索测试通过")
    return results


def test_get_paper():
    """测试获取单篇论文（更轻量的 API 调用）"""
    print("\n" + "=" * 60)
    print("测试 2: Semantic Scholar 获取单篇论文 - Attention Is All You Need")
    print("=" * 60)

    client = SemanticScholarClient()
    # "Attention Is All You Need" 的 S2 Paper ID
    paper_id = "204e3073870fae3d05bcbc2f6a8e263d9b72e776"

    paper = client.get_paper(paper_id)
    print(f"\n论文: {paper.get('title', 'N/A')}")
    print(f"年份: {paper.get('year', 'N/A')}")
    print(f"引用数: {paper.get('citationCount', 'N/A')}")
    print(f"作者: {', '.join(a.get('name', '') for a in paper.get('authors', []))}")
    print(f"领域: {paper.get('fieldsOfStudy', 'N/A')}")

    assert paper.get("title") is not None, "未获取到论文标题"
    print("\n✅ 单篇论文获取测试通过")
    return paper


def test_search_authors():
    """测试作者搜索"""
    print("\n" + "=" * 60)
    print("测试 3: Semantic Scholar 作者搜索 - 'Yann LeCun'")
    print("=" * 60)

    client = SemanticScholarClient()
    results = client.search_authors("Yann LeCun", limit=3)

    print(f"\n找到 {len(results)} 位作者:")
    for i, author in enumerate(results, 1):
        name = author.get("name", "N/A")
        h_index = author.get("hIndex", "N/A")
        paper_count = author.get("paperCount", 0)
        author_id = author.get("authorId", "N/A")
        print(f"\n  [{i}] {name} (ID: {author_id})")
        print(f"      h-index: {h_index} | 论文数: {paper_count}")

    assert len(results) > 0, "未找到任何作者"
    print("\n✅ 作者搜索测试通过")
    return results


def test_get_coauthors():
    """测试合作者关系提取"""
    print("\n" + "=" * 60)
    print("测试 4: Semantic Scholar 合作者关系")
    print("=" * 60)

    client = SemanticScholarClient()

    # 使用已知的 Yann LeCun ID，避免额外搜索请求
    target_id = "1688681"
    target_name = "Yann LeCun"
    print(f"\n目标作者: {target_name} (ID: {target_id})")

    # 获取合作者（限制论文数以减少请求）
    coauthors = client.get_coauthors(target_id, max_papers=10)

    print(f"\n找到 {len(coauthors)} 位合作者，Top 10:")
    for i, co in enumerate(coauthors[:10], 1):
        print(f"  [{i}] {co['name']} - 合作 {co['collaboration_count']} 次")

    assert len(coauthors) > 0, "未找到合作者"
    print("\n✅ 合作者关系测试通过")
    return coauthors


def test_network_building_s2():
    """测试通过 S2 数据构建网络"""
    print("\n" + "=" * 60)
    print("测试 5: 使用 S2 数据构建合作网络 - 'vector search recommendation'")
    print("=" * 60)

    client = SemanticScholarClient()
    papers = client.search_papers("vector search recommendation", limit=10)

    builder = NetworkBuilder()
    builder.build_from_works(papers, source="s2")

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
    print("\n✅ S2 网络构建测试通过")
    return stats


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    print("🚀 Semantic Scholar API 调用测试")
    print("注意: 无 API key 时有速率限制（约 1 req/min），测试会较慢\n")

    tests = [
        ("获取单篇论文", test_get_paper),
        ("作者搜索", test_search_authors),
        ("合作者关系", test_get_coauthors),
        ("论文搜索", test_search_papers),
        ("网络构建", test_network_building_s2),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"\n❌ 测试 [{name}] 失败: {e}")
            if "429" in str(e) or "Too Many Requests" in str(e):
                print("   → 触发速率限制，等待后继续...")
                time.sleep(10)
            else:
                import traceback
                traceback.print_exc()
            failed += 1

        # 请求间延迟
        if test_fn != tests[-1][1]:
            wait()

    print("\n" + "=" * 60)
    if failed == 0:
        print(f"🎉 所有 {passed} 个 Semantic Scholar 测试通过!")
    else:
        print(f"⚠️ 通过 {passed}/{passed+failed} 个测试 (失败 {failed} 个)")
        if failed > 0:
            print("   提示: 设置 S2_API_KEY 环境变量可提高速率限制")
    print("=" * 60)
