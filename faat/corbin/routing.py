import re


class Router:
    def __init__(self):
        self.routes = []
        self._default = None

    def route(self, path):
        route = parse_route(path)

        def decorator(func):
            self.routes.append((route, func))
            return func

        return decorator

    def default(self, func):
        self._default = func
        return func

    def find_handler(self, path):
        for route, func in self.routes:
            route_params = route.match(path)
            if route_params is None:
                continue
            return func, route_params
        return self._default, {}


def parse_route(path):
    pos = 0
    parts = ["^"]
    parameters = []
    while True:
        m = PARAM_PATTERN.search(path, pos=pos)
        if m:
            parts.append(re.escape(path[pos : m.start()]))
            name, _, type_ = m.group(1).partition(":")
            type_ = type_ or "str"
            if not name:
                raise ValueError(f"Parameter name required: {m.group(1)!r}")
            name = name or str(len(parameters))
            try:
                param_type_pattern, param_parser = PARAM_TYPES[type_]
            except IndexError:
                raise ValueError(f"Unknown param type: {type_}")
            parts.append("(" + param_type_pattern + ")")
            parameters.append(Parameter(name, param_parser))
            pos = m.end()
        else:
            parts.append(re.escape(path[pos:]))
            break

    parts.append("$")
    pattern = re.compile("".join(parts))
    return Route(pattern, parameters)


class Route:
    def __init__(self, pattern, parameters):
        self._pattern = pattern
        self._parameters = parameters

    def match(self, path):
        m = self._pattern.search(path)
        if not m:
            return None
        result = {}
        for parameter, value in zip(self._parameters, m.groups()):
            result[parameter.name] = parameter.parser(value)
        return result


class Parameter:
    def __init__(self, name, parser):
        self.name = name
        self.parser = parser


PARAM_PATTERN = re.compile(r"\<(.+?)\>")

PARAM_TYPES = {
    "int": (r"\d+?", int),
    "str": (r"[^/]+?", str),
    "path": (r".*?", str),
}
