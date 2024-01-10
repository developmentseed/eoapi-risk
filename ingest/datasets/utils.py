import subprocess
import json

def run_fio_stac(args):
    # Base command
    command = ["fio", "stac"]

    # Add arguments and options to the command
    for key, value in args.items():
        if key.startswith('--'):
            # It's an option with a value
            command.append(key)
            if value is not None:
                command.append(str(value))
        elif key.startswith('-'):
            # It's a flag
            if value:
                command.append(key)

    # Execute the command
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = result.stdout
        error = result.stderr
    except subprocess.CalledProcessError as e:
        # Handle errors in command execution
        return json.dumps({"error": str(e), "output": e.output, "stderr": e.stderr})

    # Return output and error as JSON
    return json.dumps({"output": output, "error": error})

# Example usage with dummy arguments
args = {
    "--datetime": "2020-01-01T01:01:01",
    "--collection": "collection-id",
    # Add other options and flags as needed
}
output_json = run_fio_stac(args)
print(output_json)
