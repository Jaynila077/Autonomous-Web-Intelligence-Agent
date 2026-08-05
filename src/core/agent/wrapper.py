import asyncio

class SyncAgentWrapper:
    """
    Bridges async MCP tools for synchronous callers by wrapping the compiled agent.
    Intercepts .invoke() and safely routes it to .ainvoke() within an event loop.
    """
    def __init__(self, agent):
        self.agent = agent

    def invoke(self, *args, **kwargs):
        return asyncio.run(self.agent.ainvoke(*args, **kwargs))

    def __getattr__(self, name):
        return getattr(self.agent, name)