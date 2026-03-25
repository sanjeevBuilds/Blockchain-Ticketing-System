import os
import subprocess
import sys
import time
import webbrowser


ROOT = os.path.dirname(os.path.abspath(__file__))


def spawn(command):
    kwargs = {"cwd": ROOT}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    return subprocess.Popen(command, **kwargs)


def main():
    processes = []
    try:
        processes.append(spawn([sys.executable, "node_server.py", "--name", "Server A", "--port", "5001"]))
        processes.append(spawn([sys.executable, "node_server.py", "--name", "Server B", "--port", "5002"]))
        processes.append(spawn([sys.executable, "node_server.py", "--name", "Server C", "--port", "5003"]))
        processes.append(spawn([sys.executable, "app.py", "--port", "5000"]))

        time.sleep(2.5)
        webbrowser.open("http://127.0.0.1:5000")
        webbrowser.open("http://127.0.0.1:5001")
        webbrowser.open("http://127.0.0.1:5002")
        webbrowser.open("http://127.0.0.1:5003")

        print("Controller + Server A/B/C launched. Press Ctrl+C to stop all.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping all servers...")
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()


if __name__ == "__main__":
    main()
