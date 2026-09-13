"""Allow ``python -m solitaire_lab`` as an alias for the ``solitaire-lab`` command."""

import sys

from .cli import main

sys.exit(main())
