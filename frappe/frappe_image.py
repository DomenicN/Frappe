
import bioio
# from time import time
# from frappe.utilities.reader_utilities import timed_function
from PyQt5 import QtCore
from PyQt5.QtWidgets import QTableWidgetItem
from pyqtgraph import colormap
import numpy as np
import xml.etree.ElementTree as ET


class FrappeImage(QtCore.QObject):

    def __init__(self) -> None:
        super().__init__()
        self.image_viewer = None
        self.cursor_label = None
        self.current_image = None
        self.file_path = None
        self._T = 0
        self._Z = 0
        self._C = 0
        self._autoscale = True
        self._function_call_times = {}
        self._colormap = colormap.get("gray", source='matplotlib')
        self._invert_colormap = False
        self.last_mouse_pos = QtCore.QPointF(0.0, 0.0)

    @property
    def T(self):
        return self._T

    @T.setter
    def T(self, t):
        self._T = t
        self.refresh_image_view()

    @property
    def C(self):
        return self._C

    @C.setter
    def C(self, c):
        self._C = c
        self.refresh_image_view()

    @property
    def Z(self):
        return self._Z

    @Z.setter
    def Z(self, c):
        self._Z = c
        self.refresh_image_view()

    @property
    def has_T(self):
        if self.current_image is None:
            return False
        return self.current_image.dims.T > 1

    @property
    def has_Z(self):
        if self.current_image is None:
            return False
        return self.current_image.dims.Z > 1

    @property
    def has_C(self):
        if self.current_image is None:
            return False
        return self.current_image.dims.C > 1

    @property
    def autoscale(self):
        return self._autoscale

    @autoscale.setter
    def autoscale(self, auto):
        self._autoscale = auto
        self.refresh_image_view()

    @property
    def colormap(self):
        return self._colormap

    @colormap.setter
    def colormap(self, new_colormap):
        self._colormap = new_colormap
        if self._invert_colormap:
            self._colormap.reverse()
        if self.image_viewer is not None:
            self.image_viewer.setColorMap(self._colormap)

    @property
    def invert_colormap(self):
        return self._invert_colormap

    @invert_colormap.setter
    def invert_colormap(self, invert):
        if self._invert_colormap != invert:
            self._invert_colormap = invert
            self._colormap.reverse()
        if self.image_viewer is not None:
            self.image_viewer.setColorMap(self._colormap)

    def mouse_move_event(self, mouse_position):
        if self.image_viewer is not None:
            assert self.cursor_label is not None
            # mouse_position = event.scenePos()
            self.last_mouse_pos = mouse_position
            view_rectangle = self.image_viewer.view.viewRect()
            bounding_padding = 1.5
            bounding_rect = self.image_viewer.view.boundingRect()
            x_y_values = [view_rectangle.left() + view_rectangle.width() *
                          mouse_position.x() / (bounding_rect.right() -
                                                bounding_rect.left() -
                                                bounding_padding),
                          view_rectangle.top() + view_rectangle.height() *
                          mouse_position.y() / (bounding_rect.bottom() -
                                                bounding_rect.top() -
                                                bounding_padding)]
            if self.current_image is not None:
                image = self.current_image.get_image_data("XY", T=self.T,
                                                          C=self.C, Z=self.Z)

                for i, value in enumerate(x_y_values):
                    if value >= image.shape[i]:
                        x_y_values[i] = image.shape[i] - 1
                    elif value < 0:
                        x_y_values[i] = 0

                image_value = image[
                        np.floor(x_y_values[0]).astype(int),
                        np.floor(x_y_values[1]).astype(int)]
            else:
                image_value = 0

            self.cursor_label.setText(
                f"x: {x_y_values[0]:.2f}, y: {x_y_values[1]:.2f}, "
                f"value: {image_value}")

    def add_viewport(self, image_viewer, cursor_label):
        self.image_viewer = image_viewer
        self.image_viewer.getHistogramWidget().sigLevelsChanged.connect(
            lambda hist: setattr(self, "levels", hist.getLevels())
        )

        self.image_viewer.getImageItem().scene().sigMouseMoved.connect(
            self.mouse_move_event
        )

        self.cursor_label = cursor_label

    def remove_viewport(self):
        self.image_viewer = None
        self.cursor_label = None

    def open_file(self, image_path):
        self.file_path = image_path
        self.fetch_image(image_path)

        self.T, self.C, self.Z = 0, 0, 0

    def fetch_image(self, image_path):
        self.current_image = bioio.BioImage(image_path)

    def refresh_image_view(self, scale_hist=False, reset_autorange=False):
        if scale_hist or self.autoscale:
            self.image_viewer.setImage(self.current_image.get_image_data(
                "XY", T=self.T, C=self.C, Z=self.Z),
                autoRange=reset_autorange,
                autoLevels=self.autoscale)
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
