from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("python-can-remote")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
