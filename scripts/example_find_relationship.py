"""
示例：查询两位学者的学术关系

用法:
    python scripts/example_find_relationship.py

可通过修改 main() 中的学者信息来查询任意两人的学术关系。
支持通过 ORCID、OpenAlex ID 或姓名来定位学者。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "third_party", "pyalex"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from academiconnection import RelationshipFinder


def main():
    finder = RelationshipFinder()

    # 定位学者 A（可用 name、orcid 或 openalex_id）
    print("正在定位学者...")
    scholar_a = finder.find_scholar(name="Yann LeCun")
    print(f"  学者 A: {scholar_a.name} ({scholar_a.openalex_id})")
    print(f"    机构: {scholar_a.institutions}")

    # 定位学者 B
    scholar_b = finder.find_scholar(name="Geoffrey Hinton")
    print(f"  学者 B: {scholar_b.name} ({scholar_b.openalex_id})")
    print(f"    机构: {scholar_b.institutions}")

    # 查询关系
    print("\n正在查询学术关系（可能需要 30-60 秒）...")
    result = finder.find_relationship(scholar_a, scholar_b, max_works=100)

    # 打印报告
    finder.print_report(result)


if __name__ == "__main__":
    main()
