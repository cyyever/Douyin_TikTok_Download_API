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
import json
import asyncio
import re

from httpx import Response

from crawlers.utils.logger import logger
from crawlers.utils.api_exceptions import (
    APIError,
    APIConnectionError,
    APIResponseError,
    APIRetryExhaustedError,
)


class BaseCrawler:
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
        # 业务逻辑重试次数 / Business logic retry count
        self._max_retries = max_retries

        # 超时等待时间 / Timeout waiting time
        self._timeout = timeout
        self.timeout = httpx.Timeout(timeout)
        # 异步客户端 / Asynchronous client
        self.aclient = httpx.AsyncClient(
            headers=crawler_headers or {},
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=max_connections),
            transport=httpx.AsyncHTTPTransport(retries=max_retries),
        )

    async def fetch_get_json(self, endpoint: str) -> dict:
        """获取 JSON 数据 (Get JSON data)

        Args:
            endpoint (str): 接口地址 (Endpoint URL)

        Returns:
            dict: 解析后的JSON数据 (Parsed JSON data)
        """
        response = await self.fetch_response(endpoint)
        return self.parse_json(response)

    async def fetch_post_json(
        self, endpoint: str, params: dict = {}, data=None
    ) -> dict:
        """获取 JSON 数据 (Post JSON data)

        Args:
            endpoint (str): 接口地址 (Endpoint URL)

        Returns:
            dict: 解析后的JSON数据 (Parsed JSON data)
        """
        response = await self.post_fetch_data(endpoint, params, data)
        return self.parse_json(response)

    def parse_json(self, response: Response | None) -> dict:
        """解析JSON响应对象 (Parse JSON response object)

        Args:
            response (Response): 原始响应对象 (Raw response object)

        Returns:
            dict: 解析后的JSON数据 (Parsed JSON data)
        """
        if (
            response is not None
            and isinstance(response, Response)
            and response.status_code == 200
        ):
            try:
                return response.json()
            except json.JSONDecodeError:
                # 尝试使用正则表达式匹配response.text中的json数据
                match = re.search(r"\{.*\}", response.text)
                if match is None:
                    raise APIResponseError("解析JSON数据失败 " + response.text)

                try:
                    return json.loads(match.group())
                except json.JSONDecodeError as e:
                    logger.error(
                        "解析 {0} 接口 JSON 失败： {1}".format(response.url, e)
                    )
                    raise APIResponseError("解析JSON数据失败")

        if isinstance(response, Response):
            logger.error("获取数据失败。状态码: {0}".format(response.status_code))
        else:
            logger.error("无效响应类型。响应类型: {0}".format(type(response)))

        raise APIResponseError("获取数据失败")

    async def fetch_response(self, url: str):
        """
        获取GET端点数据 (Get GET endpoint data)

        Args:
            url (str): 端点URL (Endpoint URL)

        Returns:
            response: 响应内容 (Response content)
        """
        for attempt in range(self._max_retries):
            try:
                response = await self.aclient.get(url, follow_redirects=True)
                if not response.text.strip() or not response.content:
                    error_message = (
                        "第 {0} 次响应内容为空, 状态码: {1}, URL:{2}".format(
                            attempt + 1, response.status_code, response.url
                        )
                    )

                    logger.warning(error_message)

                    if attempt == self._max_retries - 1:
                        raise APIRetryExhaustedError("获取端点数据失败, 次数达到上限")

                    await asyncio.sleep(self._timeout)
                    continue

                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as http_error:
                self.handle_http_status_error(http_error, url, attempt + 1)
                raise http_error

    async def post_fetch_data(self, url: str, params: dict | None = None, data=None):
        """
        获取POST端点数据 (Get POST endpoint data)

        Args:
            url (str): 端点URL (Endpoint URL)
            params (dict): POST请求参数 (POST request parameters)

        Returns:
            response: 响应内容 (Response content)
        """
        for attempt in range(self._max_retries):
            try:
                response = await self.aclient.post(
                    url,
                    json=None if not params else dict(params),
                    data=None if not data else data,
                    follow_redirects=True,
                )
                if not response.text.strip() or not response.content:
                    error_message = (
                        "第 {0} 次响应内容为空, 状态码: {1}, URL:{2}".format(
                            attempt + 1, response.status_code, response.url
                        )
                    )

                    logger.warning(error_message)

                    if attempt == self._max_retries - 1:
                        raise APIRetryExhaustedError("获取端点数据失败, 次数达到上限")

                    await asyncio.sleep(self._timeout)
                    continue

                # logger.info("响应状态码: {0}".format(response.status_code))
                response.raise_for_status()
                return response

            except httpx.RequestError:
                raise APIConnectionError(
                    "连接端点失败，检查网络环境或代理：{0} ".format(url)
                )

            except httpx.HTTPStatusError as http_error:
                self.handle_http_status_error(http_error, url, attempt + 1)
                raise http_error

            except APIError as e:
                e.display_error()

    def handle_http_status_error(
        self, http_error: httpx.HTTPStatusError, url: str, attempt: int
    ):
        """
        处理HTTP状态错误 (Handle HTTP status error)

        Args:
            http_error: HTTP状态错误 (HTTP status error)
            url: 端点URL (Endpoint URL)
            attempt: 尝试次数 (Number of attempts)
        """
        response = http_error.response
        status_code = response.status_code

        logger.error(
            "HTTP状态错误: {0}, URL: {1}, 尝试次数: {2}".format(
                status_code, url, attempt
            )
        )

    async def close(self):
        await self.aclient.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclient.aclose()
