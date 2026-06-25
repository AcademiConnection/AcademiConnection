#!/usr/bin/env python3
"""
学者学术关系网络查询脚本

用法:
    python query_scholar_network.py --orcid 0000-0002-8168-6075
    python query_scholar_network.py --openalex-id A5073352741
    python query_scholar_network.py --name "Yoshua Bengio"

输出完整的学术 connection 报告，包括合作者网络和实验室同期成员。
"""

import argparse
import sys
import time

try:
    import pyalex
    from pyalex import Authors, Works
except ImportError:
    print("正在安装 pyalex...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyalex", "-q"])
    import pyalex
    from pyalex import Authors, Works


def find_scholar(name=None, orcid=None, openalex_id=None):
    """定位学者，返回 author 数据"""
    author = None

    if openalex_id:
        try:
            author = Authors()[openalex_id]
        except Exception as e:
            print(f"  [!] OpenAlex ID 查询失败: {e}")

    if not author and orcid:
        try:
            orcid_url = orcid if orcid.startswith("http") else f"https://orcid.org/{orcid}"
            author = Authors()[orcid_url]
        except Exception as e:
            print(f"  [!] ORCID 查询失败: {e}")

    if not author and name:
        results = []
        for page in Authors().search(name).paginate(per_page=5, n_max=5):
            results.extend(page)
        if results:
            author = results[0]
            print(f"  [i] 通过姓名搜索匹配到: {author.get('display_name')} ({author.get('id')})")
            print(f"      请确认是否正确（可能存在重名）")
        else:
            print(f"  [!] 未找到名为 '{name}' 的学者")

    return author


def get_all_works(author_id, max_works=500):
    """获取学者全部论文"""
    all_works = []
    for page in Works().filter(author={"id": author_id}).sort(publication_year="desc").paginate(per_page=200, n_max=max_works):
        all_works.extend(page)
    return all_works


def extract_coauthors(all_works, author_full_id):
    """从论文中提取合作者网络"""
    coauthor_map = {}

    for work in all_works:
        year = work.get("publication_year")
        title = work.get("title", "")
        for authorship in work.get("authorships", []):
            co = authorship.get("author", {})
            co_id = co.get("id", "")
            co_name = co.get("display_name", "")

            if co_id and co_id != author_full_id:
                if co_id not in coauthor_map:
                    coauthor_map[co_id] = {
                        "name": co_name,
                        "id": co_id,
                        "count": 0,
                        "papers": [],
                        "institutions": set(),
                        "years": set(),
                    }
                coauthor_map[co_id]["count"] += 1
                coauthor_map[co_id]["papers"].append({"title": title, "year": year})
                if year:
                    coauthor_map[co_id]["years"].add(year)
                for inst in authorship.get("institutions", []):
                    iname = inst.get("display_name", "")
                    if iname:
                        coauthor_map[co_id]["institutions"].add(iname)

    return sorted(coauthor_map.values(), key=lambda x: x["count"], reverse=True)


def find_lab_mates(author_info, coauthors, top_n_advisors=5, max_advisor_works=300):
    """通过导师的合作网络追溯实验室同期成员"""

    # 提取目标学者的机构和时间信息
    affiliations = author_info.get("affiliations", [])
    inst_names = set()
    all_years = set()
    for aff in affiliations:
        inst = aff.get("institution", {})
        years = aff.get("years", [])
        inst_names.add(inst.get("display_name", ""))
        all_years.update(years)

    # 扩展年份容差 ±1
    expanded_years = set()
    for y in all_years:
        expanded_years.update([y - 1, y, y + 1])

    # 取前N个高频合作者作为可能的导师
    potential_advisors = coauthors[:top_n_advisors]
    all_lab_mates = {}  # advisor_name -> [lab_mates]

    for advisor in potential_advisors:
        advisor_id = advisor["id"].replace("https://openalex.org/", "")
        advisor_name = advisor["name"]
        time.sleep(0.2)

        try:
            advisor_works = []
            for page in Works().filter(author={"id": advisor_id}).paginate(per_page=200, n_max=max_advisor_works):
                advisor_works.extend(page)

            # 构建导师的合作者网络
            advisor_coauthors = {}
            for work in advisor_works:
                year = work.get("publication_year")
                for authorship in work.get("authorships", []):
                    co = authorship.get("author", {})
                    co_id = co.get("id", "")
                    co_name = co.get("display_name", "")
                    if co_id and co_id != advisor["id"]:
                        if co_id not in advisor_coauthors:
                            advisor_coauthors[co_id] = {
                                "name": co_name,
                                "id": co_id,
                                "count": 0,
                                "years": set(),
                                "institutions": set(),
                            }
                        advisor_coauthors[co_id]["count"] += 1
                        if year:
                            advisor_coauthors[co_id]["years"].add(year)
                        for inst in authorship.get("institutions", []):
                            iname = inst.get("display_name", "")
                            if iname:
                                advisor_coauthors[co_id]["institutions"].add(iname)

            # 过滤同组成员
            lab_mates = []
            target_author_id = author_info.get("id", "")
            for co_id, co_info in advisor_coauthors.items():
                if target_author_id and target_author_id in co_id:
                    continue
                shared_inst = co_info["institutions"] & inst_names
                year_overlap = co_info["years"] & expanded_years
                if shared_inst and year_overlap and co_info["count"] >= 2:
                    lab_mates.append({
                        "name": co_info["name"],
                        "id": co_info["id"],
                        "collaborations_with_advisor": co_info["count"],
                        "shared_institutions": list(shared_inst),
                        "active_years": sorted(co_info["years"]),
                    })

            lab_mates.sort(key=lambda x: x["collaborations_with_advisor"], reverse=True)
            all_lab_mates[advisor_name] = lab_mates

        except Exception as e:
            all_lab_mates[advisor_name] = f"Error: {e}"

        time.sleep(0.3)

    return all_lab_mates


def print_report(author_info, all_works, coauthors, lab_mates):
    """打印完整报告"""
    name = author_info.get("display_name", "Unknown")
    oa_id = author_info.get("id", "").replace("https://openalex.org/", "")

    print("\n" + "=" * 70)
    print(f"  学术关系网络报告: {name}")
    print("=" * 70)

    # 基本信息
    print(f"\n  OpenAlex ID: {oa_id}")
    print(f"  ORCID: {author_info.get('orcid', 'N/A')}")
    print(f"  论文数: {author_info.get('works_count', 0)}")
    print(f"  被引次数: {author_info.get('cited_by_count', 0)}")
    print(f"  H-Index: {author_info.get('summary_stats', {}).get('h_index', 'N/A')}")

    # 机构历史
    affiliations = author_info.get("affiliations", [])
    if affiliations:
        print("\n  机构历史:")
        for aff in affiliations:
            inst = aff.get("institution", {})
            years = aff.get("years", [])
            yr = f"{min(years)}-{max(years)}" if years else "N/A"
            print(f"    - {inst.get('display_name', 'N/A')} ({yr})")

    # 论文列表（概要）
    print(f"\n{'─' * 70}")
    print(f"  全部论文 ({len(all_works)} 篇，按年份降序)")
    print(f"{'─' * 70}")
    for i, w in enumerate(all_works[:20], 1):
        title = w.get("title", "N/A")
        year = w.get("publication_year", "?")
        cited = w.get("cited_by_count", 0)
        print(f"  [{i}] ({year}) {title} [cited: {cited}]")
    if len(all_works) > 20:
        print(f"  ... (共 {len(all_works)} 篇，仅显示前 20)")

    # 合作者网络
    print(f"\n{'─' * 70}")
    print(f"  合作者网络 ({len(coauthors)} 位)")
    print(f"{'─' * 70}")

    core = [c for c in coauthors if c["count"] >= 3]
    print(f"\n  核心合作者（合作≥3次，共 {len(core)} 位）:")
    for c in core[:20]:
        years = sorted(c["years"]) if c["years"] else []
        yr = f"{years[0]}-{years[-1]}" if years else "N/A"
        insts = ", ".join(sorted(c["institutions"])) if c["institutions"] else "N/A"
        print(f"    • {c['name']} ({c['count']}次, {yr}) — {insts}")

    # 实验室同期成员
    print(f"\n{'─' * 70}")
    print(f"  实验室/团队同期成员分析")
    print(f"{'─' * 70}")

    for advisor_name, mates in lab_mates.items():
        print(f"\n  ── 以 {advisor_name} 为中心 ──")
        if isinstance(mates, str):
            print(f"    {mates}")
            continue
        print(f"    找到 {len(mates)} 位同期成员:")
        for m in mates[:15]:
            yrs = m["active_years"]
            yr = f"{yrs[0]}-{yrs[-1]}" if yrs else "N/A"
            print(f"      • {m['name']} (与{advisor_name}合作{m['collaborations_with_advisor']}次, {yr})")
            print(f"        机构: {', '.join(m['shared_institutions'])}")

    # 总结
    print(f"\n{'═' * 70}")
    print(f"  Connection 圈层总结")
    print(f"{'═' * 70}")
    advisors = coauthors[:3]
    advisor_strs = [a["name"] + f"({a['count']}次)" for a in advisors]
    print(f"  第一圈层（导师/核心）: {', '.join(advisor_strs)}")
    mid = [c for c in coauthors[3:] if c["count"] >= 3]
    if mid:
        mid_names = [c["name"] for c in mid[:10]]
        print(f"  第二圈层（密切合作）: {', '.join(mid_names)}")
    single = [c for c in coauthors if c["count"] == 1]
    print(f"  第三圈层（一般合作）: {len(single)} 位单次合作者")
    print(f"\n{'═' * 70}")


def main():
    parser = argparse.ArgumentParser(description="查询学者学术关系网络")
    parser.add_argument("--name", type=str, help="学者姓名（有重名风险）")
    parser.add_argument("--orcid", type=str, help="ORCID（精确匹配）")
    parser.add_argument("--openalex-id", type=str, help="OpenAlex ID（如 A5073352741）")
    parser.add_argument("--max-works", type=int, default=500, help="最大论文检索数")
    parser.add_argument("--top-advisors", type=int, default=5, help="追溯前N个高频合作者的团队")
    args = parser.parse_args()

    if not any([args.name, args.orcid, args.openalex_id]):
        parser.error("请至少提供 --name, --orcid, 或 --openalex-id 之一")

    print("📖 正在定位学者...")
    author_info = find_scholar(name=args.name, orcid=args.orcid, openalex_id=args.openalex_id)
    if not author_info:
        print("❌ 未找到学者，请检查输入")
        sys.exit(1)

    author_id = author_info.get("id", "").replace("https://openalex.org/", "")
    author_full_id = author_info.get("id", "")
    print(f"✓ 已定位: {author_info.get('display_name')} (ID: {author_id})")

    print("📄 正在获取论文列表...")
    all_works = get_all_works(author_id, max_works=args.max_works)
    print(f"✓ 获取到 {len(all_works)} 篇论文")

    print("🔗 正在提取合作者网络...")
    coauthors = extract_coauthors(all_works, author_full_id)
    print(f"✓ 提取到 {len(coauthors)} 位合作者")

    print("🏫 正在追溯实验室同期成员...")
    lab_mates = find_lab_mates(author_info, coauthors, top_n_advisors=args.top_advisors)
    print("✓ 实验室分析完成")

    print_report(author_info, all_works, coauthors, lab_mates)


if __name__ == "__main__":
    main()
