import subprocess
import json


def run_fio_stac(pre_commands: list, file: str, args: dict):
    command = [*pre_commands, file]
    for key, value in args.items():
        if key.startswith("--"):
            command.append(key)
            if value is not None:
                command.append(str(value))
        elif key.startswith("-"):
            if value:
                command.append(key)
    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        output = json.loads(result.stdout)
        error = result.stderr
    except subprocess.CalledProcessError as e:
        return {"error": str(e), "output": e.output, "stderr": e.stderr}
    # Return output and error as JSON
    return {"output": output, "error": error}
