import sys
import hou
import sgtk
from PySide2 import QtWidgets, QtCore
import core  # make sure core.py is on Python path

class UpdatePathsDialog(QtWidgets.QDialog):
    """
    Dialog to configure and run the update paths operation.
    """
    def __init__(self, parent=None):
        super(UpdatePathsDialog, self).__init__(parent)
        self.setWindowTitle("Update File & Alembic Paths")

        # Scope selection
        scope_label = QtWidgets.QLabel("Apply to:")
        self.selected_radio = QtWidgets.QRadioButton("Selected Nodes")
        self.all_radio = QtWidgets.QRadioButton("All Nodes")
        self.all_radio.setChecked(True)
        scope_layout = QtWidgets.QHBoxLayout()
        scope_layout.addWidget(scope_label)
        scope_layout.addWidget(self.selected_radio)
        scope_layout.addWidget(self.all_radio)

        # Publish filter
        self.filter_combo = QtWidgets.QComboBox()
        self.filter_combo.addItems(["apr_ta", "apr", "ta", "all"])
        self.filter_combo.setCurrentText("apr_ta")
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(QtWidgets.QLabel("Version filter:"))
        filter_layout.addWidget(self.filter_combo)

        # Buttons
        self.run_button = QtWidgets.QPushButton("Run")
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.cancel_button)

        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(scope_layout)
        main_layout.addLayout(filter_layout)
        main_layout.addLayout(button_layout)

        # Signals
        self.run_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def get_options(self):
        return {
            "scope": "selected" if self.selected_radio.isChecked() else "all",
            "version_filter": self.filter_combo.currentText()
        }


def update_paths_gui():
    parent = hou.qt.mainWindow()
    dialog = UpdatePathsDialog(parent)
    result = dialog.exec_()

    if result == QtWidgets.QDialog.Accepted:
        opts = dialog.get_options()
        try:
            process_nodes(opts["scope"], opts["version_filter"])
            hou.ui.setStatusMessage("Paths updated successfully.", severity=hou.severityType.ImportantMessage)
        except Exception as e:
            hou.ui.setStatusMessage(f"Error updating paths: {e}", severity=hou.severityType.Error)
    else:
        hou.ui.setStatusMessage("Update cancelled.", severity=hou.severityType.Message)


def process_nodes(scope, version_filter):
    if scope == 'all':
        core.update_all_node_paths(version_filter)
    else:
        for node in hou.selectedNodes():
            for parm_name in core.NODE_PATH_PARMS.get(node.type().name(), []):
                parm = node.parm(parm_name)
                if parm and parm.evalAsString():
                    newp = core.change_shot_in_path(parm.evalAsString(), version_filter=version_filter)
                    if newp and newp != parm.evalAsString():
                        parm.set(newp)

# To launch from shelf: import gui; gui.update_paths_gui()
