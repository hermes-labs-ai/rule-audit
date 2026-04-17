"""Allow `python -m rule_audit` invocation."""

import sys
from rule_audit.cli import main

sys.exit(main())
