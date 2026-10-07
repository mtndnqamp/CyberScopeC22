"""Adapters for the production team collector and canonical I2Map format."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from i2map_hashing import build_integrity_map, get_device_parameters
from integrity_check import DEFAULT_EXCLUDED
from cyberscope.models import CollectedState

class TeamDeviceStateProvider:
    def __init__(self, parameters=None, excluded=DEFAULT_EXCLUDED):
        self.parameters = parameters
        self.excluded = set(excluded)
    def collect(self):
        params = list(self.parameters.items()) if self.parameters is not None else get_device_parameters()
        return CollectedState(
            monitored={k:v for k,v in params if k not in self.excluded},
            diagnostic={k:v for k,v in params if k in self.excluded},
        )

class TeamIntegrityProvider:
    @property
    def provider_id(self):
        return "cyberscope-team-canonical-json-sha256-v1"
    def digest(self, monitored_state):
        return build_integrity_map(list(monitored_state.items()))["root_hash"]
