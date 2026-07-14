"""Recovered-island metadata for the Stix port (re-exports c64_re.islands).

Lives at the ``stix`` top level so every clean layer can self-describe with a
game-package import (``from ..islands import oracle_link``) instead of a
framework import — which keeps ``recovered/`` auditably free of any ``c64_re``
import while still carrying ``@oracle_link`` tags.  No VM deps; the decorator
returns the function unchanged (a documentation/testing aid, never a runtime
dependency).  The island manifest is generated from these tags:

    python c64_re/tools/gen_island_manifest.py stix.recovered -o docs/stix/recovered_islands.md
"""
from c64_re.islands import (  # noqa: F401
    STATUSES,
    OracleLink,
    collect_islands,
    oracle_link,
    render_manifest,
)

__all__ = ["STATUSES", "OracleLink", "collect_islands", "oracle_link", "render_manifest"]
