#!/usr/bin/env python3
"""
领域课题组调研辅助工具

功能：给定一个研究领域的关键词列表和目标会议列表（如CCF-A），
批量检索近N年发表的相关论文，自动聚合为课题组视角的报告。

用法:
    python survey_domain_groups.py \
        --keywords "embedding table" "recommendation storage" "parameter server" \
        --venues "OSDI" "SOSP" "ASPLOS" "EuroSys" "ATC" "SC" "VLDB" "SIGMOD" "FAST" "ISCA" "HPCA" \
        --years 5 \
        --output report.json

    # 也可以直接查询已知作者在特定方向的发表情况
    python survey_domain_groups.py \
        --author "Youyou Lu" \
        --venues "OSDI" "ASPLOS" "VLDB" "SC" "EuroSys" "SIGMOD" \
        --years 5

输出：按课题组（PI）聚合的论文统计、代表作、合作者网络。
"""

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime

try:
    import pyalex
    from pyalex import Authors, Works, Sources
except ImportError:
    print("正在安装 pyalex...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyalex", "-q"])
    import pyalex
    from pyalex import Authors, Works, Sources

# 配置 pyalex
pyalex.config.email = "academiconnection@example.com"

# CCF-A 会议/期刊名称映射（用于模糊匹配）
CCF_A_VENUES = {
    # 系统
    "OSDI": ["OSDI", "Operating Systems Design and Implementation"],
    "SOSP": ["SOSP", "Symposium on Operating Systems Principles"],
    "ASPLOS": ["ASPLOS", "Architectural Support for Programming Languages"],
    "EuroSys": ["EuroSys", "European Conference on Computer Systems"],
    "ATC": ["ATC", "USENIX Annual Technical Conference"],
    "SC": ["SC", "Supercomputing", "International Conference for High Performance Computing"],
    "FAST": ["FAST", "File and Storage Technologies"],
    "NSDI": ["NSDI", "Networked Systems Design and Implementation"],
    # 数据库
    "VLDB": ["VLDB", "Very Large Data Bases", "PVLDB"],
    "SIGMOD": ["SIGMOD", "Management of Data"],
    "ICDE": ["ICDE", "Data Engineering"],
    # 体系结构
    "ISCA": ["ISCA", "International Symposium on Computer Architecture"],
    "HPCA": ["HPCA", "High Performance Computer Architecture"],
    "MICRO": ["MICRO", "Microarchitecture"],
    # AI
    "NeurIPS": ["NeurIPS", "Neural Information Processing"],
    "ICML": ["ICML", "International Conference on Machine Learning"],
    "ICLR": ["ICLR", "International Conference on Learning Representations"],
    # 推荐系统
    "RecSys": ["RecSys", "Recommender Systems"],
    "KDD": ["KDD", "Knowledge Discovery and Data Mining"],
    "WWW": ["WWW", "World Wide Web", "TheWebConf"],
}


def match_venue(source_name, target_venues):
    """精确匹配会议/期刊名称，避免误匹配（如生物学期刊中的SC）"""
    if not source_name:
        return None
    source_lower = source_name.lower()

    for venue_key, aliases in CCF_A_VENUES.items():
        if venue_key not in target_venues:
            continue
        for alias in aliases:
            alias_lower = alias.lower()
            # 对短缩写（<=4字符），要求精确词边界匹配
            if len(alias) <= 4:
                # 检查是否以 "proceedings of xxx" 开头或是精确的期刊名
                pattern = r'\b' + re.escape(alias_lower) + r'\b'
                if re.search(pattern, source_lower):
                    # 额外验证：排除明显不相关的期刊
                    exclude_keywords = ["biology", "chemistry", "medical", "clinical",
                                        "cancer", "cell", "nature", "lancet", "bmj",
                                        "pharmaceutical", "surgery", "pathol"]
                    if any(ek in source_lower for ek in exclude_keywords):
                        continue
                    return venue_key
            else:
                if alias_lower in source_lower:
                    return venue_key
    return None


def search_works_by_keywords(keywords, target_venues, start_year, max_results=500):
    """按关键词搜索论文并过滤会议"""
    all_results = []
    query = " OR ".join(f'"{kw}"' for kw in keywords)

    print(f"  搜索关键词: {query}")
    print(f"  目标会议: {', '.join(target_venues)}")
    print(f"  起始年份: {start_year}")

    try:
        works = Works().search(query).filter(
            publication_year=f">{start_year - 1}"
        ).sort(cited_by_count="desc")

        count = 0
        for page in works.paginate(per_page=200, n_max=max_results):
            for work in page:
                source = work.get("primary_location", {})
                if source:
                    source = source.get("source", {}) or {}
                source_name = source.get("display_name", "") if source else ""

                matched_venue = match_venue(source_name, target_venues)
                if matched_venue:
                    all_results.append({
                        "title": work.get("title", ""),
                        "year": work.get("publication_year"),
                        "venue": matched_venue,
                        "cited_by_count": work.get("cited_by_count", 0),
                        "doi": work.get("doi", ""),
                        "authors": [
                            {
                                "name": a.get("author", {}).get("display_name", ""),
                                "id": a.get("author", {}).get("id", ""),
                                "institutions": [
                                    inst.get("display_name", "")
                                    for inst in a.get("institutions", [])
                                ],
                            }
                            for a in work.get("authorships", [])
                        ],
                    })
                count += 1
            time.sleep(0.1)

        print(f"  检索了 {count} 篇论文，匹配目标会议 {len(all_results)} 篇")
    except Exception as e:
        print(f"  [!] 搜索出错: {e}")

    return all_results


def search_author_works(author_name, target_venues, start_year, max_results=500):
    """查询特定作者在目标会议的发表情况"""
    print(f"\n  查询作者: {author_name}")

    # 定位作者
    results = []
    for page in Authors().search(author_name).paginate(per_page=5, n_max=5):
        results.extend(page)

    if not results:
        print(f"  [!] 未找到作者: {author_name}")
        return []

    author = results[0]
    author_id = author.get("id", "").replace("https://openalex.org/", "")
    print(f"  匹配到: {author.get('display_name')} (ID: {author_id}, h-index: {author.get('summary_stats', {}).get('h_index', 'N/A')})")

    all_results = []
    try:
        works = Works().filter(
            author={"id": author_id},
            publication_year=f">{start_year - 1}"
        ).sort(publication_year="desc")

        for page in works.paginate(per_page=200, n_max=max_results):
            for work in page:
                source = work.get("primary_location", {})
                if source:
                    source = source.get("source", {}) or {}
                source_name = source.get("display_name", "") if source else ""

                matched_venue = match_venue(source_name, target_venues)
                if matched_venue:
                    all_results.append({
                        "title": work.get("title", ""),
                        "year": work.get("publication_year"),
                        "venue": matched_venue,
                        "cited_by_count": work.get("cited_by_count", 0),
                        "doi": work.get("doi", ""),
                        "authors": [
                            {
                                "name": a.get("author", {}).get("display_name", ""),
                                "id": a.get("author", {}).get("id", ""),
                                "institutions": [
                                    inst.get("display_name", "")
                                    for inst in a.get("institutions", [])
                                ],
                            }
                            for a in work.get("authorships", [])
                        ],
                    })
        time.sleep(0.2)
        print(f"  找到 {len(all_results)} 篇目标会议论文")
    except Exception as e:
        print(f"  [!] 查询出错: {e}")

    return all_results


def aggregate_by_group(papers):
    """按课题组（最后通讯作者的机构+PI）聚合论文"""
    group_map = defaultdict(lambda: {
        "papers": [],
        "members": defaultdict(int),
        "venues": defaultdict(int),
        "years": defaultdict(int),
        "total_citations": 0,
    })

    for paper in papers:
        authors = paper.get("authors", [])
        if not authors:
            continue

        # 通常最后一位作者或机构最频繁出现的为PI所在组
        # 取第一作者的机构作为课题组归属
        first_author = authors[0]
        institutions = first_author.get("institutions", [])
        group_key = institutions[0] if institutions else "Unknown"

        # 找最后位作者作为潜在PI
        last_author = authors[-1] if len(authors) > 1 else authors[0]

        group_map[group_key]["papers"].append(paper)
        group_map[group_key]["venues"][paper["venue"]] += 1
        group_map[group_key]["years"][paper["year"]] += 1
        group_map[group_key]["total_citations"] += paper.get("cited_by_count", 0)

        for a in authors:
            group_map[group_key]["members"][a["name"]] += 1

    return dict(group_map)


def print_report(groups, papers):
    """打印调研报告"""
    print("\n" + "=" * 80)
    print("  领域课题组调研报告")
    print("=" * 80)
    print(f"\n  总计 {len(papers)} 篇匹配论文，分布在 {len(groups)} 个机构/课题组\n")

    # 按论文数排序
    sorted_groups = sorted(groups.items(), key=lambda x: len(x[1]["papers"]), reverse=True)

    for rank, (group_name, info) in enumerate(sorted_groups[:15], 1):
        print(f"\n{'─' * 80}")
        print(f"  #{rank} {group_name}")
        print(f"{'─' * 80}")
        print(f"  论文数: {len(info['papers'])}  |  总引用: {info['total_citations']}")

        # 会议分布
        venue_str = ", ".join(f"{v}:{c}" for v, c in sorted(info["venues"].items(), key=lambda x: -x[1]))
        print(f"  会议分布: {venue_str}")

        # 年度分布
        year_str = ", ".join(f"{y}:{c}" for y, c in sorted(info["years"].items()))
        print(f"  年度分布: {year_str}")

        # 核心成员（合作≥2次）
        core_members = [(name, cnt) for name, cnt in info["members"].items() if cnt >= 2]
        core_members.sort(key=lambda x: -x[1])
        if core_members:
            member_str = ", ".join(f"{name}({cnt})" for name, cnt in core_members[:10])
            print(f"  核心成员: {member_str}")

        # 代表作
        top_papers = sorted(info["papers"], key=lambda x: x.get("cited_by_count", 0), reverse=True)[:5]
        print(f"  代表作:")
        for p in top_papers:
            print(f"    • [{p['venue']}'{str(p['year'])[2:]}] {p['title']} (cited: {p['cited_by_count']})")

    # 总体统计
    print(f"\n{'═' * 80}")
    print(f"  总体统计")
    print(f"{'═' * 80}")

    venue_total = defaultdict(int)
    year_total = defaultdict(int)
    for p in papers:
        venue_total[p["venue"]] += 1
        year_total[p["year"]] += 1

    print(f"  按会议: {', '.join(f'{v}:{c}' for v, c in sorted(venue_total.items(), key=lambda x: -x[1]))}")
    print(f"  按年份: {', '.join(f'{y}:{c}' for y, c in sorted(year_total.items()))}")
    print(f"  平均引用: {sum(p.get('cited_by_count', 0) for p in papers) / max(len(papers), 1):.1f}")
    print(f"{'═' * 80}\n")


def save_report(groups, papers, output_path):
    """保存JSON格式报告"""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    report = {
        "generated_at": datetime.now().isoformat(),
        "total_papers": len(papers),
        "total_groups": len(groups),
        "groups": {},
        "all_papers": papers,
    }

    for group_name, info in groups.items():
        report["groups"][group_name] = {
            "paper_count": len(info["papers"]),
            "total_citations": info["total_citations"],
            "venues": dict(info["venues"]),
            "years": dict(info["years"]),
            "core_members": [
                {"name": name, "paper_count": cnt}
                for name, cnt in sorted(info["members"].items(), key=lambda x: -x[1])
                if cnt >= 2
            ],
            "papers": sorted(info["papers"], key=lambda x: -x.get("cited_by_count", 0)),
        }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  报告已保存到: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="领域课题组调研辅助工具 — 批量检索特定领域在顶会的发表情况并按课题组聚合"
    )
    parser.add_argument(
        "--keywords", nargs="+",
        help='搜索关键词列表，如: "embedding table" "recommendation storage"'
    )
    parser.add_argument(
        "--author", type=str,
        help="查询特定作者的发表情况"
    )
    parser.add_argument(
        "--venues", nargs="+", default=["OSDI", "SOSP", "ASPLOS", "EuroSys", "ATC", "SC", "VLDB", "SIGMOD", "FAST"],
        help="目标会议列表（默认系统方向CCF-A）"
    )
    parser.add_argument(
        "--years", type=int, default=5,
        help="检索最近N年（默认5年）"
    )
    parser.add_argument(
        "--max-results", type=int, default=500,
        help="最大检索论文数"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="输出JSON报告路径"
    )
    args = parser.parse_args()

    if not args.keywords and not args.author:
        parser.error("请至少提供 --keywords 或 --author")

    start_year = datetime.now().year - args.years

    print("=" * 80)
    print("  领域课题组调研辅助工具")
    print("=" * 80)

    papers = []

    if args.keywords:
        print(f"\n📖 按关键词搜索论文...")
        papers.extend(search_works_by_keywords(args.keywords, args.venues, start_year, args.max_results))

    if args.author:
        print(f"\n📖 按作者搜索论文...")
        papers.extend(search_author_works(args.author, args.venues, start_year, args.max_results))

    if not papers:
        print("\n  未找到匹配论文，建议：")
        print("  1. 尝试更宽泛的关键词")
        print("  2. 扩大年份范围")
        print("  3. 增加目标会议列表")
        sys.exit(0)

    # 去重
    seen = set()
    unique_papers = []
    for p in papers:
        key = (p["title"], p["year"])
        if key not in seen:
            seen.add(key)
            unique_papers.append(p)
    papers = unique_papers
    print(f"\n  去重后共 {len(papers)} 篇论文")

    # 聚合
    print("\n🔬 按课题组聚合...")
    groups = aggregate_by_group(papers)

    # 输出
    print_report(groups, papers)

    if args.output:
        save_report(groups, papers, args.output)


if __name__ == "__main__":
    main()
