import sys

if "--mcp-server" in sys.argv[1:]:
    # the MCP stdio server: no Qt, so decide before importing the app
    from .mcp_server import main as mcp_main

    sys.exit(mcp_main([a for a in sys.argv[1:] if a != "--mcp-server"]))

from .app import main

main()
