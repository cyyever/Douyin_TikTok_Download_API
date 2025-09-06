# ==============================================================================
# Copyright (C) 2021 Evil0ctal
#
# This file is part of the Douyin_TikTok_Download_API project.
#
# This project is licensed under the Apache License 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
# 　　　　 　　  ＿＿
# 　　　 　　 ／＞　　フ
# 　　　 　　| 　_　 _ l
# 　 　　 　／` ミ＿xノ
# 　　 　 /　　　 　 |       Feed me Stars ⭐
# 　　　 /　 ヽ　　 ﾉ
# 　 　 │　　|　|　|
# 　／￣|　　 |　|　|
# 　| (￣ヽ＿_ヽ_)__)
# 　＼二つ
# ==============================================================================
#
# Contributor Link:
# - https://github.com/Evil0ctal
# - https://github.com/Johnserf-Seed
#
# ==============================================================================

import httpx

from httpx import Response

from crawlers.utils.logger import logger


class BaseCrawler(httpx.AsyncClient):
    """
    基础爬虫客户端 (Base crawler client)
    """

    def __init__(
        self,
        max_retries: int = 3,
        max_connections: int = 50,
        timeout: int = 10,
        crawler_headers: dict | None = None,
    ):
        # 异步客户端 / Asynchronous client
        super().__init__(
            headers=crawler_headers or {},
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=max_connections),
            transport=httpx.AsyncHTTPTransport(retries=max_retries),
        )

    async def get_json(self, *args, **kwargs) -> dict:
        """获取 JSON 数据 (Get JSON data)

        Args:
            endpoint (str): 接口地址 (Endpoint URL)

        Returns:
            dict: 解析后的JSON数据 (Parsed JSON data)
        """
        response = await self.get(*args, **kwargs)
        return self.parse_json(response)

    def parse_json(self, response: Response) -> dict:
        """解析JSON响应对象 (Parse JSON response object)

        Args:
            response (Response): 原始响应对象 (Raw response object)

        Returns:
            dict: 解析后的JSON数据 (Parsed JSON data)
        """
        result = response.json()
        if not result:
            raise RuntimeError("invalid json response " + str(response))
        return result

    async def get(self, *args, **kwargs):
        """
        获取GET端点数据 (Get GET endpoint data)

        Args:
            url (str): 端点URL (Endpoint URL)

        Returns:
            response: 响应内容 (Response content)
        """
        response = await super().get(*args, **kwargs)
        if not response.text.strip():
            error_message = "响应内容为空, 状态码: {0}, URL:{1}".format(
                response.status_code, response.url
            )

            logger.warning(error_message)

        response.raise_for_status()
        return response
