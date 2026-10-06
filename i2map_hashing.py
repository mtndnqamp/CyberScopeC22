import hashlib

from pi_device_params import get_device_parameters


def sha256(value):
    return hashlib.sha256(str(value).encode()).hexdigest()
# generates a sha256 hash from any value
# input: value
# output: sha256 hash


def build_integrity_map(params):
    values = {name: value for name, value in params}
    root = sha256("".join(str(v) for _, v in sorted(params)))
    return {"param_values": values, "root_hash": root}
# builds an i2map from a list of parameters that stores the parameters alongside a sha256 hash
# input: list of parameters
# output: i2map


def verify(integrity_map, trusted_root_hash):
    return integrity_map["root_hash"] == trusted_root_hash
# verifies an integrity map against the trusted root hash
# input: integrity map, trusted root
# output: true for matching, false for not matching

def generate_runtime_map():
    params = get_device_parameters()
    imap = build_integrity_map(params)
    return imap
# generates an integrity map based on device's current parameters
# inputs: none
# outputs: i2map
    
def find_diff(integrity_map, trusted_integrity_map):
    current_params = integrity_map["param_values"]
    trusted_params = trusted_integrity_map["trusted_integrity_map"]
    changed_params = [name for name in current_params if name in trusted_params and current_params[name != trusted_params[name]]]
    added_params = [name for name in current_params if name not in trusted_params]
    removed_params = [name for name in trusted_params if name not in current_params]
    return {"changed": changed_params, "added": added_params, "removed": removed_params}
# generates a list of each changed, added or removed parameter between an integrity map and the baseline
# inputs: i2map, trusted baseline
# outputs: list of changed, added and removed params

def check_device_integrity(baseline_map):
    current_map = generate_runtime_map()
    if verify(current_map, baseline_map["root_hash"]):
        return {
            "ok": True,
            "current_map": current_map
        }
    changed_params = find_diff(current_map, baseline_map)
    return {
        "ok": False,
        "current_map": current_map,
        "diff": changed_params,
    }
# generates an integrity map, compares parameters and generates a report containing whether it matches, what changed and the current map
# inputs: baseline i2map
# outputs: report on i2map integrity

def sensor_data_check(sensor_data, baseline_map):
    report = check_device_integrity(baseline_map)
    
    if report["ok"]:
        return {
            "data_accepted": True, 
            "data": sensor_data, 
            "reason": "passed integrity check"
        }
    
    return {
        "data_accepted": False,
        "data": None,
        "reason": f"integrity check failed. mismatches: [report['changed_params']]"
    }
# checks whether sensor data should be accepted by checking device integrity, if passed the data moves through, if failed the data is removed and a reason is provided
# inputs: sensor data to test, trusted baseline
# outputs: data acceptance status, data, reason

if __name__ == "__main__":
    baseline_map = generate_runtime_map()
    print(baseline_map)
    
# todo:
# some testing stuff for the new functions
# loop that listens for sensor data to run the data check