import pathlib
import shutil
import tempfile

import pytest

import video_io.utils
from video_io.video_reader import VideoReader


def test_trim_video():
    with tempfile.NamedTemporaryFile(suffix='.mp4') as fp:
        input_path = f"{pathlib.Path(__file__).parent.resolve()}/videos/cat-10-seconds-fps-10.mp4"
        output_path = fp.name

        video_reader = VideoReader(input_path)
        assert video_reader.fps() == 10
        assert video_reader.frames() == 100
        assert video_reader.duration() == 10.0

        success = video_io.utils.trim_video(
            input_path=input_path,
            output_path=output_path,
            start_trim=1.5,
            end_trim=8.5
        )
        assert success

        video_reader = VideoReader(output_path)
        assert video_reader.fps() == 10
        assert video_reader.frames() == 70
        assert video_reader.duration() == 7.0


def test_trim_video_30_to_10_fps():
    with tempfile.NamedTemporaryFile(suffix='.mp4') as fp:
        input_path = f"{pathlib.Path(__file__).parent.resolve()}/videos/cat-10-seconds-fps-30.mp4"
        output_path = fp.name

        video_reader = VideoReader(input_path)
        assert video_reader.fps() == 30
        assert video_reader.frames() == 300
        assert video_reader.duration() == 10.0

        success = video_io.utils.trim_video(
            input_path=input_path,
            output_path=output_path,
            start_trim=1.9,
            end_trim=5.2,
            fps=10
        )
        assert success

        video_reader = VideoReader(output_path)
        assert video_reader.fps() == 10
        assert video_reader.frames() == 33
        assert video_reader.duration() == 3.3


def test_trim_video_10_to_30_fps():
    with tempfile.NamedTemporaryFile(suffix='.mp4') as fp:
        input_path = f"{pathlib.Path(__file__).parent.resolve()}/videos/cat-10-seconds-fps-10.mp4"
        output_path = fp.name

        video_reader = VideoReader(input_path)
        assert video_reader.fps() == 10
        assert video_reader.frames() == 100
        assert video_reader.duration() == 10.0

        success = video_io.utils.trim_video(
            input_path=input_path,
            output_path=output_path,
            start_trim=0.0,
            end_trim=5.0,
            fps=30
        )
        assert success

        video_reader = VideoReader(output_path)
        assert video_reader.fps() == 30
        assert video_reader.frames() == 150
        assert video_reader.duration() == 5.0


def test_trim_video_edge_cases():
    with tempfile.NamedTemporaryFile(suffix='.mp4') as fp:
        input_path = f"{pathlib.Path(__file__).parent.resolve()}/videos/cat-10-seconds-fps-10.mp4"
        output_path = fp.name

        video_reader = VideoReader(input_path)
        assert video_reader.fps() == 10
        assert video_reader.frames() == 100
        assert video_reader.duration() == 10.0

        # Test min/max start/end values
        success = video_io.utils.trim_video(
            input_path=input_path,
            output_path=output_path,
            start_trim=0.0,
            end_trim=10.0
        )
        assert success

        video_reader = VideoReader(output_path)
        assert video_reader.fps() == 10
        assert video_reader.frames() == 100
        assert video_reader.duration() == 10

        # Leave off end_trim, should default to video's length
        success = video_io.utils.trim_video(
            input_path=input_path,
            output_path=output_path,
            start_trim=0.0
        )
        assert success

        video_reader = VideoReader(output_path)
        assert video_reader.fps() == 10
        assert video_reader.frames() == 100
        assert video_reader.duration() == 10


def test_trim_video_overwrite():
    with tempfile.NamedTemporaryFile(suffix='.mp4') as fp:

        input_path = f"{pathlib.Path(__file__).parent.resolve()}/videos/cat-10-seconds-fps-10.mp4"
        new_input_path_for_overwriting = fp.name

        shutil.copy(input_path, new_input_path_for_overwriting)

        video_reader = VideoReader(new_input_path_for_overwriting)
        assert video_reader.fps() == 10
        assert video_reader.frames() == 100
        assert video_reader.duration() == 10.0

        # Test min/max start/end values
        success = video_io.utils.trim_video(
            input_path=new_input_path_for_overwriting,
            output_path=new_input_path_for_overwriting,
            start_trim=0.0,
            end_trim=0.1
        )
        assert success

        video_reader = VideoReader(new_input_path_for_overwriting)
        assert video_reader.fps() == 10
        assert video_reader.frames() == 1
        assert video_reader.duration() == 0.1


def test_mosaic():
    input_path = f"{pathlib.Path(__file__).parent.resolve()}/videos/cat-10-seconds-fps-10.mp4"
    input_reader = VideoReader(input_path)

    input_width = input_reader.width()
    input_height = input_reader.height()

    with tempfile.NamedTemporaryFile(suffix='.mp4') as fp:
        size = 4

        video_io.utils.generate_video_mosaic(
            video_inputs=[input_path] * size,
            output_path=fp.name
        )

        video_reader = VideoReader(fp.name)
        assert video_reader.fps() == 10
        assert video_reader.width() == (input_width * 2)
        assert video_reader.height() == (input_height * 2)

    with tempfile.NamedTemporaryFile(suffix='.mp4') as fp:
        size = 1

        with pytest.raises(ValueError):
            video_io.utils.generate_video_mosaic(
                video_inputs=[input_path] * size,
                output_path=fp.name
            )

    with tempfile.NamedTemporaryFile(suffix='.mp4') as fp:
        size = 3

        video_io.utils.generate_video_mosaic(
            video_inputs=[input_path] * size,
            output_path=fp.name
        )

        video_reader = VideoReader(fp.name)
        assert video_reader.fps() == 10
        assert video_reader.width() == input_width * 2
        assert video_reader.height() == input_height * 2

    with tempfile.NamedTemporaryFile(suffix='.mp4') as fp:
        size = 5

        video_io.utils.generate_video_mosaic(
            video_inputs=[input_path] * size,
            output_path=fp.name
        )

        video_reader = VideoReader(fp.name)
        assert video_reader.fps() == 10
        assert video_reader.width() == input_width * 3
        assert video_reader.height() == input_height * 2