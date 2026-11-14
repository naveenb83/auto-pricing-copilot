import sys

try:
    from _bootstrap import add_repo_root
except ImportError:  # executed without the jobs/ dir on sys.path
    import os
    sys.path.insert(0, os.path.join(os.getcwd(), "jobs"))
    from _bootstrap import add_repo_root

add_repo_root()
from datagen.generate import main  # noqa: E402

main(sys.argv[1:])
