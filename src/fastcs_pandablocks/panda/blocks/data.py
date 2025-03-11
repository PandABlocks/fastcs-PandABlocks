import asyncio
import enum
import logging
import os
from asyncio import CancelledError
from collections import deque
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Union

import numpy as np
from fastcs.attributes import AttrR, AttrRW
from fastcs.controller import SubController
from fastcs.datatypes import Bool, Enum, Float, Int, String, Table
from numpy.typing import DTypeLike
from pandablocks.hdf import (
    EndData,
    FrameData,
    Pipeline,
    StartData,
    create_default_pipeline,
    stop_pipeline,
)
from pandablocks.responses import Data, EndReason, ReadyData

from fastcs_pandablocks.types import PandaName

HDFReceived = Union[ReadyData, StartData, FrameData, EndData]


class CaptureMode(enum.Enum):
    """
    The mode which the circular buffer will use to flush.
    """

    #: Wait till N frames are recieved then write them
    #:  and finish capture
    FIRST_N = 0

    #: On EndData write the last N frames
    LAST_N = 1

    #: Write data as received until Capture set to 0
    FOREVER = 2


class NumCapturedSetter(Pipeline):
    def __init__(self, number_captured_setter: Callable) -> None:
        self.number_captured_setter = number_captured_setter
        self.number_captured_setter(0)
        super().__init__()

        self.what_to_do = {int: self.set_record}

    def set_record(self, value: int):
        self.number_captured_setter(value)


class HDF5Buffer:
    _buffer_index = None
    start_data = None
    number_of_received_rows = 0
    finish_capturing = False
    number_of_rows_in_circular_buffer = 0

    def __init__(
        self,
        capture_mode: CaptureMode,
        filepath: Path,
        number_of_rows_to_capture: int,
        status_message_setter: Callable,
        number_received_setter: Callable,
        number_captured_setter_pipeline: NumCapturedSetter,
        dataset_name_cache: dict[str, dict[str, str]],
    ):
        # Only one filename - user must stop capture and set new FileName/FilePath
        # for new files

        self.circular_buffer: deque[FrameData] = deque()
        self.capture_mode = capture_mode

        match capture_mode:
            case CaptureMode.FIRST_N:
                self._handle_FrameData = self._capture_first_n
            case CaptureMode.LAST_N:
                self._handle_FrameData = self._capture_last_n
            case CaptureMode.FOREVER:
                self._handle_FrameData = self._capture_forever
            case _:
                raise RuntimeError("Invalid capture mode")

        self.filepath = filepath
        self.number_of_rows_to_capture = number_of_rows_to_capture
        self.status_message_setter = status_message_setter
        self.number_received_setter = number_received_setter
        self.number_captured_setter_pipeline = number_captured_setter_pipeline
        self.number_captured_setter_pipeline.number_captured_setter(0)

        self.dataset_name_cache = dataset_name_cache

        if (
            self.capture_mode == CaptureMode.LAST_N
            and self.number_of_rows_to_capture <= 0
        ):
            raise RuntimeError("Number of rows to capture must be > 0 on LAST_N mode")

        self.start_pipeline()

    def __del__(self):
        if self.pipeline[0].is_alive():
            stop_pipeline(self.pipeline)

    def put_data_to_file(self, data: HDFReceived):
        try:
            self.pipeline[0].queue.put_nowait(data)
        except Exception as ex:
            logging.exception(f"Failed to save the data to HDF5 file: {ex}")

    def start_pipeline(self):
        self.pipeline = create_default_pipeline(
            iter([str(self.filepath)]),
            self.dataset_name_cache,
            self.number_captured_setter_pipeline,
        )

    def _handle_StartData(self, data: StartData):
        if self.start_data and data != self.start_data:
            # PandA was disarmed, had config changed, and rearmed.
            # Cannot process to the same file with different start data.
            logging.error(
                "New start data detected, differs from previous start "
                "data for this file. Aborting HDF5 data capture."
            )

            self.status_message_setter(
                "Mismatched StartData packet for file",
            )
            self.put_data_to_file(
                EndData(self.number_of_received_rows, EndReason.START_DATA_MISMATCH)
            )

            self.finish_capturing = True

        # Only pass StartData to pipeline if we haven't previously
        else:
            # In LAST_N mode, wait till the end of capture to write
            # the StartData to file.
            # In FOREVER mode write the StartData to file if it's the first received.
            if (
                self.capture_mode == CaptureMode.FIRST_N
                or self.capture_mode == CaptureMode.FOREVER
                and not self.start_data
            ):
                self.put_data_to_file(data)

            self.start_data = data

    def _capture_first_n(self, data: FrameData):
        """
        Capture framedata as it comes in. Stop when number of frames exceeds
        number_of_rows_to_capture, and cut off the data so that it's length
        number_of_rows_to_capture.
        """
        self.number_of_received_rows += len(data.data)

        if (
            self.number_of_rows_to_capture > 0
            and self.number_of_received_rows > self.number_of_rows_to_capture
        ):
            # Discard extra collected data points if necessary
            data.data = data.data[
                : self.number_of_rows_to_capture - self.number_of_received_rows
            ].copy()
            self.number_of_received_rows = self.number_of_rows_to_capture

        self.put_data_to_file(data)
        self.number_received_setter(self.number_of_received_rows)

        if (
            self.number_of_rows_to_capture > 0
            and self.number_of_received_rows == self.number_of_rows_to_capture
        ):
            # Reached configured capture limit, stop the file
            logging.info(
                f"Requested number of frames ({self.number_of_rows_to_capture}) "
                "captured, disabling Capture."
            )
            self.status_message_setter("Requested number of frames captured")
            self.put_data_to_file(EndData(self.number_of_received_rows, EndReason.OK))
            self.finish_capturing = True

    def _capture_forever(self, data: FrameData):
        self.put_data_to_file(data)
        self.number_of_received_rows += len(data.data)
        self.number_received_setter(self.number_of_received_rows)

    def _capture_last_n(self, data: FrameData):
        """
        Append every FrameData to a buffer until the number of rows equals
        `:NumCapture`. Then rewrite the data circularly.

        Only write the data once PCAP is received.
        """
        self.circular_buffer.append(data)
        self.number_of_received_rows += len(data.data)
        self.number_of_rows_in_circular_buffer += len(data.data)

        if self.number_of_rows_in_circular_buffer > self.number_of_rows_to_capture:
            self.status_message_setter(
                "NumCapture received, rewriting first frames received"
            )

        else:
            self.status_message_setter("Filling buffer to NumReceived")

        while self.number_of_rows_in_circular_buffer > self.number_of_rows_to_capture:
            first_frame_data = self.circular_buffer.popleft()
            first_frame_data_length = len(first_frame_data.data)

            if first_frame_data_length > self.number_of_rows_to_capture:
                # More data than we want to capture, all in a single FrameData
                # We can just slice with the NumCapture since this has to be the
                # only FrameData in the buffer at this point
                assert len(self.circular_buffer) == 0
                shrinked_data = first_frame_data.data[
                    -self.number_of_rows_to_capture :
                ].copy()
                first_frame_data.data = shrinked_data
                self.circular_buffer.appendleft(first_frame_data)
                self.number_of_rows_in_circular_buffer = self.number_of_rows_to_capture
            elif (
                first_frame_data_length
                > self.number_of_rows_in_circular_buffer
                - self.number_of_rows_to_capture
            ):
                # We can slice from the beginning of the FrameData to have the desired
                # number of rows
                indices_to_discard = (
                    self.number_of_rows_in_circular_buffer
                    - self.number_of_rows_to_capture
                )
                shrinked_data = first_frame_data.data[indices_to_discard:].copy()
                first_frame_data.data = shrinked_data
                self.circular_buffer.appendleft(first_frame_data)
                self.number_of_rows_in_circular_buffer -= indices_to_discard
                assert (
                    self.number_of_rows_in_circular_buffer
                    == self.number_of_rows_to_capture
                )
            else:
                # If we remove the enire first frame data then the buffer will still
                # be too big, or it will be exactly the number of rows we want
                self.number_of_rows_in_circular_buffer -= first_frame_data_length

        self.number_received_setter(self.number_of_received_rows)

    def _handle_EndData(self, data: EndData):
        match self.capture_mode:
            case CaptureMode.LAST_N:
                # In LAST_N only write FrameData if the EndReason is OK
                if data.reason not in (EndReason.OK, EndReason.MANUALLY_STOPPED):
                    self.status_message_setter(
                        f"Stopped capturing with reason {data.reason}, "
                        "skipping writing of buffered frames"
                    )
                    self.finish_capturing = True
                    return

                self.status_message_setter(
                    "Finishing capture, writing buffered frames to file"
                )
                assert self.start_data is not None
                self.put_data_to_file(self.start_data)
                for frame_data in self.circular_buffer:
                    self.put_data_to_file(frame_data)

            case CaptureMode.FOREVER:
                if data.reason != EndReason.MANUALLY_STOPPED:
                    self.status_message_setter(
                        "Finished capture, waiting for next ReadyData"
                    )
                    return

            case CaptureMode.FIRST_N:
                pass  # Frames will have already been written in FirstN

            case _:
                raise RuntimeError("Unknown capture mode")

        self.status_message_setter("Finished capture")
        self.finish_capturing = True
        self.put_data_to_file(data)

    def handle_data(self, data: HDFReceived):
        match data:
            case ReadyData():
                pass
            case StartData():
                self.status_message_setter("Starting capture")
                self._handle_StartData(data)
            case FrameData():
                self._handle_FrameData(data)
            case EndData():
                self._handle_EndData(data)
            case _:
                raise RuntimeError(
                    f"Data was recieved that was of type {type(data)}, not"
                    "StartData, EndData, ReadyData, or FrameData"
                )


@dataclass
class DatasetAttributes:
    """A dataset name and capture mode"""

    name: AttrRW[str]
    capture: AttrRW[enum.Enum]


class DatasetTableWrapper:
    """Used for outputing formatted dataset names in the HDF5 writer, and creating
    and updating the HDF5 `DATASETS` table attribute."""

    NUMPY_TYPE: list[tuple[str, DTypeLike]] = [
        ("Name", np.dtype("S1000")),
        ("DType", np.dtype("S1000")),
    ]

    def __init__(
        self,
        dataset_cache: dict[PandaName, DatasetAttributes],
    ):
        self._dataset_cache = dataset_cache

    def hdf_writer_names(self) -> dict[str, dict[str, str]]:
        """Formats the current dataset names for use in the HDFWriter"""

        hdf_names: dict[str, dict[str, str]] = {}
        for panda_name, dataset in self._dataset_cache.items():
            capture_str_value = dataset.capture.get().value
            name_str_value = dataset.name.get()
            if not name_str_value or capture_str_value == "No":
                continue

            hdf_names[str(panda_name)] = hdf_name = {}

            hdf_name[capture_str_value.split(" ")[-1]] = name_str_value
            # Suffix -min and -max if both are present
            if "Min Max" in capture_str_value:
                hdf_name["Min"] = f"{name_str_value}-min"
                hdf_name["Max"] = f"{name_str_value}-max"

        return hdf_names

    def get_numpy_table(self) -> np.ndarray:
        return np.array(
            [
                (dataset.name.get(), "float64")
                for dataset in self._dataset_cache.values()
                if dataset.name.get() and dataset.capture.get() != "No"
            ],
            dtype=self.NUMPY_TYPE,
        )

    def set_on_update_callback(self, table_attribute: AttrR):
        async def callback(value):
            await table_attribute.set(self.get_numpy_table())

        for dataset_attributes in self._dataset_cache.values():
            dataset_attributes.name.add_update_callback(callback)
            dataset_attributes.capture.add_update_callback(callback)


class DataController(SubController):
    """Class to create and control the records that handle HDF5 processing"""

    hdf_directory = AttrRW(String(), description="File path for HDF5 files.")

    create_directory = AttrRW(
        Int(),
        description="Directory creation depth",
        initial_value=0,
    )

    directory_exists = AttrR(
        Bool(), description="Directory exists", initial_value=False
    )

    hdf_file_name = AttrRW(
        String(),
        description="File name prefix for HDF5 files",
        initial_value="",
    )

    hdf_full_file_path = AttrR(
        String(),
        description="Full HDF5 file name with directory",
        initial_value="",
    )

    num_capture = AttrRW(
        Int(min=0),
        description="Number of frames to capture. 0=infinite",
        initial_value=0,  # Infinite capture
    )

    num_captured = AttrR(
        Int(),
        description="Number of frames written to file.",
        initial_value=0,
    )

    num_received = AttrR(
        Int(),
        description="Number of frames received from panda.",
        initial_value=0,
    )
    flush_period = AttrRW(
        Float(units="s"),
        description="Frequency that data is flushed (seconds).",
        initial_value=1.0,
    )

    capture = AttrRW(
        Bool(), description="Start/stop HDF5 capture.", initial_value=False
    )
    capture_mode = AttrRW(
        Enum(CaptureMode),
        description="Choose how to hdf writer flushes",
        initial_value=CaptureMode.FIRST_N,
    )

    status = AttrR(
        String(),
        description="Status of HDF5 capture",
        initial_value="OK",
    )

    def __init__(
        self,
        client_data: Callable[[bool, float], AsyncGenerator[Data, None]],
        dataset_attributes: dict[PandaName, DatasetAttributes],
    ):
        super().__init__()

        if find_spec("h5py") is None:
            logging.warning("No HDF5 support detected - skipping creating HDF5 records")
            return

        self._client_data = client_data
        self._dataset_table_wrapper = DatasetTableWrapper(dataset_attributes)

        datasets_attribute = AttrR(
            Table(self._dataset_table_wrapper.NUMPY_TYPE),
            description="HDF5 dataset names.",
            initial_value=self._dataset_table_wrapper.get_numpy_table(),
        )
        self.attributes["datasets"] = datasets_attribute
        self._dataset_table_wrapper.set_on_update_callback(datasets_attribute)

        self.hdf_directory.add_update_callback(self._update_directory_path)
        self.hdf_file_name.add_update_callback(self._update_full_file_path)
        self.capture.add_update_callback(self._capture_on_update)

    async def _update_directory_path(self, new_val) -> None:
        """Handles writes to the directory path PV, creating
        directories based on the setting of the CreateDirectory record"""
        new_path = Path(new_val).absolute()
        create_dir_depth = self.create_directory.get()
        max_dirs_to_create = 0
        if create_dir_depth < 0:
            max_dirs_to_create = abs(create_dir_depth)
        elif create_dir_depth > len(new_path.parents):
            max_dirs_to_create = 0
        elif create_dir_depth > 0:
            max_dirs_to_create = len(new_path.parents) - create_dir_depth

        logging.debug(f"Permitted to create up to {max_dirs_to_create} dirs.")
        dirs_to_create = 0
        for p in reversed(new_path.parents):
            if not p.exists():
                if dirs_to_create == 0:
                    # First directory level that does not exist, log it.
                    logging.error(f"All dir from {str(p)} and below do not exist!")
                dirs_to_create += 1
            else:
                logging.info(f"{str(p)} exists")

        # Account for target path itself not existing
        if not os.path.exists(new_path):
            dirs_to_create += 1

        logging.debug(f"Need to create {dirs_to_create} directories.")

        # Case where all dirs exist
        if dirs_to_create == 0:
            if os.access(new_path, os.W_OK):
                status_msg = "Dir exists and is writable"
                await self.directory_exists.set(True)
            else:
                status_msg = "Dirs exist but aren't writable."
                await self.directory_exists.set(False)
        # Case where we will create directories
        elif dirs_to_create <= max_dirs_to_create:
            logging.debug(f"Attempting to create {dirs_to_create} dir(s)...")
            try:
                os.makedirs(new_path, exist_ok=True)
                status_msg = f"Created {dirs_to_create} dirs."
                await self.directory_exists.set(True)
            except PermissionError:
                status_msg = "Permission error creating dirs!"
                await self.directory_exists.set(False)
        # Case where too many directories need to be created
        else:
            status_msg = f"Need to create {dirs_to_create} > {max_dirs_to_create} dirs."
            await self.directory_exists.set(False)

        if self.directory_exists.get() == 0:
            logging.error(status_msg)
        else:
            logging.debug(status_msg)

        await self.status.set(status_msg)

        await self._update_full_file_path(new_val)

    async def _update_full_file_path(self, value: str) -> None:
        await self.hdf_full_file_path.set(self._get_filepath())

    async def _handle_hdf5_data(self) -> None:
        """Handles writing HDF5 data from the PandA to file, based on configuration
        in the various HDF5 records.
        This method expects to be run as an asyncio Task."""
        buffer: HDF5Buffer | None = None
        try:
            # Set up the hdf buffer

            if not self.hdf_directory.get() == 1:
                raise RuntimeError(
                    "Configured HDF directory does not exist or is not writable!"
                )

            num_capture: int = self.num_capture.get()
            capture_mode: CaptureMode = CaptureMode(self.capture_mode.get())
            filepath = self._get_filepath()

            number_captured_setter_pipeline = NumCapturedSetter(self.num_captured.set)

            await self.attributes["datasets"].set(  # type: ignore
                self._dataset_table_wrapper.get_numpy_table()
            )

            buffer = HDF5Buffer(
                capture_mode,
                Path(filepath),
                num_capture,
                self.status.set,
                self.num_received.set,
                number_captured_setter_pipeline,
                self._dataset_table_wrapper.hdf_writer_names(),
            )
            flush_period: float = self.flush_period.get()
            async for data in self._client_data(False, flush_period):
                logging.debug(f"Received data packet: {data}")

                buffer.handle_data(data)  # type: ignore
                if buffer.finish_capturing:
                    break

        except CancelledError:
            logging.info("Capturing task cancelled, closing HDF5 file")
            await self.status.set("Capturing disabled")
            # Only send EndData if we know the file was opened - could be cancelled
            # before PandA has actually send any data
            if buffer and buffer.capture_mode != CaptureMode.LAST_N:
                buffer.put_data_to_file(
                    EndData(buffer.number_of_received_rows, EndReason.MANUALLY_STOPPED)
                )

        except Exception:
            logging.exception("HDF5 data capture terminated due to unexpected error")
            await self.status.set(
                "Capture disabled, unexpected exception.",
            )
            # Only send EndData if we know the file was opened - exception could happen
            # before file was opened
            if (
                buffer
                and buffer.start_data
                and buffer.capture_mode != CaptureMode.LAST_N
            ):
                buffer.put_data_to_file(
                    EndData(buffer.number_of_received_rows, EndReason.UNKNOWN_EXCEPTION)
                )

        finally:
            logging.debug("Finishing processing HDF5 PandA data")
            await self.num_received.set(buffer.number_of_received_rows if buffer else 0)
            await self.capture.set(False)

    def _get_filepath(self) -> str:
        """Create the file path for the HDF5 file from the relevant records"""
        return "/".join([self.hdf_directory.get(), self.hdf_file_name.get()])

    async def _capture_on_update(self, value: int) -> None:
        """Process an update to the Capture record, to start/stop recording HDF5 data"""
        logging.debug(f"Entering HDF5:Capture record on_update method, value {value}.")
        if value:
            if self._handle_hdf5_data_task:
                logging.warning("Existing HDF5 capture running, cancelling it.")
                self._handle_hdf5_data_task.cancel()

            self._handle_hdf5_data_task = asyncio.create_task(self._handle_hdf5_data())
        else:
            assert self._handle_hdf5_data_task
            self._handle_hdf5_data_task.cancel()  # Abort any HDF5 file writing
            self._handle_hdf5_data_task = None
