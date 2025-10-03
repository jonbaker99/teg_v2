# TEG Golf Analytics Dashboard

This repository contains a Streamlit application for analyzing and visualizing golf data for the TEG (The El Golfo) society. It provides a comprehensive set of tools for tracking player performance, viewing historical data, and managing tournament information.

## Features

*   **Interactive Leaderboards:** View real-time leaderboards for ongoing tournaments, with support for both net and gross scoring.
*   **Historical Data:** Explore the complete history of TEG winners, including an honours board for major achievements.
*   **Performance Analysis:** Analyze player performance by course, par, and other metrics.
*   **Scorecards:** View detailed hole-by-hole scorecards for any player, round, or tournament.
*   **Data Management:** A secure interface for updating, editing, and deleting tournament data.

## Project Structure

The repository is organized as follows:

*   `streamlit/`: Contains the main Streamlit application files.
    *   `helpers/`: A directory with helper functions for data processing and display.
    *   `pages/`: While not a conventional pages directory, the numbered files in `streamlit/` act as the different pages of the application.
*   `data/`: Stores all the data files for the application, including tournament results, handicaps, and cached analysis files.
*   `dev_notebooks/`: Contains Jupyter notebooks for development and ad-hoc analysis.
*   `*.py`: Various scripts in the root directory for testing and data management.

## Setup and Installation

To set up the development environment, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/jonbaker99/teg_v2.git
    cd teg_v2
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

To run the Streamlit application, execute the following command from the root directory:

```bash
streamlit run streamlit/nav.py
```

This will start the application on your local machine, and you can access it in your web browser at `http://localhost:8501`.

## Data Management

The application provides a set of tools for managing the data used in the analysis. These tools are available in the "Data" section of the application and include:

*   **Data Update:** Load new round data from a Google Sheet.
*   **Data Edit:** Directly edit the CSV data files.
*   **Delete Data:** Safely delete tournament data with backups.

All data changes are automatically synced with the GitHub repository to ensure data integrity and version control.