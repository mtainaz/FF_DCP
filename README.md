Copernicus Data Downloader
This is a PyQt6-based tool that allows users to download NDVI, topological, weather, and fire data of any province using the Copernicus API. The tool supports input validation to ensure correct user input for seamless data retrieval. This data can be used for predictive modeling, such as forest fire prediction or other environmental analyses.

Features
NDVI, Topological, Weather, and Fire Data: Download various datasets provided by the Copernicus API.
Province Selection: Users can select any province to retrieve data.
User Input Validation: Ensures that input values are valid, preventing errors.
Predictive Modeling: Downloaded data can be used in machine learning models for environmental predictions.
Installation
Clone this repository:

bash
Copy
Edit
git clone https://github.com/yourusername/copernicus-data-downloader.git
Install the required dependencies:

bash
Copy
Edit
pip install -r requirements.txt
Run the application:

bash
Copy
Edit
python main.py
Usage
Open the application.
Enter the province for which you want to download data.
Select the type of data (NDVI, topological, weather, or fire data).
The tool will validate the input and fetch the corresponding data from the Copernicus API.
The downloaded data can be saved for use in predictive modeling or further analysis.
Technologies Used
PyQt6: For creating the graphical user interface (GUI).
Copernicus API: For accessing environmental datasets.
Python: The programming language used to build the tool.
License
This project is licensed under the MIT License - see the LICENSE file for details.
