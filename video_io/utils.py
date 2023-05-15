import datetime
import errno
import logging
import math
import os
import shutil
import tempfile
from typing import List, Optional

import ffmpeg
import pandas as pd

from video_io.video_reader import VideoReader

logger = logging.getLogger(__name__)


def concat_videos(
    video_metadata: List[dict],
    start: datetime,
    end: datetime,
    output_directory: str,
    overwrite: bool = False,
) -> Optional[List]:
    """
    Use the output of core.download_video_files() to concatenate videos for each camera into a single video file.

    Function will trim video to exactly match the given start and end times.

    Args:
        video_metadata (list of dict): Data in the format output by core.download_video_files()
        start (datetime): Start of time period
        end (datetime): End of time period
        output_directory (str): Directory to write concatenated video files to. Video file names are written as "{environment_id}_{camera_device_id}_{start.strftime('%m%d%YT%H%M%S%f%z')}_{end.strftime('%m%d%YT%H%M%S%f%z')}.mp4"
        overwrite (bool): If set, any previously generated concatenated video will be overwritten

    Returns:
        concatenated_video_output (list of dict): Returns a list of dictionaries with environment, camera assignment, camera device, and concatenated video path data
    """
    video_snippet_length = 10.0
    video_snippet_fps = 10

    concatenated_video_output = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        for (
            environment_id,
            camera_assignment_id,
            camera_device_id,
        ), df_video_files_by_device in (
            pd.DataFrame(video_metadata)
            .sort_values(by=["device_id", "video_timestamp"])
            .groupby(["environment_id", "assignment_id", "device_id"], dropna=False)
        ):
            video_output_path = f"{output_directory}/{environment_id}_{camera_device_id}_{start.strftime('%m%d%YT%H%M%S%f%z')}_{end.strftime('%m%d%YT%H%M%S%f%z')}.mp4"

            if not os.path.exists(video_output_path) or overwrite:
                # tmp_concat_demuxer_file is a temp file containing a list of video files to concatenate. This file
                # gets input into ffmpeg.
                with tempfile.NamedTemporaryFile() as tmp_concat_demuxer_file:
                    for idx, video_file_row in df_video_files_by_device.iterrows():
                        video_path = video_file_row["video_local_path"]
                        final_video_snippet_path = video_path

                        # TODO: There's an assumption in the following logic that video snippets will be always be 10.0 seconds long, but that may not be true. We should trim/pad videos appropriately before executing the next piece of code

                        video_start_time = video_file_row["video_timestamp"]
                        video_end_time = video_file_row[
                            "video_timestamp"
                        ] + datetime.timedelta(seconds=video_snippet_length)

                        start_trim = 0.0
                        end_trim = video_snippet_length

                        if start > video_start_time:
                            start_trim = (
                                start - video_file_row["video_timestamp"]
                            ).total_seconds()

                        if end < video_end_time:
                            end_trim = (
                                video_snippet_length
                                - (video_end_time - end).total_seconds()
                            )

                        duration = end_trim - start_trim
                        if duration != video_snippet_length:
                            final_video_snippet_path = f"{tmp_dir}/{environment_id}_{camera_device_id}_{idx}_trimmed_video.mp4"
                            trim_video(
                                input_path=video_path,
                                output_path=final_video_snippet_path,
                                start_trim=start_trim,
                                end_trim=end_trim,
                                fps=video_snippet_fps,
                            )

                        tmp_concat_demuxer_file.write(
                            str.encode(f"file 'file:{final_video_snippet_path}'\n")
                        )
                        tmp_concat_demuxer_file.flush()

                    ffmpeg.input(
                        f"file:{tmp_concat_demuxer_file.name}",
                        format="concat",
                        safe=0,
                        r=video_snippet_fps,
                    ).output(
                        f"file:{video_output_path}",
                        c="copy",
                        r=video_snippet_fps,
                        vsync=0,
                    ).overwrite_output().run()

            concatenated_video_output.append(
                {
                    "environment_id": environment_id,
                    "camera_assignment_id": camera_assignment_id,
                    "camera_device_id": camera_device_id,
                    "file_path": video_output_path,
                }
            )

    return concatenated_video_output


def trim_video(
    input_path: str,
    output_path: str,
    start_trim: float = 0.0,
    end_trim: Optional[float] = None,
    fps: int = 10,
) -> bool:
    """
    Trims video from a given start offset (in seconds) to a given end offset (in seconds).

    Trimmed video will be output to the provided output_path. Or, you can overwrite a video file
    by using the same input and output path.

    Function also accepts a FPS value. The trimmed output video will be written with this FPS.

    Returns a boolean success value

    Args:
        input_path (str): Path to the local video file
        output_path (str): Path to where the trimmed output file should be written
        start_trim (float): Trim from a given time, in seconds (default is 0.0)
        end_trim (float): Trim to a given time, in seconds. This is NOT duration. (default is video's length in seconds)
        fps (int): Desired frames per second of output file (default is 10)

    Returns:
        (boolean): True if video could be trimmed and output to the given output_path
    """
    logging.info(
        "Trimming video '{}' from {} seconds to {} seconds".format(
            input_path, start_trim, end_trim
        )
    )

    if not os.path.exists(input_path):
        err = f"'{input_path}' does not exist, unable to trim video. Raising FileNotFoundError exception."
        logger.error(err)
        raise (FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), err))

    if end_trim is None:
        video_reader = VideoReader(input_path)
        end_trim = video_reader.duration()

    tmp_file = None
    should_overwrite_input = input_path == output_path
    ffmpeg_output_path = output_path
    try:
        if should_overwrite_input:
            tmp_file = tempfile.NamedTemporaryFile(suffix=".mp4")
            ffmpeg_output_path = tmp_file.name

        duration_seconds = end_trim - start_trim
        ffmpeg.input(input_path, ss=start_trim, to=end_trim).output(
            ffmpeg_output_path, r=fps, vframes=int(duration_seconds * fps)
        ).overwrite_output().run()

        if should_overwrite_input:
            shutil.copy(ffmpeg_output_path, input_path)
    except ffmpeg._run.Error as e:
        logging.error("Failed trimming video {}".format(input_path))
        logging.error(e)

        # Cleanup
        if tmp_file is None and os.path.exists(ffmpeg_output_path):
            try:
                os.remove(ffmpeg_output_path)
            except:
                logger.error(
                    f"Unable to cleanup {ffmpeg_output_path} after exception trimming video"
                )

        return False

    return True


def generate_video_mosaic(
    video_inputs: List[str],
    output_directory: Optional[str] = None,
    output_path: Optional[str] = None,
):
    width = None
    height = None

    if output_directory is None and output_path is None:
        raise ValueError("output_directory and output_path cannot both be None")

    if len(video_inputs) <= 1:
        raise ValueError("Number of video inputs must be two or greater")

    _output_directory = output_directory
    _output_path = output_path
    if output_path is not None:
        _output_directory = os.path.dirname(output_path)
    else:
        _output_path = f"{_output_directory}/{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.mp4"

    os.makedirs(_output_directory, exist_ok=True)
    ffmpeg_inputs = []
    for f in video_inputs:
        if not os.path.exists(f):
            err = f"'{f}' does not exist, unable to trim video. Raising FileNotFoundError exception."
            logger.error(err)
            raise (FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), err))
        ffmpeg_inputs.append(ffmpeg.input(f))

        if width is None or height is None:
            v = VideoReader(f)
            width = int(v.width())
            height = int(v.height())

    def get_grid(n):
        if n <= 0:
            return []

        row_width = math.ceil(math.sqrt(n))
        shape = []
        for ii in range(row_width, n + 1, row_width):
            shape.append(row_width)

        if n > sum(shape):
            shape.append(n - sum(shape))

        return shape

    grid = get_grid(len(video_inputs))

    layout = []
    ideal_shape = max(grid)
    for row, num_cols in enumerate(grid):
        for col in range(num_cols):
            offset = int((ideal_shape - num_cols) * width * 0.5)
            layout.append(f"{offset + (col * width)}_{row * height}")

    vout = ffmpeg.filter(
        list(map(lambda v: v.video, ffmpeg_inputs)),
        "xstack",
        inputs=len(ffmpeg_inputs),
        layout="|".join(layout),
        # fill="black[out]"
    )

    ffmpeg.output(
        vout, _output_path, pix_fmt="yuv420p", vcodec="libx264"
    ).overwrite_output().run()

    return _output_path
