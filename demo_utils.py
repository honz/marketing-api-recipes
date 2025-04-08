def print_and_log(run_id: str, message: str):
    # Print the message to the console
    print(message)

    # Log the message to demo_out.log with run_id
    with open("demo_out.log", "a") as log_file:
        log_file.write(f"{run_id}: {message}\n")
