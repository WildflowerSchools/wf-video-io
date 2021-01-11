import minimal_honeycomb
import cv_utils
import cv2 as cv
import boto3
import os
import math
import datetime
import logging

logger = logging.getLogger(__name__)

DEFAULT_CAMERA_DEVICE_TYPES = [
    'PI3WITHCAMERA',
    'PI4WITHCAMERA',
    'PIZEROWITHCAMERA'
]

def fetch_videos(
    start=None,
    end=None,
    video_timestamps=None,
    camera_assignment_ids=None,
    environment_id=None,
    environment_name=None,
    camera_device_types=DEFAULT_CAMERA_DEVICE_TYPES,
    camera_device_ids=None,
    camera_part_numbers=None,
    camera_names=None,
    camera_serial_numbers=None,
    chunk_size=100,
    minimal_honeycomb_client=None,
    uri=None,
    token_uri=None,
    audience=None,
    client_id=None,
    client_secret=None,
    local_video_directory='./videos',
    video_filename_extension='mp4'
):
    """
    Downloads videos that match search parameters and returns their metadata.

    This function simply combines the operations of fetch_video_metadata() and
    download_video_files(). See documentation of those functions for details.

    Args:
        start (datetime): Earliest video start time (default is None)
        end (datetime): Latest video start time (default is None)
        video_timestamps (list of datetime): List of video start times (default is None)
        camera_assignment_ids (list of str): Honeycomb assignment IDs (default is None)
        environment_id (str): Honeycomb environment ID (default is None)
        environment_name (str): Honeycomb environment name (default is None)
        camera_device_types (list of str): Honeycomb device types (default is ['PI3WITHCAMERA', 'PIZEROWITHCAMERA'])
        camera_device_ids (list of str): Honeycomb device IDs (default is None)
        camera_part_numbers (list of str): Honeycomb device part numbers (default is None)
        camera_names (list of str): Honeycomb device names (default is None)
        camera_serial_numbers (list of str): Honeycomb device serial numbers (default is None)
        chunk_size (int): Maximum number of data points to be returned by each Honeycomb query (default is 100)
        minimal_honeycomb_client (MinimalHoneycombClient): Existing Honeycomb client (otherwise will create one)
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
    video_metadata = fetch_video_metadata(
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
        minimal_honeycomb_client=minimal_honeycomb_client,
        uri=uri,
        token_uri=token_uri,
        audience=audience,
        client_id=client_id,
        client_secret=client_secret
    )
    logger.info('Downloading video files')
    video_metadata_with_local_paths = download_video_files(
        video_metadata=video_metadata,
        local_video_directory=local_video_directory,
        video_filename_extension=video_filename_extension
    )
    return video_metadata_with_local_paths

def fetch_images(
    image_timestamps,
    camera_assignment_ids=None,
    environment_id=None,
    environment_name=None,
    camera_device_types=DEFAULT_CAMERA_DEVICE_TYPES,
    camera_device_ids=None,
    camera_part_numbers=None,
    camera_names=None,
    camera_serial_numbers=None,
    chunk_size=100,
    minimal_honeycomb_client=None,
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
        image_timestamps (list of datetime): List of image timestamps
        camera_assignment_ids (list of str): Honeycomb assignment IDs (default is None)
        environment_id (str): Honeycomb environment ID (default is None)
        environment_name (str): Honeycomb environment name (default is None)
        camera_device_types (list of str): Honeycomb device types (default is ['PI3WITHCAMERA', 'PIZEROWITHCAMERA'])
        camera_device_ids (list of str): Honeycomb device IDs (default is None)
        camera_part_numbers (list of str): Honeycomb device part numbers (default is None)
        camera_names (list of str): Honeycomb device names (default is None)
        camera_serial_numbers (list of str): Honeycomb device serial numbers (default is None)
        chunk_size (int): Maximum number of data points to be returned by each Honeycomb query (default is 100)
        minimal_honeycomb_client (MinimalHoneycombClient): Existing Honeycomb client (otherwise will create one)
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
    image_metadata = fetch_image_metadata(
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
        minimal_honeycomb_client=minimal_honeycomb_client,
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

def fetch_video_metadata(
    start=None,
    end=None,
    video_timestamps=None,
    camera_assignment_ids=None,
    environment_id=None,
    environment_name=None,
    camera_device_types=DEFAULT_CAMERA_DEVICE_TYPES,
    camera_device_ids=None,
    camera_part_numbers=None,
    camera_names=None,
    camera_serial_numbers=None,
    chunk_size=100,
    minimal_honeycomb_client=None,
    uri=None,
    token_uri=None,
    audience=None,
    client_id=None,
    client_secret=None
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

    Returned metadata is a list of dictionaries, one for each video. Each
    dictionary has the following fields: data_id, video_timestamp,
    environment_id, assignment_id, device_id, bucket, key.

    Args:
        start (datetime): Earliest video start time (default is None)
        end (datetime): Latest video start time (default is None)
        video_timestamps (list of datetime): List of video start times (default is None)
        camera_assignment_ids (list of str): Honeycomb assignment IDs (default is None)
        environment_id (str): Honeycomb environment ID (default is None)
        environment_name (str): Honeycomb environment name (default is None)
        camera_device_types (list of str): Honeycomb device types (default is ['PI3WITHCAMERA', 'PIZEROWITHCAMERA'])
        camera_device_ids (list of str): Honeycomb device IDs (default is None)
        camera_part_numbers (list of str): Honeycomb device part numbers (default is None)
        camera_names (list of str): Honeycomb device names (default is None)
        camera_serial_numbers (list of str): Honeycomb device serial numbers (default is None)
        chunk_size (int): Maximum number of data points to be returned by each Honeycomb query (default is 100)
        minimal_honeycomb_client (MinimalHoneycombClient): Existing Honeycomb client (otherwise will create one)
        uri (str): Server URI for creating Honeycomb client (default is value of HONEYCOMB_URI environment variable)
        token_uri (str): Token URI for creating Honeycomb client (default is value of HONEYCOMB_TOKEN_URI environment variable)
        audience (str): Audience for creating Honeycomb client (default is value of HONEYCOMB_AUDIENCE environment variable)
        client_id: Client ID for creating Honeycomb client (default is value of HONEYCOMB_CLIENT_ID environment variable)
        client_secret: Client secret for creating Honeycomb client (default is value of HONEYCOMB_CLIENT_SECRET environment variable)

    Returns:
        (list of dict): Metadata for videos that match search parameters
    """
    if (start is not None or end is not None) and video_timestamps is not None:
        raise ValueError('Cannot specify start/end and list of video timestamps')
    if (
        camera_assignment_ids is not None and
        (
            environment_id is not None or
            environment_name is not None
        )
    ):
        raise ValueError('Cannot specify camera assignment IDs and environment')
    if (
        camera_assignment_ids is not None and
        (
            camera_device_ids is not None or
            camera_part_numbers is not None or
            camera_names is not None or
            camera_serial_numbers is not None
        )
    ):
        raise ValueError('Cannot specify camera assignment IDs and camera device properties')
    if environment_id is not None and environment_name is not None:
        raise ValueError('Cannot specify environment ID and environment name')
    if video_timestamps is not None:
        start = min(video_timestamps)
        end = max(video_timestamps)
        video_timestamps_honeycomb = [minimal_honeycomb.to_honeycomb_datetime(video_timestamp) for video_timestamp in video_timestamps]
    if start is not None:
        start_honeycomb = minimal_honeycomb.to_honeycomb_datetime(start)
    if end is not None:
        end_honeycomb = minimal_honeycomb.to_honeycomb_datetime(end)
    if environment_name is not None:
        environment_id = fetch_environment_id(
            environment_name=environment_name,
            chunk_size=chunk_size,
            minimal_honeycomb_client=minimal_honeycomb_client,
            uri=uri,
            token_uri=token_uri,
            audience=audience,
            client_id=client_id,
            client_secret=client_secret
        )
    camera_assignment_ids_from_environment = fetch_camera_assignment_ids_from_environment(
        start=start,
        end=end,
        environment_id=environment_id,
        camera_device_types=camera_device_types,
        chunk_size=chunk_size,
        minimal_honeycomb_client=minimal_honeycomb_client,
        uri=uri,
        token_uri=token_uri,
        audience=audience,
        client_id=client_id,
        client_secret=client_secret
    )
    camera_assignment_ids_from_camera_properties = fetch_camera_assignment_ids_from_camera_properties(
        start=start,
        end=end,
        camera_device_ids=camera_device_ids,
        camera_part_numbers=camera_part_numbers,
        camera_names=camera_names,
        camera_serial_numbers=camera_serial_numbers,
        chunk_size=100,
        minimal_honeycomb_client=None,
        uri=uri,
        token_uri=token_uri,
        audience=audience,
        client_id=client_id,
        client_secret=client_secret
    )
    logger.info('Building query list for video metadata search')
    query_list = list()
    if start is not None:
        query_list.append({
            'field': 'timestamp',
            'operator': 'GTE',
            'value': start_honeycomb
        })
    if end is not None:
        query_list.append({
            'field': 'timestamp',
            'operator': 'LTE',
            'value': end_honeycomb
        })
    if video_timestamps is not None:
        query_list.append({
            'field': 'timestamp',
            'operator': 'IN',
            'values': video_timestamps_honeycomb
        })
    if camera_assignment_ids is not None:
        query_list.append({
            'field': 'source',
            'operator': 'IN',
            'values': camera_assignment_ids
        })
    if camera_assignment_ids_from_environment is not None:
        query_list.append({
            'field': 'source',
            'operator': 'IN',
            'values': camera_assignment_ids_from_environment
        })
    if camera_assignment_ids_from_camera_properties is not None:
        query_list.append({
            'field': 'source',
            'operator': 'IN',
            'values': camera_assignment_ids_from_camera_properties
        })
    return_data= [
        'data_id',
        'timestamp',
        {'source': [
            {'... on Assignment': [
                {'environment': [
                    'environment_id'
                ]},
                'assignment_id',
                {'assigned': [
                    {'... on Device': [
                        'device_id'
                    ]}
                ]}
            ]}
        ]},
        {'file': [
            'bucketName',
            'key'
        ]}
    ]
    result = search_datapoints(
        query_list=query_list,
        return_data=return_data,
        chunk_size=chunk_size,
        minimal_honeycomb_client=None,
        uri=uri,
        token_uri=token_uri,
        audience=audience,
        client_id=client_id,
        client_secret=client_secret
    )
    video_metadata = list()
    logger.info('Parsing {} returned camera datapoints'.format(len(result)))
    for datum in result:
        source = datum.get('source') if datum.get('source') is not None else {}
        file = datum.get('file') if datum.get('file') is not None else {}
        video_metadata.append({
            'data_id': datum.get('data_id'),
            'video_timestamp': minimal_honeycomb.from_honeycomb_datetime(datum.get('timestamp')),
            'environment_id': (source.get('environment') if source.get('environment') is not None else {}).get('environment_id'),
            'assignment_id': source.get('assignment_id'),
            'device_id': (source.get('assigned') if source.get('assigned') is not None else {}).get('device_id'),
            'bucket': file.get('bucketName'),
            'key': file.get('key')
        })
    return video_metadata

def download_video_files(
    video_metadata,
    local_video_directory='./videos',
    video_filename_extension='mp4'
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
    video_metadata_with_local_paths = list()
    for video in video_metadata:
        download_path = video_local_path(
            local_video_directory=local_video_directory,
            environment_id=video.get('environment_id'),
            assignment_id=video.get('assignment_id'),
            video_timestamp=video.get('video_timestamp'),
            video_filename_extension=video_filename_extension
        )
        if not os.path.exists(download_path):
            load_file_from_s3(video.get('key'), video.get('bucket'), download_path)
        else:
            logger.info('File {} already exists'.format(download_path))
        video['video_local_path'] = download_path
        video_metadata_with_local_paths.append(video)
    return video_metadata_with_local_paths

def video_local_path(
    local_video_directory,
    environment_id,
    assignment_id,
    video_timestamp,
    video_filename_extension='mp4'
):
    return os.path.join(
        local_video_directory,
        environment_id,
        assignment_id,
        '{}.{}'.format(
            video_timestamp.strftime("%Y/%m/%d/%H-%M-%S"),
            video_filename_extension
        )
    )

def load_file_from_s3(
    key,
    bucket_name,
    download_path
):
    s3 = boto3.resource('s3')
    logger.info('Loading {} from {} into {}'.format(
        key,
        bucket_name,
        download_path
    ))
    download_directory = os.path.dirname(download_path)
    os.makedirs(download_directory, exist_ok=True)
    s3.meta.client.download_file(bucket_name, key, download_path)

def fetch_image_metadata(
    image_timestamps,
    camera_assignment_ids=None,
    environment_id=None,
    environment_name=None,
    camera_device_types=DEFAULT_CAMERA_DEVICE_TYPES,
    camera_device_ids=None,
    camera_part_numbers=None,
    camera_names=None,
    camera_serial_numbers=None,
    chunk_size=100,
    minimal_honeycomb_client=None,
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
        image_timestamps (list of datetime): List of image timestamps
        camera_assignment_ids (list of str): Honeycomb assignment IDs (default is None)
        environment_id (str): Honeycomb environment ID (default is None)
        environment_name (str): Honeycomb environment name (default is None)
        camera_device_types (list of str): Honeycomb device types (default is ['PI3WITHCAMERA', 'PIZEROWITHCAMERA'])
        camera_device_ids (list of str): Honeycomb device IDs (default is None)
        camera_part_numbers (list of str): Honeycomb device part numbers (default is None)
        camera_names (list of str): Honeycomb device names (default is None)
        camera_serial_numbers (list of str): Honeycomb device serial numbers (default is None)
        chunk_size (int): Maximum number of data points to be returned by each Honeycomb query (default is 100)
        minimal_honeycomb_client (MinimalHoneycombClient): Existing Honeycomb client (otherwise will create one)
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
    video_metadata = fetch_video_metadata(
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
        minimal_honeycomb_client=minimal_honeycomb_client,
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

def fetch_environment_id(
    environment_name=None,
    chunk_size=None,
    minimal_honeycomb_client=None,
    uri=None,
    token_uri=None,
    audience=None,
    client_id=None,
    client_secret=None
):
    if environment_name is None:
        return None
    logger.info('Fetching environment ID for specified environment name')
    if minimal_honeycomb_client is None:
        minimal_honeycomb_client = minimal_honeycomb.MinimalHoneycombClient(
            uri=uri,
            token_uri=token_uri,
            audience=audience,
            client_id=client_id,
            client_secret=client_secret
        )
    result = minimal_honeycomb_client.bulk_query(
        request_name='findEnvironments',
        arguments={
            'name': {
                'type': 'String',
                'value': environment_name
            }
        },
        return_data=[
            'environment_id'
        ],
        id_field_name='environment_id',
        chunk_size=chunk_size
    )
    if len(result) == 0:
        raise ValueError('No environments match environment name {}'.format(
            environment_name
        ))
    if len(result) > 1:
        raise ValueError('Multiple environments match environment name {}'.format(
            environment_name
        ))
    environment_id = result[0].get('environment_id')
    logger.info('Found environment ID for specified environment name')
    return environment_id

def fetch_camera_assignment_ids_from_environment(
    start=None,
    end=None,
    environment_id=None,
    camera_device_types=DEFAULT_CAMERA_DEVICE_TYPES,
    chunk_size=100,
    minimal_honeycomb_client=None,
    uri=None,
    token_uri=None,
    audience=None,
    client_id=None,
    client_secret=None
):
    if environment_id is None:
        return None
    logger.info('Fetching camera assignments for specified environment and time span')
    if minimal_honeycomb_client is None:
        minimal_honeycomb_client = minimal_honeycomb.MinimalHoneycombClient(
            uri=uri,
            token_uri=token_uri,
            audience=audience,
            client_id=client_id,
            client_secret=client_secret
        )
    result = minimal_honeycomb_client.request(
        request_type='query',
        request_name='getEnvironment',
        arguments={
            'environment_id': {
                'type': 'ID!',
                'value': environment_id
            }
        },
        return_object=[
            {'assignments': [
                'assignment_id',
                'start',
                'end',
                {'assigned': [
                    {'... on Device': [
                        'device_type'
                    ]}
                ]}
            ]}
        ]
    )
    filtered_assignments = minimal_honeycomb.filter_assignments(
        assignments=result.get('assignments'),
        start_time=start,
        end_time=end
    )
    camera_assignment_ids = list()
    for assignment in filtered_assignments:
        device_type = assignment.get('assigned').get('device_type')
        if device_type is not None and device_type in camera_device_types:
            camera_assignment_ids.append(assignment.get('assignment_id'))
    if len(camera_assignment_ids) == 0:
        raise ValueError('No camera assignments found in specified environment for specified time span')
    logger.info('Found {} camera assignments for specified environment and time span'.format(len(camera_assignment_ids)))
    return camera_assignment_ids

def fetch_camera_assignment_ids_from_camera_properties(
    start=None,
    end=None,
    camera_device_ids=None,
    camera_part_numbers=None,
    camera_names=None,
    camera_serial_numbers=None,
    chunk_size=100,
    minimal_honeycomb_client=None,
    uri=None,
    token_uri=None,
    audience=None,
    client_id=None,
    client_secret=None
):
    if camera_device_ids is None and camera_names is None and camera_part_numbers is None and camera_serial_numbers is None:
        return None
    query_list=list()
    if camera_device_ids is not None:
        query_list.append({
            'field': 'device_id',
            'operator': 'IN',
            'values': camera_device_ids
        })
    if camera_part_numbers is not None:
        query_list.append({
            'field': 'part_number',
            'operator': 'IN',
            'values': camera_part_numbers
        })
    if camera_names is not None:
        query_list.append({
            'field': 'name',
            'operator': 'IN',
            'values': camera_names
        })
    if camera_serial_numbers is not None:
        query_list.append({
            'field': 'serial_number',
            'operator': 'IN',
            'values': camera_serial_numbers
        })
    logger.info('Fetching camera assignments for cameras with specified properties')
    if minimal_honeycomb_client is None:
        minimal_honeycomb_client = minimal_honeycomb.MinimalHoneycombClient(
            uri=uri,
            token_uri=token_uri,
            audience=audience,
            client_id=client_id,
            client_secret=client_secret
        )
    result = minimal_honeycomb_client.bulk_query(
        request_name='searchDevices',
        arguments={
            'query': {
                'type': 'QueryExpression!',
                'value': {
                    'operator': 'AND',
                    'children': query_list
                }
            }
        },
        return_data=[
            'device_id',
            {'assignments': [
                'assignment_id',
                'start',
                'end'
            ]}
        ],
        id_field_name='device_id',
        chunk_size=chunk_size
    )
    assignments = list()
    for datum in result:
        if datum.get('assignments') is not None and len(datum.get('assignments')) > 0:
            assignments.extend(datum.get('assignments'))
    filtered_assignments = minimal_honeycomb.filter_assignments(
        assignments=assignments,
        start_time=start,
        end_time=end
    )
    if len(filtered_assignments) == 0:
        raise ValueError('No camera assignments match specified camera device IDs/names/part numbers/serial numbers and time span')
    camera_assignment_ids = [assignment.get('assignment_id') for assignment in filtered_assignments]
    return camera_assignment_ids

def search_datapoints(
    query_list,
    return_data,
    chunk_size=100,
    minimal_honeycomb_client=None,
    uri=None,
    token_uri=None,
    audience=None,
    client_id=None,
    client_secret=None
):
    logger.info('Searching for datapoints that match the specified parameters')
    if minimal_honeycomb_client is None:
        minimal_honeycomb_client = minimal_honeycomb.MinimalHoneycombClient(
            uri=uri,
            token_uri=token_uri,
            audience=audience,
            client_id=client_id,
            client_secret=client_secret
        )
    result = minimal_honeycomb_client.bulk_query(
        request_name='searchDatapoints',
        arguments={
            'query': {
                'type': 'QueryExpression!',
                'value': {
                    'operator': 'AND',
                    'children': query_list
                }
            }
        },
        return_data=return_data,
        id_field_name = 'data_id',
        chunk_size=chunk_size
    )
    logger.info('Fetched {} datapoints'.format(len(result)))
    return result
