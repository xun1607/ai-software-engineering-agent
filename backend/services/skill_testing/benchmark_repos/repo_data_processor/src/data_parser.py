import json

def parse_record(json_str):
    data = json.loads(json_str)
    # Bug: KeyError when 'id' key is missing in json_str, should default to 0
    record_id = data["id"]
    val = data.get("value", 0.0)
    return {"id": int(record_id), "value": float(val)}
