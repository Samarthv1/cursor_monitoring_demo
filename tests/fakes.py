class FakeConnection:
    def __init__(self, host_key="ssh-ed25519 TESTKEY", output="", error=None):
        self.host_key = host_key
        self._output = output
        self._error = error

    def __enter__(self):
        if self._error is not None:
            raise self._error
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read_output(self):
        return self._output


class ScriptedConnector:
    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.calls = []

    def __call__(self, server):
        self.calls.append(("connect", server.get("host")))
        outcome = self.outcomes.get(server.get("host"), FakeConnection())
        if isinstance(outcome, Exception):
            return FakeConnection(error=outcome)
        if isinstance(outcome, list):
            return outcome.pop(0)
        return outcome
