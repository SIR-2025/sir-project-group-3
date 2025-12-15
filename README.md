# Setup and Dependencies

To get started with this project, please follow these steps to install the required dependencies.

1.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv .venv
    ```

2.  **Activate the Virtual Environment:**
    *   **On macOS/Linux:**
        ```bash
        source .venv/bin/activate
        ```
    *   **On Windows (Command Prompt):**
        ```bash
        .venv\Scripts\activate.bat
        ```
    *   **On Windows (PowerShell):**
        ```bash
        .venv\Scripts\Activate.ps1
        ```

3.  **Install Dependencies:**
    With your virtual environment activated, install all necessary packages:
    ```bash
    pip install -r sir_code/requirements.txt
    ```


# Configuration Files

In the `sir_code/conf` directory, add your OpenAI key and Google key in the following files:
- `.openai-key` (for your OpenAI API key)
- `google-key.json` (for your Google credentials)

---

# How to Run the Project

## Setting Up Redis

1. Open a new terminal window.
2. Start the Redis server using the following command:

   ```bash
   redis-server conf/redis/redis.conf
   ```

## Starting Services

1. In another terminal, run the Google Text-to-Speech service:

   ```bash
   run-google-tts
   ```

2. Start the demo by executing:

   ```bash
   python sir_code/main.py
   ```

### Running the Demo on Desktop or Robot

- To run the demo on the desktop, set the `RUN_ROBOT` variable to `0` in `sir_code/main.py`.
  
  ```python
  RUN_ROBOT = 0
  ```

- To run the demo on the robot, set the `RUN_ROBOT` variable to `1` in `sir_code/main.py`.
  
  ```python
  RUN_ROBOT = 1
  ```

   
   
