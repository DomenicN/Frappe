import sys

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QFileDialog, QShortcut, QHeaderView
    )
from PyQt5.QtGui import QKeySequence
from pyqtgraph import colormap, ColorMap

from frappe.frappe_image import FrappeImage
from frappe.pyuic5_output.main_window import Ui_MainWindow
from frappe.dialogs import metadata_dialog


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
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setup_image_viewer()
        self.connect_actions()
        self.connect_signals_and_slots()

    def setup_image_viewer(self):
        # set default state of the viewer
        self.frappe_image = FrappeImage()
        self.frappe_image.add_viewport(self.ui.image_viewer,
                                       self.ui.cursor_label)
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

    def open_file_dialog(self):
        filename, _ = QFileDialog.getOpenFileName(
            parent=self, caption="Open file",
            filter="Image files (*.czi);;Acquisition block (*.czmbi)")
        self.frappe_image.open_file(filename)
        self.frappe_image.populate_metadata_table(self.ui.info_table)

        self.hide_and_show_sliders()

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
            self.ui.cursor_label.show()
            self.ui.reset_view.show()
        else:
            self.ui.cursor_label.hide()
            self.ui.reset_view.hide()

    def open_metadata_dialog(self):
        dialog = metadata_dialog.MetadataDialog(
            self.frappe_image.get_metadata_tree())
        dialog.exec()

    def about(self):
        QMessageBox.about(
            self,
            "About Sample Editor",
            "<p>A sample text editor app built with:</p>"
            "<p>- PyQt</p>"
            "<p>- Qt Designer</p>"
            "<p>- Python</p>",
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())
