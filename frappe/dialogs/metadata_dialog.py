from PyQt5.QtWidgets import QDialog, QTreeWidgetItem
from frappe.pyuic5_output.metadata_dialog import Ui_ImageMetadata


class MetadataDialog(QDialog):

    def __init__(self, metadata_tree):
        super().__init__()
        self.ui = Ui_ImageMetadata()
        self.ui.setupUi(self)
        self.setWindowTitle("Metadata")
        self.metadata_xml = metadata_tree

    def populate_metadata(self):
        # iterate over metadata
        for element in self.metadata_xml[0]:
            current_widget_item = QTreeWidgetItem(self.ui.metadata_tree)
            current_widget_item.setText(0, element.tag)
            current_widget_item.setText(1, element.text)
            self.populate_children_recursively(element, current_widget_item)
            self.ui.metadata_tree.addTopLevelItem(current_widget_item)

    def populate_children_recursively(self, parent, parent_widget):
        if parent:
            # parent has children
            for element in parent:
                current_widget_item = QTreeWidgetItem(parent_widget)
                current_widget_item.setText(0, element.tag)
                current_widget_item.setText(1, element.text)
                parent_widget.addChild(current_widget_item)

                self.populate_children_recursively(element,
                                                   current_widget_item)

    def exec(self):
        self.populate_metadata()
        super().exec()
