from __future__ import annotations

import importlib
import sys

# Alias the kimi_code package to cran_code for compatibility.
sys.modules[__name__] = importlib.import_module("cran_code")
