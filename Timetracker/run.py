import streamlit.web.cli as stcli
import os
import sys

def main():
    app_path = os.path.join(os.path.dirname(__file__), '1_TimeTracker.py')
    sys.argv = ["streamlit", "run", app_path]
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()