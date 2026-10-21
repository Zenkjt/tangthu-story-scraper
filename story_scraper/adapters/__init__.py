from .wattpad import WattpadAdapter

# More-specific adapters must precede broad family adapters when both match.
ADAPTERS = [WattpadAdapter]
