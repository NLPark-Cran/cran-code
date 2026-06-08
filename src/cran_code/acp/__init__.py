def acp_main() -> None:
    """Entry point for the multi-session ACP server."""
    import asyncio

    import acp

    from cran_code.acp.server import ACPServer
    from cran_code.app import enable_logging
    from cran_code.utils.logging import logger

    enable_logging()
    logger.info("Starting ACP server on stdio")
    asyncio.run(acp.run_agent(ACPServer(), use_unstable_protocol=True))
