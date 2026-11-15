import sys
import kernel0d as zd

# perform all custom imports
from d2jp import *

[palette, env] = zd.initialize_from_files (sys.argv[3:])
# perform all custom installs
Preda_install (palette)
Predb_install (palette)
PredItem_install (palette)
AltItem_install (palette)
AltGroup_install (palette)
SeqGroup_install (palette)
InitBuffer_install (palette)

top = zd.start_bare (part_name=sys.argv[2], palette=palette, env=env)
# customize the "" 2nd arg as the first injected message into your project
zd.inject (top, "", sys.argv[1])
zd.finalize (top)

