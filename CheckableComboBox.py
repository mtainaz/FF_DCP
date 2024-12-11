# importing libraries
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt


class CheckableComboBox(QComboBox):
    def __init__(self, parent=None):
        super(CheckableComboBox, self).__init__(parent)
        self.setModel(QStandardItemModel(self))
        self.view().pressed.connect(self.handleItemPressed)
        self._changed = False
        self.setEditable(True)

    def addItem(self, text):
        """Add items with checkboxes to the combo box."""
        item = QStandardItem(text)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Unchecked)
        self.model().appendRow(item)

    def check_items(self):
        """Update the combo box label with selected items."""
        checked_values = []
        for row in range(self.model().rowCount()):
            item = self.model().item(row)
            if item.checkState() == Qt.Checked:
                checked_values.append(item.text())

        # Update the combo box display text based on checked items
        if checked_values:
            self.setCurrentText(f'Selected: {", ".join(checked_values)}')

        return checked_values

    def handleItemPressed(self, index):
        """Toggle the checked state of an item."""
        item = self.model().itemFromIndex(index)
        item.setCheckState(Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)
        self._changed = True
        self.check_items()

    def hidePopup(self):
        """Close the popup only if no changes were made."""
        if not self._changed:
            super(CheckableComboBox, self).hidePopup()
        self._changed = False

