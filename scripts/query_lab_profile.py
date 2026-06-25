#!/usr/bin/env python3
"""
实验室全景画像辅助工具

功能：给定实验室成员名单，批量查询每人的论文、引用、合作者，
并分析成员间合作关系和外部合作网络。

用法:
    # 查询单个PI的合作网络和学生
    python query_lab_profile.py --pi "Youyou Lu"

    # 给定成员名单批量查询
    python query_lab_profile.py --members "Youyou Lu" "Jiwu Shu" "Minhui Xie" "Ruwen Fan"

    # 从文件读取成员名单（每行一个名字）
    python query_lab_profile.py --members-file lab_members.txt

    # 指定输出JSON
    python query_lab_profile.py --pi "Bin Cui" --output lab_report.json

输出：每位成员的论文统计、合作者、成员间合作矩阵、外部合作网络。
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime

try:
    import pyalex
    from pyalex import Authors, Works
except ImportError:
    print("正在安装 pyalex...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyalex", "-q"])
    import pyalex
    from pyalex import Authors, Works

pyalex.config.email = "academiconnection@example.com"


def find_author(name, affiliation_hint=None):
    """通过姓名查找作者，返回 OpenAlex author 对象。
    affiliation_hint 用于消歧（如 'Tsinghua'）。
    """
    results = []
    try:
        for page in Authors().search(name).paginate(per_page=10, n_max=10):
            results.extend(page)
    except Exception as e:
        print(f"  [!] 搜索 '{name}' 失败: {e}")
        return None

    if not results:
        print(f"  [!] 未找到: {name}")
        return None

    # 如果有机构提示，优先匹配
    if affiliation_hint:
        hint_lower = affiliation_hint.lower()
        for r in results:
            affs = r.get("affiliations", [])
            for aff in affs:
                inst_name = aff.get("institution", {}).get("display_name", "").lower()
                if hint_lower in inst_name:
                    print(f"  [i] 通过机构匹配: {r.get('display_name')} @ {aff['institution']['display_name']}")
                    return r

    # 否则取第一个结果，但打印警告
    author = results[0]
    if len(results) > 1:
        print(f"  [⚠] '{name}' 有多个匹配，取第一个: {author.get('display_name')} "
              f"(works:{author.get('works_count', 0)}). 建议使用 --affiliation 消歧。")
    return author


def get_author_works(author_id, max_works=300):
    """获取作者全部论文"""
    all_works = []
    try:
        for page in Works().filter(
            author={"id": author_id}
        ).sort(publication_year="desc").paginate(per_page=200, n_max=max_works):
            all_works.extend(page)
    except Exception as e:
        print(f"  [!] 获取论文失败: {e}")
    return all_works


def build_member_profile(name, max_works=300, affiliation_hint=None):
    """构建单个成员的画像"""
    print(f"  查询: {name}...")
    author = find_author(name, affiliation_hint=affiliation_hint)
    if not author:
        return {"name": name, "status": "not_found"}

    author_id = author.get("id", "").replace("https://openalex.org/", "")
    display_name = author.get("display_name", name)

    profile = {
        "name": display_name,
        "openalex_id": author_id,
        "orcid": author.get("orcid"),
        "works_count": author.get("works_count", 0),
        "cited_by_count": author.get("cited_by_count", 0),
        "h_index": author.get("summary_stats", {}).get("h_index"),
        "affiliations": [],
        "top_papers": [],
        "coauthors": {},  # name -> count
        "yearly_stats": {},  # year -> paper_count
    }

    # 机构历史
    for aff in author.get("affiliations", []):
        inst = aff.get("institution", {})
        years = aff.get("years", [])
        profile["affiliations"].append({
            "institution": inst.get("display_name", ""),
            "years": f"{min(years)}-{max(years)}" if years else "N/A",
        })

    # 获取论文
    time.sleep(0.15)
    works = get_author_works(author_id, max_works)

    # 年度统计
    for w in works:
        year = w.get("publication_year")
        if year:
            profile["yearly_stats"][year] = profile["yearly_stats"].get(year, 0) + 1

    # Top papers by citation
    sorted_works = sorted(works, key=lambda x: x.get("cited_by_count", 0), reverse=True)
    for w in sorted_works[:10]:
        source = w.get("primary_location", {})
        source_name = ""
        if source and source.get("source"):
            source_name = source["source"].get("display_name", "")

        profile["top_papers"].append({
            "title": w.get("title", ""),
            "year": w.get("publication_year"),
            "venue": source_name,
            "cited_by_count": w.get("cited_by_count", 0),
        })

    # 合作者统计
    author_full_id = author.get("id", "")
    for w in works:
        for authorship in w.get("authorships", []):
            co = authorship.get("author", {})
            co_id = co.get("id", "")
            co_name = co.get("display_name", "")
            if co_id and co_id != author_full_id and co_name:
                profile["coauthors"][co_name] = profile["coauthors"].get(co_name, 0) + 1

    # 只保留合作>=2次的
    profile["coauthors"] = {
        k: v for k, v in sorted(
            profile["coauthors"].items(), key=lambda x: -x[1]
        ) if v >= 2
    }

    time.sleep(0.2)
    return profile


def find_pi_students(pi_name, pi_profile, all_profiles):
    """通过PI的合作者推断学生列表（辅助信息）"""
    if not pi_profile or pi_profile.get("status") == "not_found":
        return []

    # PI的合作者中，与PI合作>=3次且在同机构的年轻学者
    pi_insts = {a["institution"] for a in pi_profile.get("affiliations", [])}
    potential_students = []

    for co_name, count in pi_profile.get("coauthors", {}).items():
        if count >= 3:
            # 检查是否已在成员列表中
            is_member = any(
                p.get("name", "").lower() == co_name.lower()
                for p in all_profiles
            )
            potential_students.append({
                "name": co_name,
                "collaborations_with_pi": count,
                "already_in_list": is_member,
            })

    return potential_students[:30]


def build_collaboration_matrix(profiles):
    """构建成员间合作矩阵"""
    names = [p["name"] for p in profiles if p.get("status") != "not_found"]
    matrix = {}

    for p in profiles:
        if p.get("status") == "not_found":
            continue
        pname = p["name"]
        matrix[pname] = {}
        coauthors = p.get("coauthors", {})
        for other_name in names:
            if other_name == pname:
                continue
            # 模糊匹配合作者名称
            count = 0
            for co_name, co_count in coauthors.items():
                if _name_match(co_name, other_name):
                    count = co_count
                    break
            if count > 0:
                matrix[pname][other_name] = count

    return matrix


def _name_match(name1, name2):
    """模糊匹配两个名字（处理大小写、名字顺序差异）"""
    n1 = name1.lower().strip()
    n2 = name2.lower().strip()
    if n1 == n2:
        return True
    # 比较名字的词集合
    parts1 = set(n1.split())
    parts2 = set(n2.split())
    if len(parts1 & parts2) >= 2:
        return True
    return False


def find_external_collaborations(profiles):
    """汇总外部合作网络（不在成员名单中的高频合作者）"""
    member_names = {p["name"].lower() for p in profiles if p.get("status") != "not_found"}
    external = defaultdict(lambda: {"total_collabs": 0, "collaborators_in_lab": []})

    for p in profiles:
        if p.get("status") == "not_found":
            continue
        for co_name, count in p.get("coauthors", {}).items():
            # 检查是否为外部合作者
            is_internal = any(_name_match(co_name, mn) for mn in member_names)
            if not is_internal and count >= 3:
                external[co_name]["total_collabs"] += count
                external[co_name]["collaborators_in_lab"].append(
                    {"member": p["name"], "count": count}
                )

    # 排序
    return dict(sorted(external.items(), key=lambda x: -x[1]["total_collabs"])[:20])


def print_report(profiles, matrix, external_collabs, pi_students=None):
    """打印实验室画像报告"""
    found = [p for p in profiles if p.get("status") != "not_found"]
    not_found = [p for p in profiles if p.get("status") == "not_found"]

    print("\n" + "=" * 80)
    print("  实验室全景画像报告")
    print("=" * 80)
    print(f"\n  成员数: {len(found)} (查询到) / {len(profiles)} (输入)")
    if not_found:
        print(f"  未找到: {', '.join(p['name'] for p in not_found)}")

    # 每位成员画像
    for p in found:
        print(f"\n{'─' * 80}")
        print(f"  {p['name']}")
        print(f"{'─' * 80}")
        print(f"  ID: {p.get('openalex_id', 'N/A')} | ORCID: {p.get('orcid', 'N/A')}")
        print(f"  论文: {p.get('works_count', 0)} | 被引: {p.get('cited_by_count', 0)} | h-index: {p.get('h_index', 'N/A')}")

        # 机构
        affs = p.get("affiliations", [])
        if affs:
            aff_str = "; ".join(f"{a['institution']}({a['years']})" for a in affs[:3])
            print(f"  机构: {aff_str}")

        # 年度发表
        yearly = p.get("yearly_stats", {})
        if yearly:
            recent = {y: c for y, c in yearly.items() if y and y >= 2020}
            if recent:
                yr_str = ", ".join(f"{y}:{c}" for y, c in sorted(recent.items()))
                print(f"  近年发表: {yr_str}")

        # 代表作
        top = p.get("top_papers", [])[:5]
        if top:
            print(f"  代表作:")
            for paper in top:
                venue = paper.get("venue", "")
                venue_short = venue[:30] + "..." if len(venue) > 30 else venue
                print(f"    • ({paper['year']}) {paper['title'][:60]} [{venue_short}, cited:{paper['cited_by_count']}]")

        # 组内合作
        internal = matrix.get(p["name"], {})
        if internal:
            int_str = ", ".join(f"{n}({c})" for n, c in sorted(internal.items(), key=lambda x: -x[1])[:5])
            print(f"  组内合作: {int_str}")

    # 合作矩阵
    print(f"\n{'═' * 80}")
    print(f"  成员间合作矩阵")
    print(f"{'═' * 80}")
    for member, collabs in matrix.items():
        if collabs:
            collab_str = ", ".join(f"{n}({c})" for n, c in sorted(collabs.items(), key=lambda x: -x[1]))
            print(f"  {member}: {collab_str}")

    # 外部合作
    print(f"\n{'═' * 80}")
    print(f"  外部合作网络 (Top 20)")
    print(f"{'═' * 80}")
    for ext_name, info in list(external_collabs.items())[:20]:
        labs = ", ".join(f"{c['member']}({c['count']})" for c in info["collaborators_in_lab"])
        print(f"  {ext_name} [总{info['total_collabs']}次]: {labs}")

    # PI的潜在学生
    if pi_students:
        print(f"\n{'═' * 80}")
        print(f"  PI高频合作者（可能的学生/博后，未在名单中）")
        print(f"{'═' * 80}")
        unlisted = [s for s in pi_students if not s["already_in_list"]]
        for s in unlisted[:15]:
            print(f"  {s['name']} (合作{s['collaborations_with_pi']}次)")

    print(f"\n{'═' * 80}\n")


def save_report(profiles, matrix, external_collabs, pi_students, output_path):
    """保存JSON报告"""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    report = {
        "generated_at": datetime.now().isoformat(),
        "total_members": len(profiles),
        "members": [],
        "collaboration_matrix": matrix,
        "external_collaborations": external_collabs,
        "potential_students": pi_students,
    }

    for p in profiles:
        # 序列化 coauthors（只保留top 20）
        coauthors_top = dict(list(p.get("coauthors", {}).items())[:20])
        member = {**p, "coauthors": coauthors_top}
        report["members"].append(member)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  报告已保存: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="实验室全景画像辅助工具 — 批量查询成员论文/引用/合作者并分析合作网络"
    )
    parser.add_argument("--pi", type=str, help="PI姓名（将额外分析其学生网络）")
    parser.add_argument("--members", nargs="+", help="成员姓名列表")
    parser.add_argument("--members-file", type=str, help="成员名单文件（每行一个）")
    parser.add_argument("--affiliation", type=str, help="机构名称提示，用于消歧重名（如 'Tsinghua'）")
    parser.add_argument("--max-works", type=int, default=300, help="每人最大论文检索数")
    parser.add_argument("--output", type=str, help="输出JSON报告路径")
    args = parser.parse_args()

    # 收集成员名单
    members = []
    if args.pi:
        members.append(args.pi)
    if args.members:
        members.extend(args.members)
    if args.members_file:
        try:
            with open(args.members_file, "r") as f:
                for line in f:
                    name = line.strip()
                    if name and not name.startswith("#"):
                        members.append(name)
        except FileNotFoundError:
            print(f"  [!] 文件不存在: {args.members_file}")
            sys.exit(1)

    if not members:
        parser.error("请提供 --pi、--members 或 --members-file")

    # 去重保序
    seen = set()
    unique_members = []
    for m in members:
        if m.lower() not in seen:
            seen.add(m.lower())
            unique_members.append(m)
    members = unique_members

    print("=" * 80)
    print("  实验室全景画像辅助工具")
    print("=" * 80)
    print(f"\n  待查询成员: {len(members)} 位")
    print(f"  {', '.join(members)}\n")

    # 批量查询
    profiles = []
    for name in members:
        profile = build_member_profile(name, max_works=args.max_works,
                                       affiliation_hint=args.affiliation)
        profiles.append(profile)
        time.sleep(0.3)

    # 构建合作矩阵
    print("\n🔗 构建成员间合作矩阵...")
    matrix = build_collaboration_matrix(profiles)

    # 外部合作网络
    print("🌐 分析外部合作网络...")
    external_collabs = find_external_collaborations(profiles)

    # PI学生分析
    pi_students = None
    if args.pi:
        pi_profile = next((p for p in profiles if _name_match(p.get("name", ""), args.pi)), None)
        if pi_profile:
            print("🎓 分析PI的学生网络...")
            pi_students = find_pi_students(args.pi, pi_profile, profiles)

    # 输出
    print_report(profiles, matrix, external_collabs, pi_students)

    if args.output:
        save_report(profiles, matrix, external_collabs, pi_students or [], args.output)


if __name__ == "__main__":
    main()
