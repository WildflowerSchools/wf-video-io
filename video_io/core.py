import minimal_honeycomb
import boto3
import os
import math
import datetime
import logging

logger = logging.getLogger(__name__)

DEFAULT_CAMERA_DEVICE_TYPES = [
    'PI3WITHCAMERA',
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
    filename_extension='mp4'
):
    logging.info('Fetching metadata for videos that match specified parameters')
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
    logging.info('Downloading video files')
    video_metadata_with_local_paths = download_video_files(
        video_metadata=video_metadata,
        local_video_directory=local_video_directory,
        filename_extension=filename_extension
    )
    return video_metadata_with_local_paths

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

def download_video_files(
    video_metadata,
    local_video_directory='./videos',
    filename_extension='mp4'
):
    video_metadata_with_local_paths = list()
    for video in video_metadata:
        download_path = local_video_path(
            local_video_directory=local_video_directory,
            environment_id=video.get('environment_id'),
            assignment_id=video.get('assignment_id'),
            video_timestamp=video.get('video_timestamp'),
            filename_extension=filename_extension
        )
        if not os.path.exists(download_path):
            load_file_from_s3(video.get('key'), video.get('bucket'), download_path)
        else:
            logging.info('File {} already exists'.format(download_path))
        video['local_path'] = download_path
        video_metadata_with_local_paths.append(video)
    return video_metadata_with_local_paths

def local_video_path(
    local_video_directory,
    environment_id,
    assignment_id,
    video_timestamp,
    filename_extension='mp4'
):
    return os.path.join(
        local_video_directory,
        environment_id,
        assignment_id,
        '{}.{}'.format(
            video_timestamp.strftime("%Y/%m/%d/%H-%M-%S"),
            filename_extension
        )
    )

def load_file_from_s3(
    key,
    bucket_name,
    download_path
):
    s3 = boto3.resource('s3')
    logging.info('Loading {} from {} into {}'.format(
        key,
        bucket_name,
        download_path
    ))
    download_directory = os.path.dirname(download_path)
    os.makedirs(download_directory, exist_ok=True)
    s3.meta.client.download_file(bucket_name, key, download_path)
