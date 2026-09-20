"""KherveMol launcher.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import sys

if __name__ == "__main__":
    # `KherveMol.py --mcp-server` is the MCP stdio server an assistant
    # (Claude Desktop, Claude Code, Cursor...) launches; it must not import
    # Qt, so it is handled before the application module is loaded.
    if "--mcp-server" in sys.argv[1:]:
        from khervemol.mcp_server import main as mcp_main
        sys.exit(mcp_main([a for a in sys.argv[1:] if a != "--mcp-server"]))
    from khervemol.app import main
    main()
