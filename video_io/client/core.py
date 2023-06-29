import asyncio
import concurrent.futures
from datetime import datetime
from io import BytesIO
import json
from json.decoder import JSONDecodeError
import logging
import os
from pathlib import Path
from typing import List, Dict, Union, Optional

from cachetools import TTLCache
import requests
from requests.adapters import HTTPAdapter
import tenacity
import yaml

import video_io.config
from video_io.log_retry import LogRetry
from video_io.client.errors import SyncError
from video_io.errors import BadVideoError
from video_io.client.utils import (
    client_token,
    parse_path,
    get_video_file_details,
    chunks,
    FPS_PATH,
)


logger = logging.getLogger(__name__)


UPLOAD_FAILED_REASON_BAD_VIDEO = "BAD_VIDEO"
UPLOAD_FAILED_REASON_BAD_PATH_TO_VIDEO = "BAD_PATH_TO_VIDEO"


class VideoStorageClient:
    DEFAULT_CONNECTION_POOL_SIZE = 10

    def __init__(
        self,
        token=None,
        cache_directory=video_io.config.VIDEO_STORAGE_LOCAL_CACHE_DIRECTORY,
        url=video_io.config.VIDEO_STORAGE_URL,
        auth_domain=video_io.config.VIDEO_STORAGE_AUTH_DOMAIN,
        audience=video_io.config.VIDEO_STORAGE_AUDIENCE,
        client_id=video_io.config.VIDEO_STORAGE_CLIENT_ID,
        client_secret=video_io.config.HONEYCOMB_CLIENT_SECRET,
        connection_pool_size: Optional[int] = None,
    ):
        self.CACHE_DIRECTORY = cache_directory
        self.URL = url

        self.auth_domain = auth_domain
        self.audience = audience
        self.client_id = client_id
        self.client_secret = client_secret

        self.headers = {}  # {"Content-Type": "application/json"}

        self.tokens = {}
        if token is not None:
            self.tokens["access_token"] = token

        self.request_session = self.init_request_session(
            connection_pool_size=connection_pool_size
        )

    @staticmethod
    def init_request_session(connection_pool_size=None):
        retry_strategy = LogRetry(
            total=6,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS", "POST"],
            backoff_factor=0.5,
        )
        _connection_pool_size = connection_pool_size
        if _connection_pool_size is None:
            _connection_pool_size = VideoStorageClient.DEFAULT_CONNECTION_POOL_SIZE

        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=_connection_pool_size,
            pool_maxsize=_connection_pool_size,
        )
        request_session = requests.Session()
        request_session.mount("https://", adapter)
        request_session.mount("http://", adapter)
        return request_session

    def refresh_token(self):
        try:
            (token, expires_in) = client_token(
                auth_domain=self.auth_domain,
                audience=self.audience,
                client_id=self.client_id,
                client_secret=self.client_secret,
            )
            if token is None:
                raise Exception("invalid client_credentials")

            # Refresh token once TTL is less than 5 minutes
            self.tokens = TTLCache(maxsize=1, ttl=expires_in - 300)
            self.tokens["access_token"] = token
        except Exception as err:
            import traceback

            logger.error("An exception occurred during Authorization")
            traceback.print_exception(err)
            raise Exception("invalid client_credentials") from err

    @property
    def headers(self):
        if "access_token" not in self.tokens:
            self.refresh_token()

        return {
            "Authorization": f"Bearer {self.tokens['access_token']}",
            **self._headers,
        }

    @headers.setter
    def headers(self, header_dict: dict):
        self._headers = header_dict

    async def get_videos(
        self,
        environment_id: str,
        start_date: datetime,
        end_date: datetime,
        camera_id: str = None,
        destination: Union[Path, str] = None,
    ):
        if destination is None:
            destination = self.CACHE_DIRECTORY
        if not hasattr(destination, "mkdir"):
            destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        meta = self.get_videos_metadata_paginated(
            environment_id=environment_id,
            start_date=start_date,
            end_date=end_date,
            camera_id=camera_id,
        )
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as e:
            async for vid_meta in meta:
                f = e.submit(
                    asyncio.run,
                    self.get_video(
                        path=vid_meta["meta"]["path"], destination=destination
                    ),
                )
                futures.append(f)
        list(concurrent.futures.as_completed(futures))

    @tenacity.retry(
        wait=tenacity.wait_incrementing(start=5, increment=1),
        stop=tenacity.stop_after_attempt(3),
        retry=tenacity.retry_if_exception_type(requests.exceptions.RequestException),
    )
    async def get_video(self, path: str, destination: str, overwrite: bool = False):
        p = Path(destination) / path

        if p.is_file():
            try:
                get_video_file_details(p.absolute())
            except Exception as e:
                logger.error(
                    f"Could not ffprobe video file {p.absolute()} - {e}. Removing file and attempting to re-download"
                )
                os.remove(p.absolute())

        if not p.is_file() or overwrite:
            logger.info("Downloading video file %s", path)
            request = {
                "method": "GET",
                "url": f"{self.URL}/video/{path}/data",
                "headers": self.headers,
                "timeout": 45,
            }
            try:
                response = self.request_session.request(**request)
                response.raise_for_status()

                pp = p.parent
                if not pp.exists():
                    pp.mkdir(parents=True, exist_ok=True)
                p.write_bytes(response.content)
                logger.info("Video file %s finished downloading", path)
            except requests.exceptions.HTTPError as e:
                logger.error(
                    "Failing fetching video file %s with HTTP error code %s",
                    path,
                    e.response.status_code,
                )
                raise e
            except requests.exceptions.RequestException as e:
                logger.error(
                    "Failing fetching video file %s with exception %s", path, e
                )
                raise e
        else:
            logger.info("Video file %s already exists", path)

    async def get_videos_metadata_paginated(
        self,
        environment_id: str,
        start_date: datetime,
        end_date: datetime,
        camera_id: str = None,
        skip: int = 0,
        limit: int = 1000,
    ):
        current_skip = skip
        while True:
            page = await self.get_videos_metadata(
                environment_id,
                start_date,
                end_date,
                camera_id=camera_id,
                skip=current_skip,
                limit=limit,
            )
            for item in page:
                yield item
            current_skip += limit
            if len(page) == 0:
                break

    @tenacity.retry(
        wait=tenacity.wait_incrementing(start=5, increment=1),
        stop=tenacity.stop_after_attempt(3),
        retry=tenacity.retry_if_exception_type(requests.exceptions.RequestException),
    )
    async def get_videos_metadata(
        self, environment_id, start_date, end_date, camera_id=None, skip=0, limit=1000
    ):
        request = {
            "method": "GET",
            "url": f"{self.URL}/videos/{environment_id}/device/{camera_id}"
            if camera_id is not None
            else f"{self.URL}/videos/{environment_id}",
            "headers": self.headers,
            "params": {
                "start_date": start_date,
                "end_date": end_date,
                "skip": skip,
                "limit": limit,
            },
            "timeout": 120,
        }
        try:
            response = requests.request(**request)
            response.raise_for_status()

            data = response.json()
            return data
        except requests.exceptions.HTTPError as e:
            logger.error(
                "Failing fetching video metadata for %s from %s to %s with HTTP error code %s",
                environment_id,
                start_date,
                end_date,
                e.response.status_code,
            )
            raise e
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failing fetching video metadata for %s from %s to %s with exception %s",
                environment_id,
                start_date,
                end_date,
                e,
            )
            raise e

    async def upload_video(self, path: str, local_cache_directory: str = None):
        response = await self.upload_videos(
            paths=[path], local_cache_directory=local_cache_directory
        )
        return response[0]

    async def upload_videos(self, paths: List[str], local_cache_directory: str = None):
        if local_cache_directory is None:
            local_cache_directory = self.CACHE_DIRECTORY

        bad_file_results: List[dict] = []
        all_file_details: List[dict] = []
        for path in paths:
            full_path = local_cache_directory / path
            ptype, file_details = parse_path(path)
            if ptype == "file":
                file_details["ptype"] = ptype
                file_details["path"] = full_path
                file_details["filepath"] = path
                all_file_details.append(file_details)
            else:
                bad_file_results.append(
                    {
                        "id": None,
                        "path": path,
                        "uploaded": False,
                        "upload_failed_reason": UPLOAD_FAILED_REASON_BAD_PATH_TO_VIDEO,
                        "upload_failed_error": f"Invalid path. '{path}' doesn't match pattern [environment_id]/[camera_id]/[year]/[month]/[day]/[hour]/[min]-[second].mp4",
                        "disposition": None,
                    }
                )

        upload_results = []
        if len(all_file_details) > 0:
            upload_results = await self._upload_videos(all_file_details)
        return [*upload_results, *bad_file_results]

    def prepare_video(self, file_details: Dict) -> (Dict, BytesIO):
        path = file_details["path"]

        try:
            video_properties = get_video_file_details(path)
        except Exception as e:
            raise BadVideoError(
                f"Could not ffprobe video file {file_details['path']} - {e}"
            ) from e

        if file_details["ptype"] == "file":
            ts = f"{file_details['year']}-{file_details['month']}-{file_details['day']}T{file_details['hour']}:{file_details['file'][0:2]}:{file_details['file'][3:5]}.0000"
            meta = {
                "timestamp": ts,
                "meta": {
                    "environment_id": file_details["environment_id"],
                    "camera_id": file_details["camera_id"],
                    "duration_seconds": video_properties["format"]["duration"],
                    "fps": eval(
                        FPS_PATH.search(video_properties)[0]
                    ),  # pylint: disable=W0123
                    "path": file_details["filepath"],
                },
            }
        else:
            p = Path(f"{path}.meta")
            if not p.exists():
                logger.error("missing meta file for video %s", path)
                return {"error": f"meta is missing for {path}"}
            with p.open("r", encoding="utf8") as fp:
                meta = yaml.safe_load(fp.read())
        return (
            meta,
            open(path, "rb"),  # pylint: disable=R1732
        )

    @tenacity.retry(
        wait=tenacity.wait_incrementing(start=5, increment=1),
        stop=tenacity.stop_after_attempt(3),
        retry=tenacity.retry_if_exception_type(requests.exceptions.RequestException),
    )
    async def _upload_videos(self, file_details: List[Dict]):
        request = {
            "method": "POST",
            "url": f"{self.URL}/videos",
            "headers": self.headers,
        }

        files = []
        videos = []
        results = []
        for details in file_details:
            try:
                meta, fileio = self.prepare_video(details)
            except BadVideoError as e:
                results.append(
                    {
                        "id": None,
                        "path": details["filepath"],
                        "uploaded": False,
                        "upload_failed_reason": UPLOAD_FAILED_REASON_BAD_VIDEO,
                        "upload_failed_error": str(e),
                        "disposition": None,
                    }
                )
                continue

            files.append(
                (
                    "files",
                    fileio,
                )
            )
            videos.append(meta)

        request["files"] = files
        request["data"] = {"videos": json.dumps(videos)}
        try:
            request = requests.Request(**request)
            r = request.prepare()
            response = self.request_session.send(r, timeout=45)
            response.raise_for_status()

            for ii, vr in enumerate(response.json()):
                results.append(
                    {
                        "path": videos[ii]["meta"]["path"],
                        "uploaded": True,
                        "upload_failed_reason": None,
                        "upload_failed_error": None,
                        "id": vr["id"],
                        "disposition": "ok"
                        if "disposition" not in vr
                        else vr["disposition"],
                    }
                )
            return results
        except JSONDecodeError as je:
            logger.error(
                "Unusual response from video-service for %s: %s",
                file_details,
                je.msg,
            )
            raise je
        except requests.exceptions.HTTPError as e:
            logger.error(
                "Failing uploading videos %s with HTTP error code %s",
                file_details,
                e.response.status_code,
            )
            raise e
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failing uploading videos %s with exception %s", file_details, e
            )
            raise e

    async def video_existence_check(self, paths: List[str]):
        request = {
            "method": "POST",
            "url": f"{self.URL}/videos/check",
            "headers": self.headers,
            "json": paths,
        }
        try:
            r = requests.Request(**request).prepare()
            response = self.request_session.send(r, timeout=45)
            try:
                return response.json()
            except Exception:
                print(response.text)
                return [
                    {"err": "response error", "path": p, "exists": False} for p in paths
                ]
        except requests.exceptions.HTTPError as e:
            logger.error(
                "Failing validating video existence %s with HTTP error code %s",
                paths,
                e.response.status_code,
            )
            raise e
        except requests.exceptions.RequestException as e:
            logger.error("Failing validating video existence %s exception %s", paths, e)
            raise e

    async def upload_videos_in(
        self,
        path,
        local_cache_directory=None,
        batch_size=video_io.config.SYNC_BATCH_SIZE,
        max_workers=video_io.config.MAX_SYNC_WORKERS,
    ):
        if local_cache_directory is None:
            local_cache_directory = self.CACHE_DIRECTORY
        local_cache_directory = Path(local_cache_directory)
        strpath = str(path)
        t, details = parse_path(strpath[:-1] if strpath[-1] == "/" else strpath)
        if details:
            if t in ("file", "fileV2"):
                raise SyncError(
                    "didn't expect file, expected directory, try `upload_video`"
                )
            if t == "year":
                raise SyncError("cannot sync a year of videos, try limiting to a day")
            if t == "month":
                raise SyncError("cannot sync a month of videos, try limiting to a day")
            if t == "environment":
                logger.warning(
                    "syncing an entire environment is crazy, I hope you know what you are doing."
                )
            files_found = []
            for root, _, files in os.walk(local_cache_directory / path):
                for file in files:
                    full_path = Path(os.path.join(root, file))
                    ptype, file_details = parse_path(
                        str(full_path.relative_to(local_cache_directory))
                    )
                    if ptype in ("file", "fileV2") and full_path.suffix in [
                        ".h264",
                        ".mp4",
                    ]:
                        file_details["ptype"] = ptype
                        file_details["path"] = full_path
                        file_details["filepath"] = path
                        files_found.append(file_details)
            details["files_found"] = len(files_found)
            details["files_uploaded"] = 0
            details["details"] = []
            logger.debug(f"found {len(files_found)} files to be uploaded")
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers
            ) as executor:
                results = executor.map(
                    self._upload_videos, chunks(files_found, batch_size)
                )
                logger.debug(results)
                for result in await asyncio.gather(*results):
                    logger.debug(result)
                    for data in result:
                        if data["uploaded"]:
                            details["files_uploaded"] += 1
                        details["details"].append(data)
            return details
        raise SyncError("path {path} was not parsable")
