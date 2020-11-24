import json
from dotmap import DotMap


class EventRecord:
    def __init__(self, action, result, timestamp):
        self.action = action
        self.result = result
        self.timestamp = timestamp


class SnapshotRecord:
    def __init__(self, name, snapshot, timestamp):
        self.name = name
        self.snapshot = snapshot
        self.timestamp = timestamp


class TestRecorder:
    def __init__(self, name):
        self.name = name
        self.records = []
        self.snapshots = []

    def add_snapshot(self, snapshot):
        self.snapshots.append(snapshot)

    def add_record(self, record):
        self.records.append(record)

    def serialize_records(self):
        records = []
        for record in self.records:
            records.append(
                {
                    "action": record.action,
                    "result": self.serialize_event_dict(record.result),
                    "timestamp": record.timestamp,
                }
            )
        return records

    def serialize_event_dict(self, events):
        parsed = []
        for event in events.items():
            name = event[0]
            items = event[1]
            parsedItems = []

            if name != "(unknown)" and name != "Transfer" and name != "Approval":
                for item in items:
                    parsedItems.append(dict(item))
                parsed.append({"name": name, "items": parsedItems})
        return parsed

    def print_to_file(self, path):
        output = {"name": self.name, "records": self.serialize_records()}
        with open(path, "w") as outfile:
            json.dump(output, outfile)
