
import bioio
from PyQt5 import QtCore
from PyQt5.QtWidgets import QTableWidgetItem
from pyqtgraph import ScaleBar, mkBrush, mkPen
import xml.etree.ElementTree as ET
import numpy as np
from matplotlib import pyplot as plt

from frappe.utilities.reader_utilities import parse_tracks


class FrappeTrack(QtCore.QObject):

    def __init__(self) -> None:
        super().__init__()
        self.track_plot = None
        self.tracks = None
        self.file_path = None
        self.scale_bar = ScaleBar(size=1, width=5, suffix="µm",
                                  brush=mkBrush(255, 255, 255, 255),
                                  pen=mkPen(color=(0, 0, 0)),
                                  offset=(-25, -25))

        self.visible_ids = []

    def add_track_plot(self, track_plot):
        self.track_plot = track_plot

    def open_file(self, track_path):
        self.file_path = track_path
        self.tracks = parse_tracks(self.file_path)
        self.visible_ids = np.unique(self.tracks["id"])
        self.refresh_plot_view()

    def fetch_image(self, image_path):
        self.current_image = bioio.BioImage(image_path)

    def refresh_plot_view(self):
        if self.track_plot is not None:
            colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
            for i, id in enumerate(self.visible_ids):
                current_df = self.tracks[self.tracks["id"] == id]
                self.track_plot.plot(current_df["x"].to_numpy(),
                                     current_df["y"].to_numpy(),
                                     pen=mkPen(color=colors[i % len(colors)]))

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
