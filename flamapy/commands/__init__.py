import argparse
import os
import sys
from functools import wraps
import inspect
from pathlib import Path
from shutil import copytree
from typing import List, Tuple, Optional
from types import FunctionType

from flamapy.interfaces.python.flamapy_feature_model import FLAMAFeatureModel

# List to store registered commands and their arguments
MANUAL_COMMANDS = []


def command(name, description, *args):  # type: ignore
    def decorator(func):  # type: ignore
        MANUAL_COMMANDS.append((name, description, func, args))

        @wraps(func)
        def wrapper(*func_args, **func_kwargs):  # type: ignore
            return func(*func_args, **func_kwargs)

        return wrapper

    return decorator


def extract_commands(cls: type) -> List[Tuple[str, str, FunctionType, List[inspect.Parameter]]]:
    commands = []
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        docstring: Optional[str] = method.__doc__
        signature = inspect.signature(method)
        # Exclude 'self' from parameters
        parameters = list(signature.parameters.values())[1:]  # Skip 'self'
        commands.append((name, docstring or "", method, parameters))
    return commands


@command(
    "generate_plugin",
    """This command generates a new plugin to implement your
         cusom operations. To execute it you should set yourself in the path of the
         flamapy src directory""",
    ("name", str, "The pluggins name"),
    ("extension", str, "The extansion to be registered with the flamapy ecosystem"),
    ("path", str, "The path to generate it"),
)
def generate_plugin(args):  # type: ignore
    name = args.name
    ext = args.extension
    dst = args.path
    src = "skel_metamodel/"

    # Check DST exist
    if not os.path.isdir(dst):
        print(f"Folder {dst} not exist")
        sys.exit()

    # Check DST is empty
    if len(os.listdir(dst)) != 0:
        print(f"Folder {dst} is not empty")
        sys.exit()

    # Check DST has permissions to WRITE
    if not os.access(dst, os.W_OK):
        print(f"Folder {dst} has not write permissions")
        sys.exit()

    # Generating structure
    print("Generating structure ...")

    copy_files = copytree(src, dst, dirs_exist_ok=True)

    for copy_file in Path(copy_files).glob("**/*"):
        if copy_file.is_dir():
            continue
        with open(copy_file, "r", encoding="utf-8") as file:
            lines = file.readlines()
        with open(copy_file, "w", encoding="utf-8") as filewrite:
            for line in lines:
                out_line = line.replace("__NAME__", name.capitalize()).replace("__EXT__", ext)
                filewrite.write(out_line)

    os.rename(
        os.path.join(dst, "flamapy/metamodels/__NAME__"),
        os.path.join(dst, f"flamapy/metamodels/{name}"),
    )
    print("Plugin generated!")


def setup_dynamic_commands(subparsers, dynamic_commands):  # type: ignore
    for name, docstring, method, parameters in dynamic_commands:
        subparser = subparsers.add_parser(name, help=docstring)
        subparser.add_argument("model_path", type=str, help="Path to the feature model file")
        if "configuration_path" in [param.name for param in parameters]:
            subparser.add_argument(
                "--configuration_path",
                type=str,
                help="Path to the configuration file",
                required=False,
            )
        for param in parameters:
            arg_name = param.name
            if arg_name not in ["model_path"]:  # Avoid duplicates
                if param.default == param.empty:  # Positional argument
                    subparser.add_argument(
                        arg_name, type=param.annotation, help=param.annotation.__name__
                    )
                else:  # Optional argument
                    subparser.add_argument(
                        f"--{arg_name}",
                        type=param.annotation,
                        default=param.default,
                        help=f"Optional {param.annotation.__name__}",
                    )
        subparser.set_defaults(func=method, method_name=name, parameters=parameters)


def setup_manual_commands(subparsers, manual_commands):  # type: ignore
    for name, description, func, args in manual_commands:
        subparser = subparsers.add_parser(name, help=description)
        for arg in args:
            arg_name, arg_type, arg_help = arg
            subparser.add_argument(arg_name, type=arg_type, help=arg_help)
        subparser.set_defaults(func=func)


def execute_command(args: argparse.Namespace) -> None:
    try:
        if hasattr(args, "method_name"):
            cls_instance = FLAMAFeatureModel(args.model_path)
            method_parameters = [param.name for param in args.parameters]
            command_args = {k: v for k, v in vars(args).items() if k in method_parameters}
            method = getattr(cls_instance, args.method_name)
            result = method(**command_args)
            if result is not None:
                print(result)
        else:
            func = args.func
            command_args = {k: v for k, v in vars(args).items() if k != "func"}
            result = func(args)
            if result is not None:
                print(result)
    except FileNotFoundError as fnf_error:
        print(f"File not found error: {fnf_error}")
    except TypeError as type_error:
        print(f"Type error: {type_error}")
    except ValueError as value_error:
        print(f"Value error: {value_error}")
    except KeyError as key_error:
        print(f"Key error: {key_error}")
    except AttributeError as attr_error:
        print(f"Attribute error: {attr_error}")


def flamapy_cli() -> None:
    parser = argparse.ArgumentParser(description="FLAMA Feature Model CLI")
    subparsers = parser.add_subparsers(dest="command")

    dynamic_commands = extract_commands(FLAMAFeatureModel)
    setup_dynamic_commands(subparsers, dynamic_commands)
    setup_manual_commands(subparsers, MANUAL_COMMANDS)

    args = parser.parse_args()

    if args.command:
        execute_command(args)
    else:
        print("Feature model operations:")
        for name, docstring, _, _ in dynamic_commands:
            print(f"  {name}: {docstring}")
        print("Framework developers operations:")
        for name, description, _, _ in MANUAL_COMMANDS:
            print(f"  {name}: {description}")
        print("Execute flamapy --help for more information")
