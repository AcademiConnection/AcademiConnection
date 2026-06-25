"""AcademiConnection 安装配置"""

from setuptools import setup, find_packages

setup(
    name="academiconnection",
    version="0.1.0",
    description="科研人员关系网络构建工具",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.28.0",
        "networkx>=3.0",
        "python-dotenv>=1.0.0",
    ],
)
