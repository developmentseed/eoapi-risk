import subprocess
import json

def run_fio_stac(args):
    command = ["fio", "stac"]
    for key, value in args.items():
        if key.startswith('--'):
            command.append(key)
            if value is not None:
                command.append(str(value))
        elif key.startswith('-'):
            if value:
                command.append(key)
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = result.stdout
        error = result.stderr
    except subprocess.CalledProcessError as e:
        return json.dumps({"error": str(e), "output": e.output, "stderr": e.stderr})
    # Return output and error as JSON
    return json.dumps({"output": output, "error": error})