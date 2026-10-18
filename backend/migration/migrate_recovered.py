import json, os
from pathlib import Path

def load_rows():
    p=Path(__file__).with_name("recovered_verified_v1.json")
    return json.loads(p.read_text(encoding="utf-8"))

def migrate(put, get, now):
    inserted=updated=0
    for row in load_rows():
        rid=row["id"]
        old=get("data",rid)
        obj=dict(row)
        obj["run_id"]=f'{row["date"].replace("-","")}{row["shift"]}{row.get("run_sequence",1)}'
        obj["migration_batch"]="RECOVERED_VERIFIED_V1"
        obj["updated_at"]=now()
        if old:
            # Never downgrade HUMAN_VERIFIED with weaker evidence.
            if old.get("value_source")=="HUMAN_VERIFIED" and obj.get("value_source")!="HUMAN_VERIFIED":
                continue
            obj["created_at"]=old.get("created_at",obj["updated_at"]); updated+=1
        else:
            obj["created_at"]=obj["updated_at"]; inserted+=1
        put("data",rid,obj)
    return {"batch":"RECOVERED_VERIFIED_V1","inserted":inserted,"updated":updated,"total_source":len(load_rows())}
