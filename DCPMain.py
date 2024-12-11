import sys
import os
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QLabel, QFileDialog, QMessageBox
)
from DCPHelper import DCPHelper
from DCPConstants import DCPConstants
from DCPShpGenerator import DCPShpGenerator
from CheckableComboBox import CheckableComboBox
from DCPFire import DCPFire
from DCPCopernicus import DCPCopernicus
from DCPTopographical import DCPTopographical
from DCPNdvi import DCPNdvi

class DCPMain(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_firedata = ""
        self.initUI()

    def initUI(self):
        # Set up the window
        self.setWindowTitle('Data Collection and Processing tool')
        self.setGeometry(100, 100, 500, 200)

        # Main layout
        layout = QVBoxLayout()
        # layout.setSpacing(5)

        # File Selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("Path to Canada Shapefile:")
        self.file_search = QLineEdit()
        self.file_button = QPushButton("Choose File")
        self.file_button.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.file_search)
        file_layout.addWidget(self.file_button)

        # Province Selection
        province_layout = QHBoxLayout()
        self.province_label = QLabel("Province:")
        self.province_input = QLineEdit()
        province_layout.addWidget(self.province_label)
        province_layout.addWidget(self.province_input)

        # Generate Shapefile Button
        self.generate_button = QPushButton("Generate Shapefile")
        self.generate_button.clicked.connect(self.generate_shapefile)

        # Fire Data Selection
        fire_layout = QHBoxLayout()
        self.fire_label = QLabel("Path to Canada Fire Data:")
        self.fire_search = QLineEdit()
        self.fire_button = QPushButton("Choose File")
        self.fire_button.clicked.connect(self.select_firedata)
        fire_layout.addWidget(self.fire_label)
        fire_layout.addWidget(self.fire_search)
        fire_layout.addWidget(self.fire_button)

        # Year Selection
        year_layout=QHBoxLayout()
        self.year_label=QLabel("Year:")
        self.year_input = QLineEdit()
        self.year_input.setPlaceholderText("Enter a year between 1940 and 2024")
        year_layout.addWidget(self.year_label)
        year_layout.addWidget(self.year_input)

        # Month Selection
        month_layout = QHBoxLayout()
        self.month_combo_box = CheckableComboBox(self)
        self.month_combo_box.setMinimumWidth(400)

        # create label to show to text
        self.month_label = QLabel("Month(s):")

        # month list
        months = DCPConstants.MONTHS_DICT.keys()

        # adding list of items to combo box
        for month in months:
            self.month_combo_box.addItem(month)

        month_layout.addWidget(self.month_label)
        month_layout.addWidget(self.month_combo_box)

        # Feature Selection
        feature_layout = QHBoxLayout()
        self.feature_combo_box = CheckableComboBox(self)
        self.feature_combo_box.setMinimumWidth(400)

        # create label to show to text
        self.feature_label = QLabel("Feature(s):")

        # feature list
        features = DCPConstants.FEATURES_LIST

        # adding list of items to combo box
        for feature in features:
            self.feature_combo_box.addItem(feature)

        feature_layout.addWidget(self.feature_label)
        feature_layout.addWidget(self.feature_combo_box)

        # Generate Dataset Button
        self.dataset_button = QPushButton("Generate Dataset")
        self.dataset_button.clicked.connect(self.generate_dataset)



        # Add widgets and layouts to main layout
        layout.addLayout(file_layout)
        layout.addLayout(province_layout)
        layout.addWidget(self.generate_button)
        layout.addLayout(fire_layout)
        layout.addLayout(year_layout)
        layout.addLayout(month_layout)
        layout.addLayout(feature_layout)
        layout.addWidget(self.dataset_button)

        # Set layout to window
        self.setLayout(layout)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Choose File", "", "Shapefiles (*.shp)")
        if file_path:
            just_filename=DCPHelper.getFilenameNoPath(file_path)
            self.file_search.setText(f"Selected File: {just_filename}")
            self.selected_file = file_path

    def select_firedata(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Choose File", "", "Shapefiles (*.shp)")
        if file_path:
            just_filename=DCPHelper.getFilenameNoPath(file_path)
            self.fire_search.setText(f"Selected File: {just_filename}")
            self.selected_firedata = file_path

    def generate_shapefile(self):
        self.province = self.province_input.text().title()
        if not hasattr(self, 'selected_file'):
            QMessageBox.warning(self, "File Missing", "Please select a shapefile first.")
            return
        if not self.province or self.province not in DCPConstants.PROVINCE_DICT:
            QMessageBox.warning(self, "Province Missing", "Please enter a valid province.")
            return
        provincial_shp=DCPShpGenerator(self.province, self.selected_file)
        provincial_shp.create_provincial_grid()
        provincial_shp.create_provincial_centroids()
        QMessageBox.information(self, "Shapefile Generated",
                                f"Shapefile generated for {self.province}")

    def generate_dataset(self):
        self.province = self.province_input.text().title()
        if not self.province or self.province not in DCPConstants.PROVINCE_DICT:
            QMessageBox.warning(self, "Province Missing", "Please enter a valid province.")
            return
        directory = self.province.replace(" ", "_")
        if not os.path.exists(f"{directory}/Province.shp") or not os.path.exists(f"{directory}/centroids.shp"):
            QMessageBox.warning(self, "Provincial Datasets Missing", f"Please generate the provincial datasets for {self.province}.")
            return

        self.year=self.year_input.text()
        if not self.year.isdigit() or int(self.year)<1940 or int(self.year)>2024:
            QMessageBox.warning(self, "Year Missing", "Please enter a valid year between 1940 and 2024.")
            return

        self.months=self.month_combo_box.check_items()
        if not self.months:
            QMessageBox.warning(self, "Month(s) Missing", "Please select at least one month.")
            return

        self.features=self.feature_combo_box.check_items()
        if not self.features:
            QMessageBox.warning(self, "Feature(s) Missing", "Please select at least one feature.")
            return

        if not os.path.exists(f"{directory}/FireData.shp") and not self.selected_firedata:
            QMessageBox.warning(self, "Fire Dataset Missing", "Please choose the provincial fire dataset for Canada.")
            return

        # Create instance of DCPFire, if fire data is selected, generate provincial fire data
        fire=DCPFire(self.province, self.year, self.months)
        if self.selected_firedata and not os.path.exists(f"{directory}/FireData.shp"):
            fire.generate_provincial_shp(self.selected_firedata)
        fire_df=fire.generate_dataset()

        topo_df=pd.DataFrame()
        all_df=[]
        merged_df=pd.DataFrame()
        if {"Temperature", "Total Precipitation", "Average Wind Speed", "Relative Humidity"} & set(self.features):
            cop=DCPCopernicus(self.province, self.year, self.months, self.features)
            cop_df=cop.generate_dataset()
            all_df.append(cop_df)

        if "NDVI" in self.features:
            ndvi=DCPNdvi(self.province, self.year, self.months)
            ndvi_df=ndvi.generate_dataset()
            all_df.append(ndvi_df)

        if {"Slope", "Aspect", "Elevation"} & set(self.features):
            topo=DCPTopographical(self.province, self.features)
            topo_df=topo.generate_dataset()

        # If both cop and ndvi present, merge them
        if all_df:
            if len(all_df)==2:
                merged_df=DCPHelper.merge('inner', all_df)
            else:
                merged_df=all_df[0]

        if not merged_df.empty and not topo_df.empty:
            merged_data=DCPHelper.merge_grid_id('inner', merged_df, topo_df)
            merged_data=DCPHelper.merge('left', merged_data, fire_df)
        elif not topo_df.empty:
            merged_data=DCPHelper.merge_grid_id('left', topo_df, fire_df)
        else:
            merged_data=DCPHelper.merge('left', merged_df, fire_df)

        # Fill ignition col with 0 for non-fire dates
        merged_data['ignition'] = merged_data['ignition'].fillna(0)
        merged_data.to_csv(f'{directory}/Final_Dataset_{self.year}.csv', index=False)

        QMessageBox.information(self, "Dataset Generated",
                                f"Copernicus dataset generated for {self.province}")


# Main execution
app = QApplication(sys.argv)
window = DCPMain()
window.show()
sys.exit(app.exec_())