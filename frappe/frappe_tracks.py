
import bioio
from PyQt5 import QtCore
from PyQt5.QtWidgets import QTableWidgetItem
from pyqtgraph import colormap, ScaleBar, mkBrush, mkPen
import numpy as np
import xml.etree.ElementTree as ET


class FrappeTrack(QtCore.QObject):

    def __init__(self) -> None:
        super().__init__()
        self.track_plot = None
        self.current_file = None
        self.file_path = None
        self.scale_bar = ScaleBar(size=1, width=5, suffix="µm",
                                  brush=mkBrush(255, 255, 255, 255),
                                  pen=mkPen(color=(0, 0, 0)),
                                  offset=(-25, -25))

    def add_track_plot(self, track_plot):
        self.track_plot = track_plot

    def add_cursor_label(self, cursor_label):
        self.cursor_label = cursor_label
        if self.current_image is not None:
            self.update_cursor_label_dims()

    def update_cursor_label_dims(self):
        self.cursor_label.physical_x = \
            self.current_image.physical_pixel_sizes.X
        self.cursor_label.physical_y = \
            self.current_image.physical_pixel_sizes.Y
        self.cursor_label.physical_z = \
            self.current_image.physical_pixel_sizes.Z

    def remove_viewport(self):
        self.image_viewer = None
        self.cursor_label = None

    def open_file(self, track_path):
        pass

    def fetch_image(self, image_path):
        self.current_image = bioio.BioImage(image_path)

    def refresh_image_view(self, scale_hist=False, reset_autorange=False):
        if scale_hist or self.autoscale:
            self.image_viewer.setImage(self.current_image.get_image_data(
                "XY", T=self.T, C=self.C, Z=self.Z),
                autoRange=reset_autorange,
                autoLevels=True)
        else:
            self.image_viewer.setImage(self.current_image.get_image_data(
                "XY", T=self.T, C=self.C, Z=self.Z),
                autoHistogramRange=False,
                autoRange=reset_autorange,
                autoLevels=self.autoscale)
        self.image_viewer.setColorMap(self._colormap)
        # update the position and value as user moves through stack
        self.mouse_move_event(self.last_mouse_pos)

    def reset_autorange(self):
        self.refresh_image_view(reset_autorange=True)

    def get_metadata_tree(self):
        if self.current_image is None:
            empty_tree = ET.Element(None)
            return empty_tree

        else:
            return self.current_image.metadata

    def initialize_viewer(self, roi_button=False, menu_button=False):
        if roi_button:
            self.image_viewer.ui.roiBtn.show()

        else:
            self.image_viewer.ui.roiBtn.hide()

        if menu_button:
            self.image_viewer.ui.menuBtn.show()

        else:
            self.image_viewer.ui.menuBtn.hide()

    def toggle_histogram(self, q_state):
        if q_state > 0:
            self.image_viewer.ui.histogram.show()

        else:
            self.image_viewer.ui.histogram.hide()

    def populate_metadata_table(self, metadata_table):
        properties = ["File path:",
                      "Image dims (TCZYX):",
                      "Channels:",
                      "Pixel size (x):",
                      "Pixel size (y):"]
        values = [self.file_path,
                  str(self.current_image.shape),
                  ", ".join(self.current_image.channel_names),
                  str(self.current_image.physical_pixel_sizes.X),
                  str(self.current_image.physical_pixel_sizes.Y)]

        if self.current_image.physical_pixel_sizes.Z is not None:
            properties.append("Pixel size (z):")
            values.append(str(self.current_image.physical_pixel_sizes.Z))

        metadata_table.setRowCount(len(properties))

        for i, p_v in enumerate(zip(properties, values)):
            prop, value = p_v
            metadata_table.setItem(i, 0, QTableWidgetItem(prop))
            metadata_table.setItem(i, 1, QTableWidgetItem(value))
