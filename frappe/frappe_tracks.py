
from PyQt5 import QtCore
from PyQt5.QtWidgets import QTableWidgetItem, QCheckBox, QSpinBox
from PyQt5.QtCore import QTimer
from pyqtgraph import ScaleBar, mkBrush, mkPen
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from frappe.utilities.reader_utilities import parse_tracks

FRAME_UPDATE_RATE = 17


class FrappeTrack(QtCore.QObject):

    def __init__(self) -> None:
        super().__init__()
        self.track_plot = None
        self.track_table = None
        self.tracks = None
        self.current_tracks = None
        self.file_path = None
        self.scale_bar = ScaleBar(size=1, width=5, suffix="µm",
                                  brush=mkBrush(255, 255, 255, 255),
                                  pen=mkPen(color=(0, 0, 0)),
                                  offset=(-25, -25))

        self.visible_ids = []
        self.frame_range = [-np.inf, np.inf]
        self.frames_per_update = 25
        self.max_localizations_per_track = 1000
        self.current_chunks = {}

        self.track_ranges = {}
        self._max_frames = {}

        self.plot_timer = QTimer(self)
        self.plot_timer.timeout.connect(self.play_track_visualization)

    def add_track_plot(self, track_plot):
        self.track_plot = track_plot

    def add_track_table(self, track_table):
        self.track_table = track_table

    def open_file(self, track_path):
        self.file_path = track_path
        self.tracks = parse_tracks(self.file_path)
        self.current_tracks = self.tracks.copy()
        self.visible_ids = list(np.unique(self.tracks["id"]))
        self.reset_current_chunks()
        self.setup_max_frames()
        self.setup_track_table()
        self.refresh_plot_view()
        # self.play_track_visualization()

    def reset_current_chunks(self):
        if self.tracks is not None:
            for track_id in np.unique(self.tracks["id"]):
                self.current_chunks[track_id] = 0

    def setup_max_frames(self):
        if self.tracks is not None:
            for track_id in np.unique(self.tracks["id"]):
                current_df = self.tracks[self.tracks["id"] == track_id]
                self._max_frames[track_id] = np.max(current_df["frame"])
                self.track_ranges[track_id] = [0, self._max_frames[track_id]]

    def refresh_plot_view(self, recalculate_tracks=False,
                          synchronize_tracks=False,
                          frame_range=[-np.inf, np.inf],
                          reset=False,
                          clear_existing=False):
        if self.track_plot is not None:
            assert len(frame_range) == 2
            if clear_existing:
                self.track_plot.clear()

            if recalculate_tracks:
                self.calculate_current_tracks(synchronize_tracks,
                                              frame_range,
                                              reset)

            colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
            for i, id in enumerate(self.visible_ids):
                current_df = self.current_tracks[
                    self.current_tracks["id"] == id]
                self.track_plot.plot(current_df["x"].to_numpy(),
                                     current_df["y"].to_numpy(),
                                     pen=mkPen(color=colors[i % len(colors)]))

    def play_track_visualization(self, synchronize_tracks=False):
        self.plot_timer.start(FRAME_UPDATE_RATE)
        self.track_plot.disableAutoRange()

        if synchronize_tracks:
            if self.frame_range[1] > np.max(self.tracks["frame"]):
                self.frame_range = [0, 0]

            self.frame_range[1] += self.frames_per_update
            self.frame_range[0] = max(
                0, self.frame_range[1] - self.max_localizations_per_track)
            self.refresh_plot_view(frame_range=self.frame_range,
                                   recalculate_tracks=True,
                                   synchronize_tracks=True,
                                   clear_existing=True)
        else:
            self.refresh_plot_view(frame_range=self.frame_range,
                                   recalculate_tracks=True,
                                   synchronize_tracks=False,
                                   clear_existing=True)

    def pause_track_visualization(self):
        self.plot_timer.stop()
        self.refresh_plot_view(recalculate_tracks=True,
                               synchronize_tracks=False,
                               frame_range=[-np.inf, np.inf],
                               reset=False,
                               clear_existing=True)

    def generate_track_chunk(self, reset=False):
        if reset:
            self.reset_current_chunks()

        df_list = []
        for track_id in self.visible_ids:
            current_tracks = self.tracks[self.tracks["id"] == track_id]
            if self.plot_timer.isActive():
                frame_lower_bound = max(
                    self.track_ranges[track_id][0],
                    self.current_chunks[track_id] + self.frames_per_update -
                    self.max_localizations_per_track
                    )
                current_tracks = current_tracks[
                    current_tracks["frame"] >= frame_lower_bound]
                current_tracks = current_tracks[
                    current_tracks["frame"] <=
                    min(self.current_chunks[track_id] + self.frames_per_update,
                        self.track_ranges[track_id][1])]
                df_list.append(current_tracks)
                if (self.current_chunks[track_id] + self.frames_per_update <
                        self.track_ranges[track_id][1]):
                    self.current_chunks[track_id] += self.frames_per_update
                elif (self.track_ranges[track_id][1] >
                        self.max_localizations_per_track):
                    self.current_chunks[track_id] = 0

            else:
                current_tracks = current_tracks[
                    current_tracks["frame"] >= self.track_ranges[track_id][0]]
                current_tracks = current_tracks[
                    current_tracks["frame"] <=
                    self.track_ranges[track_id][1]]
                df_list.append(current_tracks)

        return pd.concat(df_list)

    def calculate_current_tracks(self, synchronize_tracks=False,
                                 frame_range=[-np.inf, np.inf],
                                 reset=False):
        assert len(frame_range) == 2

        # if tracks are synchronized, apply restriction globally
        if synchronize_tracks:
            current_tracks = self.tracks[
                self.tracks["frame"] >= frame_range[0]]
            self.current_tracks = current_tracks[
                current_tracks["frame"] <= frame_range[1]]
        else:
            self.current_tracks = self.generate_track_chunk(reset)

    def setup_track_table(self):
        unique_ids = np.unique(self.tracks["id"])
        self.track_table.setRowCount(unique_ids.shape[0])
        self.track_checkboxes = {}
        self.track_frame_start_spinboxes = {}
        self.track_frame_end_spinboxes = {}
        for i, id in enumerate(unique_ids):
            self.track_table.setItem(i, 0, QTableWidgetItem(str(id)))

            self.track_checkboxes[id] = QCheckBox()
            self.track_checkboxes[id].setChecked(True)

            # have to bind id parameter
            self.track_checkboxes[id].stateChanged['int'].connect(
                lambda state, bound_id=id: self.add_remove_track(bound_id,
                                                                 state)
            )

            self.track_table.setCellWidget(i, 1, self.track_checkboxes[id])

            self.track_frame_start_spinboxes[id] = QSpinBox()
            self.track_frame_start_spinboxes[id].setValue(0)

            self.track_frame_start_spinboxes[id].valueChanged['int'].connect(
                lambda value, bound_id=id: self.frame_start_spinbox_changed(
                    value, bound_id)
            )

            self.track_table.setCellWidget(i, 2,
                                           self.track_frame_start_spinboxes[id]
                                           )

            self.track_frame_end_spinboxes[id] = QSpinBox()
            self.track_frame_end_spinboxes[id].setMaximum(self._max_frames[id])
            self.track_frame_end_spinboxes[id].setValue(self._max_frames[id])

            self.track_frame_end_spinboxes[id].valueChanged['int'].connect(
                lambda value, bound_id=id: self.frame_end_spinbox_changed(
                    value, bound_id)
            )

            self.track_table.setCellWidget(i, 3,
                                           self.track_frame_end_spinboxes[id]
                                           )

    def add_remove_track(self, id, state):
        if state > 0 and id not in self.visible_ids:
            self.visible_ids.append(id)
        else:
            self.visible_ids.remove(id)
        self.refresh_plot_view(clear_existing=True)

    def frame_start_spinbox_changed(self, value, id):
        self.track_frame_end_spinboxes[id].setMinimum(value)
        self.track_ranges[id][0] = value
        self.refresh_plot_view(recalculate_tracks=True,
                               synchronize_tracks=False,
                               frame_range=[-np.inf, np.inf],
                               reset=False,
                               clear_existing=True)

    def frame_end_spinbox_changed(self, value, id):
        self.track_frame_start_spinboxes[id].setMaximum(value)
        self.track_ranges[id][1] = value
        self.refresh_plot_view(recalculate_tracks=True,
                               synchronize_tracks=False,
                               frame_range=[-np.inf, np.inf],
                               reset=False,
                               clear_existing=True)
