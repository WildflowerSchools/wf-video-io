import video_io.config
import concurrent.futures
import datetime
import logging
import math
import asyncio
import os
from pathlib import Path

import boto3
import cv_utils
import cv2 as cv
import honeycomb_io

from video_io.client import client_from_honeycomb_settings

logger = logging.getLogger(__name__)

VIDEO_DURATION = datetime.timedelta(seconds=10)

async def fetch_videos(
    start=None,
    end=None,
    video_timestamps=None,
    camera_assignment_ids=None,
    environment_id=None,
    environment_name=None,
    camera_device_types=None,
    camera_device_ids=None,
    camera_part_numbers=None,
    camera_names=None,
    camera_serial_numbers=None,
    chunk_size=100,
    client=None,
    local_video_directory='./videos',
    video_filename_extension=None,
    max_workers=video_io.config.MAX_DOWNLOAD_WORKERS,
    uri=video_io.config.HONEYCOMB_URI,
    token_uri=video_io.config.HONEYCOMB_TOKEN_URI,
    audience=video_io.config.HONEYCOMB_AUDIENCE,
    client_id=video_io.config.HONEYCOMB_CLIENT_ID,
    client_secret=video_io.config.HONEYCOMB_CLIENT_SECRET
):
    """
    Downloads videos that match search parameters and returns their metadata.

    This function simply combines the operations of fetch_video_metadata() and
    download_video_files(). See documentation of those functions for details.

    Args:
        start (datetime): Start of time period to fetch (default is None)
        end (datetime): End of time period to fetch (default is None)
        video_timestamps (list of datetime): List of video start times to fetch (default is None)
        camera_assignment_ids (list of str): Honeycomb assignment IDs (default is None)
        environment_id (str): Honeycomb environment ID (default is None)
        environment_name (str): Honeycomb environment name (default is None)
        camera_device_types (list of str): Honeycomb device types (default is None)
        camera_device_ids (list of str): Honeycomb device IDs (default is None)
        camera_part_numbers (list of str): Honeycomb device part numbers (default is None)
        camera_names (list of str): Honeycomb device names (default is None)
        camera_serial_numbers (list of str): Honeycomb device serial numbers (default is None)
        chunk_size (int): Maximum number of data points to be returned by each Honeycomb query (default is 100)
        client (MinimalHoneycombClient): Existing Honeycomb client (otherwise will create one)
        uri (str): Server URI for creating Honeycomb client (default is value of HONEYCOMB_URI environment variable)
        token_uri (str): Token URI for creating Honeycomb client (default is value of HONEYCOMB_TOKEN_URI environment variable)
        audience (str): Audience for creating Honeycomb client (default is value of HONEYCOMB_AUDIENCE environment variable)
        client_id: Client ID for creating Honeycomb client (default is value of HONEYCOMB_CLIENT_ID environment variable)
        client_secret: Client secret for creating Honeycomb client (default is value of HONEYCOMB_CLIENT_SECRET environment variable)
        local_video_directory (str): Base of local video tree (default is './videos')
        video_filename_extension (str): Filename extension for video files (default is 'mp4')

    Returns:
        (list of dict): Metadata for videos with local path information appended
    """
    logger.info('Fetching metadata for videos that match specified parameters')
    video_metadata = await fetch_video_metadata(
        start=start,
        end=end,
        video_timestamps=video_timestamps,
        camera_assignment_ids=camera_assignment_ids,
        environment_id=environment_id,
        environment_name=environment_name,
        camera_device_types=camera_device_types,
        camera_device_ids=camera_device_ids,
        camera_part_numbers=camera_part_numbers,
        camera_names=camera_names,
        camera_serial_numbers=camera_serial_numbers,
        chunk_size=chunk_size,
        client=client,
        uri=uri,
        token_uri=token_uri,
        audience=audience,
        client_id=client_id,
        client_secret=client_secret
    )
    logger.info('Downloading video files')
    video_metadata_with_local_paths = await download_video_files(
        video_metadata=video_metadata,
        local_video_directory=local_video_directory,
        video_filename_extension=video_filename_extension,
        max_workers=max_workers,
        token_uri=token_uri,
        audience=audience,
        client_id=client_id,
        client_secret=client_secret
    )
    return video_metadata_with_local_paths

async def fetch_images(
    image_timestamps,
    camera_assignment_ids=None,
    environment_id=None,
    environment_name=None,
    camera_device_types=None,
    camera_device_ids=None,
    camera_part_numbers=None,
    camera_names=None,
    camera_serial_numbers=None,
    chunk_size=100,
    client=None,
    uri=None,
    token_uri=None,
    audience=None,
    client_id=None,
    client_secret=None,
    local_image_directory='./images',
    image_filename_extension='png',
    local_video_directory='./videos',
    video_filename_extension='mp4'
):
    """
    Downloads images that match search parameters and returns their metadata.

    This function simply combines the operations of fetch_image_metadata() and
    download_image_files(). See documentation of those functions for details.

    Args:
        image_timestamps (list of datetime): List of image timestamps to fetch
        camera_assignment_ids (list of str): Honeycomb assignment IDs (default is None)
        environment_id (str): Honeycomb environment ID (default is None)
        environment_name (str): Honeycomb environment name (default is None)
        camera_device_types (list of str): Honeycomb device types (default is None)
        camera_device_ids (list of str): Honeycomb device IDs (default is None)
        camera_part_numbers (list of str): Honeycomb device part numbers (default is None)
        camera_names (list of str): Honeycomb device names (default is None)
        camera_serial_numbers (list of str): Honeycomb device serial numbers (default is None)
        chunk_size (int): Maximum number of data points to be returned by each Honeycomb query (default is 100)
        client (MinimalHoneycombClient): Existing Honeycomb client (otherwise will create one)
        uri (str): Server URI for creating Honeycomb client (default is value of HONEYCOMB_URI environment variable)
        token_uri (str): Token URI for creating Honeycomb client (default is value of HONEYCOMB_TOKEN_URI environment variable)
        audience (str): Audience for creating Honeycomb client (default is value of HONEYCOMB_AUDIENCE environment variable)
        client_id: Client ID for creating Honeycomb client (default is value of HONEYCOMB_CLIENT_ID environment variable)
        client_secret: Client secret for creating Honeycomb client (default is value of HONEYCOMB_CLIENT_SECRET environment variable)
        local_image_directory (str): Base of local image file tree (default is './images')
        image_filename_extension (str): Filename extension for image files (default is 'png')
        local_video_directory (str): Base of local video file tree (default is './videos')
        video_filename_extension (str): Filename extension for video files (default is 'mp4')

    Returns:
        (list of dict): Metadata for images with local path information appended
    """
    logger.info('Fetching metadata for images that match specified parameters')
    image_metadata = await fetch_image_metadata(
        image_timestamps=image_timestamps,
        camera_assignment_ids=camera_assignment_ids,
        environment_id=environment_id,
        environment_name=environment_name,
        camera_device_types=camera_device_types,
        camera_device_ids=camera_device_ids,
        camera_part_numbers=camera_part_numbers,
        camera_names=camera_names,
        camera_serial_numbers=camera_serial_numbers,
        chunk_size=chunk_size,
        client=client,
        uri=uri,
        token_uri=token_uri,
        audience=audience,
        client_id=client_id,
        client_secret=client_secret
    )
    logger.info('Downloading image files')
    image_metadata_with_local_paths = download_image_files(
        image_metadata=image_metadata,
        local_image_directory=local_image_directory,
        image_filename_extension=image_filename_extension,
        local_video_directory=local_video_directory,
        video_filename_extension=video_filename_extension
    )
    return image_metadata_with_local_paths

async def fetch_video_metadata(
    start=None,
    end=None,
    video_timestamps=None,
    camera_assignment_ids=None,
    environment_id=None,
    environment_name=None,
    camera_device_types=None,
    camera_device_ids=None,
    camera_part_numbers=None,
    camera_names=None,
    camera_serial_numbers=None,
    chunk_size=100,
    client=None,
    uri=video_io.config.HONEYCOMB_URI,
    token_uri=video_io.config.HONEYCOMB_TOKEN_URI,
    audience=video_io.config.HONEYCOMB_AUDIENCE,
    client_id=video_io.config.HONEYCOMB_CLIENT_ID,
    client_secret=video_io.config.HONEYCOMB_CLIENT_SECRET,
):
    """
    Searches Honeycomb for videos that match specified search parameters and
    returns their metadata.

    Videos must match all specified search parameters (i.e., the function
    performs a logical AND of all of the queries). If camera information is not
    specified, returns results for all devices that have one of the specified
    camera device types ('PI3WITHCAMERA' and 'PIZEROWITHCAMERA' by default).
    Redundant combinations of search terms will generate an error (e.g., user
    cannot specify environment name and environment ID, camera assignment IDs
    and camera device IDs, etc.)

    If start and end are specified, returns all videos that overlap with
    specified start and end (e.g., if start is 10:32:56 and end is 10:33:20,
    returns videos starting at 10:32:50, 10:33:00 and 10:33:10).

    Returned metadata is a list of dictionaries, one for each video. Each
    dictionary has the following fields: data_id, video_timestamp,
    environment_id, assignment_id, device_id, bucket, key.

    Args:
        start (datetime): Start of time period to fetch (default is None)
        end (datetime): End of time period to fetch (default is None)
        video_timestamps (list of datetime): List of video start times to fetch (default is None)
        camera_assignment_ids (list of str): Honeycomb assignment IDs (default is None)
        environment_id (str): Honeycomb environment ID (default is None)
        environment_name (str): Honeycomb environment name (default is None)
        camera_device_types (list of str): Honeycomb device types (default is None)
        camera_device_ids (list of str): Honeycomb device IDs (default is None)
        camera_part_numbers (list of str): Honeycomb device part numbers (default is None)
        camera_names (list of str): Honeycomb device names (default is None)
        camera_serial_numbers (list of str): Honeycomb device serial numbers (default is None)
        chunk_size (int): Maximum number of data points to be returned by each Honeycomb query (default is 100)
        client (MinimalHoneycombClient): Existing Honeycomb client (otherwise will create one)
        uri (str): Server URI for creating Honeycomb client (default is value of HONEYCOMB_URI environment variable)
        token_uri (str): Token URI for creating Honeycomb client (default is value of HONEYCOMB_TOKEN_URI environment variable)
        audience (str): Audience for creating Honeycomb client (default is value of HONEYCOMB_AUDIENCE environment variable)
        client_id: Client ID for creating Honeycomb client (default is value of HONEYCOMB_CLIENT_ID environment variable)
        client_secret: Client secret for creating Honeycomb client (default is value of HONEYCOMB_CLIENT_SECRET environment variable)

    Returns:
        (list of dict): Metadata for videos that match search parameters
    """
    if video_timestamps is not None:
        raise NotImplementedError('Fetching specific timestamps no longer supported')
    if start is None or end is None:
        raise NotImplementedError('Now that fetching specific timestamps is no longer supported, you must specify a start and end time')
    if camera_assignment_ids is not None:
        raise NotImplementedError('Specification of cameras by assignment ID no longer supported')
    if camera_part_numbers is not None:
        raise NotImplementedError('Specification of cameras by part numbers no longer supported')
    if environment_id is None and environment_name is None:
        raise NotImplementedError('Now that specification of cameras by assignment ID is no longer supported, you must specify an environment ID or environment name')
    if environment_id is not None and environment_name is not None:
        raise ValueError('Cannot specify both an environment ID and an environment_name')
    if (
        camera_device_ids is not None and
        (
            camera_device_types is not None or
            camera_names is not None or
            camera_serial_numbers is not None
        )
    ):
        raise ValueError('Cannot specify both camera device IDs and camera device types/part numbers/names/serial numbers')
    if (
        camera_device_types is not None and
        (
            camera_names is not None or
            camera_serial_numbers is not None
        )
    ):
        raise ValueError('Cannot specify both camera device types and part numbers/names/serial numbers')
    start_utc = start.astimezone(datetime.timezone.utc)
    end_utc = end.astimezone(datetime.timezone.utc)
    start_utc_honeycomb = honeycomb_io.to_honeycomb_datetime(start_utc)
    end_utc_honeycomb = honeycomb_io.to_honeycomb_datetime(end_utc)
    video_timestamp_min_utc = video_timestamp_min(start_utc)
    video_timestamp_max_utc = video_timestamp_max(end_utc)
    if environment_name is not None:
        environment_id = honeycomb_io.fetch_environment_id(
            environment_name=environment_name,
            client=client,
            uri=uri,
            token_uri=token_uri,
            audience=audience,
            client_id=client_id,
            client_secret=client_secret
        )
    if camera_device_types is not None:
        camera_device_ids = honeycomb_io.fetch_camera_ids_from_environment(
            start=start_utc,
            end=end_utc,
            environment_id=environment_id,
            camera_device_types=camera_device_types,
            client=client,
            uri=uri,
            token_uri=token_uri,
            audience=audience,
            client_id=client_id,
            client_secret=client_secret
        )
    if (
        camera_names is not None or
        camera_serial_numbers is not None
    ):
        camera_device_ids = honeycomb_io.fetch_camera_ids_from_camera_properties(
            camera_names=camera_names,
            camera_serial_numbers=camera_serial_numbers,
            client=client,
            uri=uri,
            token_uri=token_uri,
            audience=audience,
            client_id=client_id,
            client_secret=client_secret
        )
    video_client = client_from_honeycomb_settings(
        client=None,
        token_uri=token_uri,
        audience=audience,
        client_id=client_id,
        client_secret=client_secret
    )
    result = list()
    if camera_device_ids is None:
        logger.info('Fetching video metadata for all cameras in specified environment')
        video_metadata_pages = video_client.get_videos_metadata_paginated(
            environment_id=environment_id,
            start_date=video_timestamp_min_utc,
            end_date=video_timestamp_max_utc
        )
        async for video_metadata_page in video_metadata_pages:
            result.append(video_metadata_page)
    else:
        logger.info('Fetching video metadata for specific cameras')
        for camera_id in camera_device_ids:
            logger.info('Fetching video metadata for camera device ID {}'.format(camera_id))
            video_metadata_pages = video_client.get_videos_metadata_paginated(
                environment_id=environment_id,
                start_date=video_timestamp_min_utc,
                end_date=video_timestamp_max_utc,
                camera_id=camera_id
            )
            async for video_metadata_page in video_metadata_pages:
                result.append(video_metadata_page)
    video_metadata = list()
    logger.info('Parsing {} returned video metadata'.format(len(result)))
    for datum in result:
        meta = datum.get('meta')
        video_metadata.append({
            'data_id': datum.get('id'),
            'video_timestamp': datetime.datetime.fromisoformat(datum.get('timestamp')),
            'environment_id': meta.get('environment_id'),
            'assignment_id': meta.get('assignment_id'),
            'device_id': meta.get('camera_id'),
            'path': meta.get('path')
        })
    return video_metadata


async def download_video_files(
    video_metadata,
    local_video_directory='./videos',
    video_filename_extension=None,
    max_workers=video_io.config.MAX_DOWNLOAD_WORKERS,
    token_uri=video_io.config.HONEYCOMB_TOKEN_URI,
    audience=video_io.config.HONEYCOMB_AUDIENCE,
    client_id=video_io.config.HONEYCOMB_CLIENT_ID,
    client_secret=video_io.config.HONEYCOMB_CLIENT_SECRET
):
    """
    Downloads videos from S3 to local directory tree and returns metadata with
    local path information added.

    Videos are specified as a list of dictionaries, as returned by the function
    fetch_video_metadata(). Each dictionary is assumed to have the following
    fields: data_id, video_timestamp, environment_id, assignment_id, device_id,
    bucket, and key (though only a subset of these are currently used).

    Structure of resulting tree is [base directory]/[environment ID]/[camera
    assignment ID]/[year]/[month]/[day]. Filenames are in the form
    [hour]-[minute]-[second].[filename extension]. Videos are only downloaded if
    they don't already exist in the local directory tree. Directories are
    created as necessary.

    Function returns the metadata with local path information appended to each
    record (in the field video_local_path).

    Args:
        video_metadata (list of dict): Metadata in the format output by fetch_video_metadata()
        local_video_directory (str): Base of local video file tree (default is './videos')
        video_filename_extension (str): Filename extension for video files (default is 'mp4')

    Returns:
        (list of dict): Metadata for videos with local path information appended
    """
    if video_filename_extension is not None:
        raise NotImplementedError('Specifying video filename extension is no longer supported')
    video_client = client_from_honeycomb_settings(
        client=None,
        token_uri=token_uri,
        audience=audience,
        client_id=client_id,
        client_secret=client_secret
    )
    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as e:
        for video_metadatum in video_metadata:
            f = e.submit(asyncio.run, video_client.get_video(path=video_metadatum['path'], destination=local_video_directory))
            video_metadatum['video_local_path'] = os.path.join(local_video_directory, video_metadatum['path'])
            futures.append(f)
    _ = [r for r in concurrent.futures.as_completed(futures)]
    return video_metadata

async def fetch_image_metadata(
    image_timestamps,
    camera_assignment_ids=None,
    environment_id=None,
    environment_name=None,
    camera_device_types=None,
    camera_device_ids=None,
    camera_part_numbers=None,
    camera_names=None,
    camera_serial_numbers=None,
    chunk_size=100,
    client=None,
    uri=None,
    token_uri=None,
    audience=None,
    client_id=None,
    client_secret=None
):
    """
    Searches Honeycomb for videos containing images that match specified search
    parameters and returns video/image metadata.

    Image timestamps are rounded to the nearest tenth of a second to synchronize
    with video frames. Videos containing these images must match all specified
    search parameters (i.e., the function performs a logical AND of all of the
    queries). If camera information is not specified, returns results for all
    devices that have one of the specified camera device types ('PI3WITHCAMERA'
    and 'PIZEROWITHCAMERA' by default). Redundant combinations of search terms
    will generate an error (e.g., user cannot specify environment name and
    environment ID, camera assignment IDs and camera device IDs, etc.)

    Returned metadata is a list of dictionaries, one for each image. Each
    dictionary contains information both about the image and the video that
    contains the image: data_id, video_timestamp, environment_id, assignment_id,
    device_id, bucket, key, and image_timestamp, and frame_number.

    Args:
        image_timestamps (list of datetime): List of image timestamps to fetch
        camera_assignment_ids (list of str): Honeycomb assignment IDs (default is None)
        environment_id (str): Honeycomb environment ID (default is None)
        environment_name (str): Honeycomb environment name (default is None)
        camera_device_types (list of str): Honeycomb device types (default is None)
        camera_device_ids (list of str): Honeycomb device IDs (default is None)
        camera_part_numbers (list of str): Honeycomb device part numbers (default is None)
        camera_names (list of str): Honeycomb device names (default is None)
        camera_serial_numbers (list of str): Honeycomb device serial numbers (default is None)
        chunk_size (int): Maximum number of data points to be returned by each Honeycomb query (default is 100)
        client (MinimalHoneycombClient): Existing Honeycomb client (otherwise will create one)
        uri (str): Server URI for creating Honeycomb client (default is value of HONEYCOMB_URI environment variable)
        token_uri (str): Token URI for creating Honeycomb client (default is value of HONEYCOMB_TOKEN_URI environment variable)
        audience (str): Audience for creating Honeycomb client (default is value of HONEYCOMB_AUDIENCE environment variable)
        client_id: Client ID for creating Honeycomb client (default is value of HONEYCOMB_CLIENT_ID environment variable)
        client_secret: Client secret for creating Honeycomb client (default is value of HONEYCOMB_CLIENT_SECRET environment variable)

    Returns:
        (list of dict): Metadata for images that match search parameters
    """
    image_metadata_by_video_timestamp = dict()
    for image_timestamp in image_timestamps:
        image_timestamp = image_timestamp.astimezone(datetime.timezone.utc)
        timestamp_floor = image_timestamp.replace(second=0, microsecond=0)
        video_timestamp = timestamp_floor + math.floor((image_timestamp - timestamp_floor)/datetime.timedelta(seconds=10))*datetime.timedelta(seconds=10)
        frame_number = round((image_timestamp - video_timestamp)/datetime.timedelta(milliseconds=100))
        if video_timestamp not in image_metadata_by_video_timestamp.keys():
            image_metadata_by_video_timestamp[video_timestamp] = list()
        image_metadata_by_video_timestamp[video_timestamp].append({
            'image_timestamp': image_timestamp,
            'frame_number': frame_number
        })
    video_timestamps = list(image_metadata_by_video_timestamp.keys())
    video_metadata = await fetch_video_metadata(
        video_timestamps=video_timestamps,
        camera_assignment_ids=camera_assignment_ids,
        environment_id=environment_id,
        environment_name=environment_name,
        camera_device_types=camera_device_types,
        camera_device_ids=camera_device_ids,
        camera_part_numbers=camera_part_numbers,
        camera_names=camera_names,
        camera_serial_numbers=camera_serial_numbers,
        chunk_size=chunk_size,
        client=client,
        uri=uri,
        token_uri=token_uri,
        audience=audience,
        client_id=client_id,
        client_secret=client_secret
    )
    image_metadata = list()
    for video in video_metadata:
        for image in image_metadata_by_video_timestamp[video['video_timestamp']]:
            image_metadata.append({**video, **image})
    return image_metadata

def download_image_files(
    image_metadata,
    local_image_directory='./images',
    image_filename_extension='png',
    local_video_directory='./videos',
    video_filename_extension='mp4'
):
    """
    Downloads videos from S3 to local directory tree, extract images, saves
    images to local directory tree, and returns metadata with local path
    information added.

    Images are specified as a list of dictionaries, as returned by the function
    fetch_image_metadata(). Each dictionary is expected to contain information
    both about the image and the video that contains the image and is assumed to
    have the following fields: data_id, video_timestamp, environment_id,
    assignment_id, device_id, bucket, key, and image_timestamp, and frame_number
    (though only a subset of these are currently used).

    Structure of resulting video file tree is as described in documentation for
    download_video_files(). Structure of resulting image file tree is [base
    directory]/[environment ID]/[camera assignment ID]/[year]/[month]/[day].
    Filenames contain the timestamp for the start of the containing video and
    the frame number of the image in the form [hour]-[minute]-[second]_[frame
    number].[filename extension]. Videos and images are only downloaded if they
    don't already exist in the local directory trees. Directories are created as
    necessary.

    Function returns the metadata with local path information appended to each
    record (in the fields video_local_path and image_local_path).

    Args:
        image_metadata (list of dict): Metadata in the format output by fetch_image_metadata()
        local_image_directory (str): Base of local image file tree (default is './images')
        image_filename_extension (str): Filename extension for image files (default is 'png')
        local_video_directory (str): Base of local video file tree (default is './videos')
        video_filename_extension (str): Filename extension for video files (default is 'mp4')

    Returns:
        (list of dict): Metadata for images with local path information appended
    """
    image_metadata_with_local_video_paths = download_video_files(
        image_metadata,
        local_video_directory=local_video_directory,
        video_filename_extension=video_filename_extension
    )
    image_metadata_with_local_paths = list()
    for image in image_metadata_with_local_video_paths:
        download_path = image_local_path(
            local_image_directory=local_image_directory,
            environment_id=image.get('environment_id'),
            assignment_id=image.get('assignment_id'),
            video_timestamp=image.get('video_timestamp'),
            frame_number=image.get('frame_number'),
            image_filename_extension=image_filename_extension
        )
        if not os.path.exists(download_path):
            video_input = cv_utils.VideoInput(image.get('video_local_path'))
            image_data = video_input.get_frame_by_frame_number(image.get('frame_number'))
            os.makedirs(os.path.dirname(download_path), exist_ok=True)
            cv.imwrite(download_path, image_data)
        else:
            logger.info('File {} already exists'.format(download_path))
        image['image_local_path'] = download_path
        image_metadata_with_local_paths.append(image)
    return image_metadata_with_local_paths

def image_local_path(
    local_image_directory,
    environment_id,
    assignment_id,
    video_timestamp,
    frame_number,
    image_filename_extension='png'
):
    return os.path.join(
        local_image_directory,
        environment_id,
        assignment_id,
        '{}_{:03}.{}'.format(
            video_timestamp.strftime("%Y/%m/%d/%H-%M-%S"),
            frame_number,
            image_filename_extension
        )
    )

def video_timestamp_min(start):
    original_tzinfo = start.tzinfo
    if original_tzinfo:
        start_naive = start.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    else:
        start_naive = start
    timestamp_min_naive = (
        datetime.datetime.min +
        math.floor((start_naive - datetime.datetime.min)/VIDEO_DURATION)*VIDEO_DURATION
    )
    if original_tzinfo:
        timestamp_min = timestamp_min_naive.replace(tzinfo=datetime.timezone.utc).astimezone(original_tzinfo)
    else:
        timestamp_min = timestamp_min_naive
    return timestamp_min

def video_timestamp_max(end):
    original_tzinfo = end.tzinfo
    if original_tzinfo:
        end_naive = end.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    else:
        end_naive = end
    timestamp_max_naive = (
        datetime.datetime.min +
        math.ceil((end_naive - datetime.datetime.min)/VIDEO_DURATION)*VIDEO_DURATION
    )
    if original_tzinfo:
        timestamp_max = timestamp_max_naive.replace(tzinfo=datetime.timezone.utc).astimezone(original_tzinfo)
    else:
        timestamp_max = timestamp_max_naive
    return timestamp_max
