import argparse
import os
import shutil
import sys
import textwrap
from functools import wraps
import inspect
from pathlib import Path
from shutil import copytree
from typing import Any, List, Tuple, Optional, Union, get_args, get_origin
from types import FunctionType

from flamapy.interfaces.python.flamapy_feature_model import FLAMAFeatureModel

# List to store registered commands and their arguments
MANUAL_COMMANDS: List[Tuple[str, str, FunctionType, Tuple[Any, ...]]] = []

# Section headings for the no-args listing, keyed by the operations' default backend
# (None => the operation runs directly on the feature model tree). Backends not listed
# here (future plugins) get their own section headed by the backend name.
BACKEND_SECTIONS: List[Tuple[Optional[str], str]] = [
    (None, "Feature model operations (no solver required)"),
    ("sat", "SAT-based operations (pysat metamodel)"),
    ("bdd", "BDD-based operations (bdd metamodel)"),
    ("z3", "SMT-based operations (z3 metamodel)"),
    ("pysat_diagnosis", "Diagnosis operations (pysat_diagnosis metamodel)"),
]


def _summary(doc: str) -> str:
    """One-line summary of a docstring: whitespace collapsed, first sentence only."""
    collapsed = " ".join(doc.split())
    if not collapsed:
        return "(no description)"
    end = collapsed.find(". ")
    return collapsed[: end + 1] if end != -1 else collapsed


def command(name, description, *args):  # type: ignore
    def decorator(func):  # type: ignore
        MANUAL_COMMANDS.append((name, description, func, args))

        @wraps(func)
        def wrapper(*func_args, **func_kwargs):  # type: ignore
            return func(*func_args, **func_kwargs)

        return wrapper

    return decorator


def extract_commands(
    cls: type,
) -> List[Tuple[str, str, FunctionType, List[inspect.Parameter], Any]]:
    commands = []
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        if getattr(method, "_facade_kind", "operation") != "operation":
            continue  # producers/transformers return models; Python-API only for now
        docstring: Optional[str] = method.__doc__
        signature = inspect.signature(method)
        # Exclude 'self' from parameters
        parameters = list(signature.parameters.values())[1:]  # Skip 'self'
        descriptor = getattr(method, "_facade_descriptor", None)
        commands.append((name, docstring or "", method, parameters, descriptor))
    return commands


@command(
    "generate_plugin",
    "Generates a new plugin skeleton to implement your custom operations. "
    "Run it from the path of the flamapy src directory.",
    ("name", str, "The plugin's name"),
    ("extension", str, "The extension to be registered with the flamapy ecosystem"),
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


def resolve_annotation_type(annotation: Any) -> type:
    """Map a parameter annotation to a concrete type usable as an argparse 'type'.

    Unwraps Optional[X]/Union[X, None] to X; falls back to str for anything
    that is not a plain class (argparse requires a callable).
    """
    if annotation is inspect.Parameter.empty:
        return str
    if get_origin(annotation) is Union:
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        annotation = args[0] if args else str
    return annotation if isinstance(annotation, type) else str


def setup_dynamic_commands(subparsers, dynamic_commands):  # type: ignore
    for name, docstring, method, parameters, _ in dynamic_commands:
        subparser = subparsers.add_parser(name, help=_summary(docstring), description=docstring)
        subparser.add_argument("model_path", type=str, help="Path to the feature model file")
        for param in parameters:
            arg_name = param.name
            if arg_name not in ["model_path"]:  # Avoid duplicates
                arg_type = resolve_annotation_type(param.annotation)
                if param.default == param.empty:  # Positional argument
                    subparser.add_argument(arg_name, type=arg_type, help=arg_type.__name__)
                elif arg_type is bool:  # Boolean flag (type=bool would parse 'False' as True)
                    subparser.add_argument(
                        f"--{arg_name}",
                        action=argparse.BooleanOptionalAction,
                        default=param.default,
                        help="Optional bool",
                    )
                else:  # Optional argument
                    subparser.add_argument(
                        f"--{arg_name}",
                        type=arg_type,
                        default=param.default,
                        help=f"Optional {arg_type.__name__}",
                    )
        subparser.set_defaults(func=method, method_name=name, parameters=parameters)


def setup_manual_commands(subparsers, manual_commands):  # type: ignore
    for name, description, func, args in manual_commands:
        subparser = subparsers.add_parser(name, help=_summary(description), description=description)
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


def _print_section(title: str, rows: List[Tuple[str, str]], column: int, width: int) -> None:
    print(f"{title}:")
    for label, summary in sorted(rows):
        lead = f"  {label:<{column}}  "
        wrapped = textwrap.wrap(summary, width=max(width - len(lead), 20)) or [""]
        print(lead + wrapped[0])
        for line in wrapped[1:]:
            print(" " * len(lead) + line)


def print_command_overview(dynamic_commands) -> None:  # type: ignore
    width = min(shutil.get_terminal_size().columns, 100)
    rows_by_backend: dict[Optional[str], List[Tuple[str, str]]] = {}
    for name, docstring, _, _, descriptor in dynamic_commands:
        backend = getattr(descriptor, "default_backend", None)
        label = name + (" *" if getattr(descriptor, "selectable_backend", False) else "")
        rows_by_backend.setdefault(backend, []).append((label, _summary(docstring)))
    manual_rows = [(name, _summary(description)) for name, description, _, _ in MANUAL_COMMANDS]

    all_rows = [row for rows in rows_by_backend.values() for row in rows] + manual_rows
    column = max((len(label) for label, _ in all_rows), default=0)

    sections = list(BACKEND_SECTIONS)
    known = {backend for backend, _ in sections}
    sections += [(backend, f"Operations on the {backend} backend")
                 for backend in sorted(rows_by_backend.keys() - known, key=str)]
    first = True
    for backend, title in sections:
        rows = rows_by_backend.get(backend)
        if not rows:
            continue
        if not first:
            print()
        _print_section(title, rows, column, width)
        first = False
    print()
    _print_section("Framework developers operations", manual_rows, column, width)
    print()
    print("Operations marked with * accept a --backend option to pick the solver.")
    print("Run 'flamapy <command> --help' for details, or 'flamapy --help' for the full list.")


def flamapy_cli() -> None:
    parser = argparse.ArgumentParser(description="FLAMA Feature Model CLI")
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND", title="commands")

    dynamic_commands = extract_commands(FLAMAFeatureModel)
    setup_dynamic_commands(subparsers, dynamic_commands)
    setup_manual_commands(subparsers, MANUAL_COMMANDS)

    args = parser.parse_args()

    if args.command:
        execute_command(args)
    else:
        print_command_overview(dynamic_commands)
