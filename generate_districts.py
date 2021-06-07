import json
import csv

state_districts = json.load(open("districts.json"))
political_party_ids = {1: "PAN", 2: "PRI", 3: "PRD", 4: "PVEM", 5: "PT", 6: "MC", 8: "MORENA", 9: "PES", 10: "RSP", 11: "FXM"}
inv_dict = {value:key for key, value in political_party_ids.items()}

state_number_map = {state["nombreEstado"]:state["idEstado"] for state in state_districts}
print(state_number_map)

with open("vxm_corrected.csv") as csv_file:
  vxm_reader = csv.reader(csv_file)

  for row in vxm_reader:
    ctr, state_name, district_id, old_party_name, party_name = row

    if ctr == "Número " or ctr == "":
      continue
    else:
      state_id = state_number_map[state_name.strip()]
      print(f"{state_id}-{district_id}: {party_name}")
      state_districts[int(state_id) - 1]["distritos"][int(district_id) - 1]["vxm_party_id"] = inv_dict[party_name.strip()]

with open("jhh_corrected.csv") as csv_file:
  jhh_reader = csv.reader(csv_file)

  for row in jhh_reader:
    ctr, state_name, district_id, old_party_name, party_name = row

    if ctr == "Número " or ctr == "":
      continue
    else:
      state_id = state_number_map[state_name.strip()]
      print(f"{state_id}-{district_id}: {party_name}")
      state_districts[int(state_id) - 1]["distritos"][int(district_id) - 1]["jhh_party_id"] = inv_dict[party_name.strip()]

with open("districts_coalitions.json", "w") as out:
  json.dump(state_districts, out)