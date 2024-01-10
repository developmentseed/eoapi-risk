import subprocess
import json


def run_cli(pre_commands: list, file: str, args: dict):
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
        print("#"*40)
        print(" ".join(command))
        print("#"*40)
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if not result.stdout.strip():
            output = {}
        else:
            output = json.loads(result.stdout)

        return {"output": output}

    except json.JSONDecodeError as json_err:
        return {"error": "JSON parsing error", "details": str(json_err)}
    except subprocess.CalledProcessError as e:
        return {"error": str(e), "output": e.output, "stderr": e.stderr}
