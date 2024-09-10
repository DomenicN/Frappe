import sys

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QFileDialog, QShortcut, QHeaderView
    )
from PyQt5.QtGui import QKeySequence, QDoubleValidator
from pyqtgraph import colormap, ColorMap, siFormat

from frappe.frappe_image import FrappeImage
from frappe.frappe_tracks import FrappeTrack
from frappe.pyuic5_output import main_window, track_viewer
from frappe.dialogs import metadata_dialog
from frappe.utilities.cursor_label import CursorLabel
from frappe.utilities.decorators import statusbar_message


AVAILABLE_COLORMAPS = (["Gray", "Red", "Green", "Blue", "Cyan", "Magenta",
                        "Yellow", "Hot", "Jet", "Viridis", "Inferno", "Magma"],
                       [colormap.get("gray", source='matplotlib'),
                        ColorMap([0.0, 1.0], ["black", "red"]),
                        ColorMap([0.0, 1.0], ["black", "green"]),
                        ColorMap([0.0, 1.0], ["black", "blue"]),
                        ColorMap([0.0, 1.0], ["black", "cyan"]),
                        ColorMap([0.0, 1.0], ["black", "magenta"]),
                        ColorMap([0.0, 1.0], ["black", "yellow"]),
                        colormap.get("hot", source='matplotlib'),
                        colormap.get("jet", source='matplotlib'),
                        colormap.get("viridis", source='matplotlib'),
                        colormap.get("inferno", source='matplotlib'),
                        colormap.get("magma", source='matplotlib')])


class Window(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = main_window.Ui_MainWindow()
        self.ui.setupUi(self)
        self.cursor_label = CursorLabel(self.statusBar())
        self.setup_image_viewer()
        self.connect_actions()
        self.connect_signals_and_slots()

        # allow only positive real numbers for line edit
        only_float = QDoubleValidator()
        only_float.setRange(0, 1000000)
        self.ui.bar_length.setValidator(only_float)

        # setup status bar
        self.setup_status_bar()

        # initialize track window
        self.track_window = None

    @statusbar_message("Initializing image viewer...")
    def setup_image_viewer(self):
        # set default state of the viewer
        self.frappe_image = FrappeImage()
        self.frappe_image.add_viewport(self.ui.image_viewer)
        self.frappe_image.add_cursor_label(self.cursor_label)
        self.frappe_image.initialize_viewer(roi_button=False,
                                            menu_button=False)
        self.ui.c_slider.label = "Channel"
        self.ui.z_slider.label = "Z"
        self.ui.frame_slider.label = "Frame"
        self.hide_and_show_sliders()
        self.ui.lookup_table_list.addItems(AVAILABLE_COLORMAPS[0])
        self.ui.info_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

    def connect_actions(self):
        self.ui.actionOpen.triggered.connect(self.open_file_dialog)
        self.ui.actionShowMetadata.triggered.connect(self.open_metadata_dialog)

        # keyboard shortcuts for sliders
        self.action_frame_forward_slow = QShortcut(QKeySequence("Right"), self)
        self.action_frame_forward_slow.activated.connect(
            lambda: self.ui.frame_slider.advance_frame(1)
        )
        self.action_frame_reverse_slow = QShortcut(QKeySequence("Left"), self)
        self.action_frame_reverse_slow.activated.connect(
            lambda: self.ui.frame_slider.advance_frame(-1)
        )
        self.action_frame_forward_fast = QShortcut(QKeySequence("Up"), self)
        self.action_frame_forward_fast.activated.connect(
            lambda: self.ui.frame_slider.advance_frame(10)
        )
        self.action_frame_reverse_fast = QShortcut(QKeySequence("Down"), self)
        self.action_frame_reverse_fast.activated.connect(
            lambda: self.ui.frame_slider.advance_frame(-10)
        )

        self.action_z_forward_slow = QShortcut(
            QKeySequence("Shift+Right"), self)
        self.action_z_forward_slow.activated.connect(
            lambda: self.ui.z_slider.advance_frame(1)
        )
        self.action_z_reverse_slow = QShortcut(
            QKeySequence("Shift+Left"), self)
        self.action_z_reverse_slow.activated.connect(
            lambda: self.ui.z_slider.advance_frame(-1)
        )
        self.action_z_forward_fast = QShortcut(
            QKeySequence("Shift+Up"), self)
        self.action_z_forward_fast.activated.connect(
            lambda: self.ui.z_slider.advance_frame(10)
        )
        self.action_z_reverse_fast = QShortcut(
            QKeySequence("Shift+Down"), self)
        self.action_z_reverse_fast.activated.connect(
            lambda: self.ui.z_slider.advance_frame(-10)
        )

        self.action_c_forward_slow = QShortcut(
            QKeySequence("Alt+Right"), self)
        self.action_c_forward_slow.activated.connect(
            lambda: self.ui.c_slider.advance_frame(1)
        )
        self.action_c_reverse_slow = QShortcut(
            QKeySequence("Alt+Left"), self)
        self.action_c_reverse_slow.activated.connect(
            lambda: self.ui.c_slider.advance_frame(-1)
        )
        self.action_c_forward_fast = QShortcut(
            QKeySequence("Alt+Up"), self)
        self.action_c_forward_fast.activated.connect(
            lambda: self.ui.c_slider.advance_frame(10)
        )
        self.action_c_reverse_fast = QShortcut(
            QKeySequence("Alt+Down"), self)
        self.action_c_reverse_fast.activated.connect(
            lambda: self.ui.c_slider.advance_frame(-10)
        )

    def connect_signals_and_slots(self):
        # checkboxes
        self.ui.toggle_histogram.stateChanged['int'].connect(
            self.frappe_image.toggle_histogram
        )

        self.ui.toggle_autoscale.stateChanged['int'].connect(
            lambda q_state: setattr(self.frappe_image,
                                    "autoscale", q_state > 0)
        )

        self.ui.invert_lut.stateChanged['int'].connect(
            lambda invert: setattr(self.frappe_image,
                                   "invert_colormap", invert > 0)
        )

        self.ui.show_scale_bar.stateChanged['int'].connect(
            lambda refresh: self.refresh_scale_bar(refresh > 0)
        )

        # buttons
        self.ui.reset_view.clicked['bool'].connect(
            self.frappe_image.reset_autorange
        )

        self.ui.scale_histogram.clicked['bool'].connect(
            lambda: self.frappe_image.refresh_image_view(scale_hist=True)
        )

        # combo boxes
        self.ui.lookup_table_list.currentIndexChanged['int'].connect(
            lambda x: setattr(self.frappe_image, "colormap",
                              AVAILABLE_COLORMAPS[1][x])
        )

        # sliders
        self.ui.frame_slider.ui.slider.valueChanged['int'].connect(
            lambda t: setattr(self.frappe_image, "T", t - 1)
        )

        self.ui.z_slider.ui.slider.valueChanged['int'].connect(
            lambda z: setattr(self.frappe_image, "Z", z - 1)
        )

        self.ui.c_slider.ui.slider.valueChanged['int'].connect(
            lambda c: setattr(self.frappe_image, "C", c - 1)
        )

        # text line
        self.ui.bar_length.textChanged.connect(
            lambda: self.refresh_scale_bar(self.ui.show_scale_bar.isChecked())
        )

    @statusbar_message("Opening file...")
    def open_file_dialog(self):
        allowed_files = ["Image files (*.czi *.czmbi)", "Track file (*.npy)"]
        filename, file_type = QFileDialog.getOpenFileName(
            parent=self, caption="Open file",
            filter=";;".join(allowed_files))
        if filename:
            if file_type == allowed_files[0]:
                if self.track_window is not None:
                    self.track_window = None
                    self.show()
                self.frappe_image.open_file(filename)
                self.frappe_image.populate_metadata_table(self.ui.info_table)

                self.hide_and_show_sliders()
                self.refresh_scale_bar(self.ui.show_scale_bar.isChecked())

                # update cursor label
                self.update_cursor_label()
            elif file_type == allowed_files[1]:
                self.track_window = TrackWindow(filename, self)
                self.track_window.show()
                if self.isVisible():
                    self.hide()

    def hide_and_show_sliders(self):
        # show relevant sliders
        if self.frappe_image.has_T:
            self.ui.frame_slider.set_maximum(
                self.frappe_image.current_image.dims.T)
            self.ui.frame_slider.show()
        else:
            self.ui.frame_slider.hide()

        if self.frappe_image.has_Z:
            self.ui.z_slider.set_maximum(
                self.frappe_image.current_image.dims.Z)
            self.ui.z_slider.show()
        else:
            self.ui.z_slider.hide()

        if self.frappe_image.has_C:
            self.ui.c_slider.set_maximum(
                self.frappe_image.current_image.dims.C)
            self.ui.c_slider.show()
        else:
            self.ui.c_slider.hide()

        if self.frappe_image.current_image is not None:
            self.ui.reset_view.show()
        else:
            self.ui.reset_view.hide()

    def update_cursor_label(self):
        if self.frappe_image.current_image is not None:
            self.cursor_label.has_x = \
                self.frappe_image.current_image.dims.X > 1
            self.cursor_label.has_y = \
                self.frappe_image.current_image.dims.Y > 1
            self.cursor_label.has_z = \
                self.frappe_image.current_image.dims.Z > 1
            self.cursor_label.has_t = \
                self.frappe_image.current_image.dims.T > 1
            self.cursor_label.has_c = \
                self.frappe_image.current_image.dims.C > 1
            self.cursor_label.has_value = True

        else:
            self.cursor_label.has_none()

        self.cursor_label.hide_and_show_labels()

    def setup_status_bar(self):
        self.cursor_label.setup_status_bar()

    @statusbar_message("Reading metadata...")
    def open_metadata_dialog(self):
        dialog = metadata_dialog.MetadataDialog(
            self.frappe_image.get_metadata_tree())
        dialog.exec()

    def refresh_scale_bar(self, refresh):
        self.ui.bar_length.setEnabled(refresh)
        if (refresh and self.frappe_image.current_image is not None and
                len(self.ui.bar_length.text()) > 0):
            pixel_size_x = \
                self.frappe_image.current_image.physical_pixel_sizes.X
            self.frappe_image.scale_bar.size = \
                float(self.ui.bar_length.text()) / pixel_size_x
            self.frappe_image.scale_bar.text.setText(
                siFormat(float(self.ui.bar_length.text()), suffix="µm")
                )
            self.frappe_image.scale_bar.show()
            self.frappe_image.scale_bar.updateBar()

        else:
            self.frappe_image.scale_bar.hide()

    def about(self):
        QMessageBox.about(
            self,
            "About Sample Editor",
            "<p>A sample text editor app built with:</p>"
            "<p>- PyQt</p>"
            "<p>- Qt Designer</p>"
            "<p>- Python</p>",
        )


class TrackWindow(QMainWindow):
    def __init__(self, file, called_from, parent=None):
        super().__init__(parent)
        self.ui = track_viewer.Ui_MainWindow()
        self.ui.setupUi(self)
        self.frappe_track = FrappeTrack()
        self.frappe_track.open_file(file)
        self.called_from = called_from


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())
