"""搜索服务商端口协议。"""

from __future__ import annotations

from typing import Any, Dict, Protocol


class SearchProviderPort(Protocol):
    """搜索适配器端口。"""

    provider_type: str

    def scrape(self, url: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """抓取网页正文。"""
        ...

    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """测试搜索服务商连通性。"""
        ...
