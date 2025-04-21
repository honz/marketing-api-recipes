import os

def print_and_log(run_id: str, message: str):
    # Print the message to the console
    print(message)

    # Get root directory path
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_path = os.path.join(root_dir, "demo_out.log")

    # Log the message to demo_out.log with run_id
    with open(log_path, "a") as log_file:
        log_file.write(f"{run_id}: {message}\n")
