
from PyQt5 import QtCore
from PyQt5.QtWidgets import QTableWidgetItem, QCheckBox, QSpinBox
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont
from pyqtgraph import ScaleBar, TextItem, mkBrush, mkPen
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import time

from frappe.utilities.reader_utilities import parse_tracks

FRAME_UPDATE_RATE = 50


class FrappeTrack(QtCore.QObject):

    def __init__(self) -> None:
        super().__init__()
        self.track_plot = None
        self.track_table = None
        self.frame_rate_label = None
        self.time_label = None
        self.tracks = None
        self.dt = 0
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
        self.average_update_rate = 1000 / FRAME_UPDATE_RATE
        self._last_update_time = time.time()
        self._play_time = 0
        self.track_centroids = {}
        self.track_radii_of_gyration = {}
        self._show_labels = True
        self.track_labels = {}
        self.track_plot_items = {}
        self.current_chunks = {}
        self.track_ranges = {}
        self._max_frames = {}

        self.plot_timer = QTimer(self)
        self.plot_timer.timeout.connect(self.play_track_visualization)

    @property
    def localizations_per_second(self):
        return self.average_update_rate * self.frames_per_update

    @localizations_per_second.setter
    def localizations_per_second(self, value):
        self.frames_per_update = value / self.average_update_rate

    @property
    def show_labels(self):
        return self._show_labels

    @show_labels.setter
    def show_labels(self, value):
        self._show_labels = value
        self.refresh_plot_view(recalculate_tracks=True,
                               synchronize_tracks=False,
                               frame_range=[-np.inf, np.inf],
                               reset=False,
                               clear_existing=True)

    def add_track_plot(self, track_plot):
        self.track_plot = track_plot

    def add_track_table(self, track_table):
        self.track_table = track_table

    def add_frame_rate_label(self, label):
        self.frame_rate_label = label

    def add_time_label(self, label):
        self.time_label = label

    def open_file(self, track_path):
        self.file_path = track_path
        self.tracks, self.dt = parse_tracks(self.file_path)
        self.current_tracks = self.tracks.copy()
        self.visible_ids = list(np.unique(self.tracks["id"]))
        self.calculate_track_centroids()
        self.add_track_labels()
        self.reset_current_chunks()
        self.setup_max_frames()
        self.setup_track_table()
        self.refresh_plot_view(clear_existing=True)
        self.scale_bar.setParentItem(self.track_plot.plotItem.getViewBox())

    def calculate_track_centroids(self):
        if self.tracks is not None:
            for track_id in np.unique(self.tracks["id"]):
                current_df = self.tracks[self.tracks["id"] == track_id]
                self.track_centroids[track_id] = np.mean(
                    current_df[["x", "y", "z"]].to_numpy(), axis=0
                )
                self.track_radii_of_gyration[track_id] = np.std(
                    current_df[["x", "y", "z"]].to_numpy(), axis=0
                )

    def add_track_labels(self):
        if self.tracks is not None:
            font = QFont()
            font.setPixelSize(9)
            for track_id in np.unique(self.tracks["id"]):
                self.track_labels[track_id] = TextItem(str(track_id))
                self.track_plot.addItem(self.track_labels[track_id])
                label_position = self.track_centroids[track_id] + \
                    1.25 * self.track_radii_of_gyration[track_id]
                self.track_labels[track_id].setPos(
                    label_position[0], label_position[1]
                )
                self.track_labels[track_id].setFont(font)

    def reset(self):
        self.reset_current_chunks()
        self.refresh_plot_view(recalculate_tracks=True)
        self.refresh_labels()

    def reset_current_chunks(self):
        if self.tracks is not None:
            self._play_time = 0
            for track_id in np.unique(self.tracks["id"]):
                self.current_chunks[track_id] = 0

    def refresh_labels(self):
        if self.frame_rate_label is not None:
            self.frame_rate_label.setText(f"Average update rate (1/s): "
                                          f"{self.average_update_rate:.2f}")

        if self.time_label is not None:
            self.time_label.setText(f"Time (ms): {1000*self._play_time:.5f}")

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
            for id in self.visible_ids:
                current_df = self.current_tracks[
                    self.current_tracks["id"] == id]
                if clear_existing:
                    self.track_plot_items[id] = self.track_plot.plot(
                        current_df["x"].to_numpy(),
                        current_df["y"].to_numpy(),
                        pen=mkPen(color=colors[
                            hash(id) % len(colors)])
                    )
                    if self.show_labels:
                        self.track_plot.addItem(self.track_labels[id])
                else:
                    self.track_plot_items[id].setData(
                        current_df["x"].to_numpy(),
                        current_df["y"].to_numpy()
                    )

    def play_track_visualization(self, synchronize_tracks=False):
        self.track_plot.disableAutoRange()

        self.update_frame_rate()
        self._play_time += self.dt

        self.refresh_labels()

        if synchronize_tracks:
            if self.frame_range[1] > np.max(self.tracks["frame"]):
                self.frame_range = [0, 0]

            self.frame_range[1] += self.frames_per_update
            self.frame_range[0] = max(
                0, self.frame_range[1] - self.max_localizations_per_track)
            self.refresh_plot_view(frame_range=self.frame_range,
                                   recalculate_tracks=True,
                                   synchronize_tracks=True,
                                   clear_existing=False)
        else:
            self.refresh_plot_view(frame_range=self.frame_range,
                                   recalculate_tracks=True,
                                   synchronize_tracks=False,
                                   clear_existing=False)

    def update_frame_rate(self):
        self.average_update_rate -= self.average_update_rate / 50
        # multiply by 1000 to get msecs divide by 10 for average
        self.average_update_rate += 1 / ((time.time() - self._last_update_time)
                                         * 50)
        self._last_update_time = time.time()

    def play_track(self):
        self.plot_timer.start(FRAME_UPDATE_RATE)
        self._last_update_time = time.time()
        self._play_time = 0

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
                               clear_existing=False)

    def frame_end_spinbox_changed(self, value, id):
        self.track_frame_start_spinboxes[id].setMaximum(value)
        self.track_ranges[id][1] = value
        self.refresh_plot_view(recalculate_tracks=True,
                               synchronize_tracks=False,
                               frame_range=[-np.inf, np.inf],
                               reset=False,
                               clear_existing=False)
