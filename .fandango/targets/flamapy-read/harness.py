"""Ask flamapy about one UVL file: exit 0 if it reads the model, else say why and exit 1."""

import logging
import sys
import warnings

warnings.simplefilter("ignore")  # pysat's SyntaxWarnings are not about the file
logging.disable(logging.CRITICAL)  # what is wrong is said once, below

from flamapy.interfaces.python.flamapy_feature_model import FLAMAFeatureModel  # noqa: E402

try:
    FLAMAFeatureModel(sys.argv[1], raise_errors=True)
except RecursionError:
    print("RecursionError: nesting too deep", file=sys.stderr)
    sys.exit(1)
except Exception as exc:  # whatever flamapy raises is a rejection
    print(f"{type(exc).__name__}: {' '.join(str(exc).split())}", file=sys.stderr)
    sys.exit(1)
