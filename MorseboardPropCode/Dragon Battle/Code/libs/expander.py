import machine
import libs.mcp23017


class Expander():
    def __init__(self, i2c, address=0x27):
        self.mcp = libs.mcp23017.MCP23017(i2c, address)


class ExpanderPin:

    def __init__(self, expander, pin_id, mode=-1, pull=-1):

        # Use the global expander
        self._expander = expander
        self._pin_id = pin_id
        self._mode = mode
        self._pull = pull

    def on(self):
        self._expander.mcp[self._pin_id].output(1)

    def off(self):
        self._expander.mcp[self._pin_id].output(0)

    def value(self):
        return self._expander.mcp[self._pin_id].value()




