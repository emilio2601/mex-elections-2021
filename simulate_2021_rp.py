from enum import auto
import json
import math
import requests
import threading
from tabulate import tabulate
from collections import defaultdict
from dotted_dict import DottedDict

state_districts = json.load(open("districts_coalitions.json"))
political_parties = ["PRI", "PAN", "PRD", "PVEM", "MC", "PT", "MORENA", "PES", "RSP", "FXM"]
political_party_ids = {1: "PAN", 2: "PRI", 3: "PRD", 4: "PVEM", 5: "PT", 6: "MC", 8: "MORENA", 9: "PES", 10: "RSP", 11: "FXM"}

total_party_votes = defaultdict(int)

def download_state_data(state_id):
  url = f"https://prep2021.milenio.com/diputaciones/nacional/assets/data1/circunscripcion/entidad/entidad{state_id}.json"

  r = requests.get(url)
  j = json.loads(r.content)
  
  for name, distrito in j['distritos'].items():
    distrito.pop("secciones")
  
  fp = open(f'district_data/{state_id}.json', 'w')
  json.dump(j, fp)

def open_state_data(state_id):
  return DottedDict(json.load(open(f"district_data/{state_id}.json")))

url = "https://prep2021.milenio.com/diputaciones/nacional/assets/data1/diputacionesNacional.json"
r = requests.get(url)
j = json.loads(r.content)
data = DottedDict(j)

for party in data.votosPartidosPoliticos.votos:
  if party.partido != "50":
    total_party_votes[political_party_ids[int(party.partido)]] += int(party.votos.replace(",", ""))

candidate_distribution = []
elegibility_threshold = 0.03
total_votes = sum(total_party_votes.values())
elegibility_threshold_votes = 0.03 * total_votes

total_nat_votes = sum([v if v > elegibility_threshold_votes else 0 for p, v in total_party_votes.items()])
seats_to_split = 200
votes_for_seat = total_nat_votes / seats_to_split

auto_total_seats = 0

for party, votes in total_party_votes.items():
  raw_pct   = (votes / total_nat_votes)
  raw_ratio = raw_pct * seats_to_split

  if votes > elegibility_threshold_votes:
    auto_seats = math.floor(raw_ratio)
    auto_total_seats += auto_seats
    remaining_votes = votes - (auto_seats * votes_for_seat)
    candidate_distribution.append([party, f"{votes:,}", f"{(votes/total_votes):.2%}", auto_seats, f"{int(remaining_votes):,}"])
  else:
    candidate_distribution.append([party, f"{votes:,}", f"{(votes/total_votes):.2%}", "0", "0"])

all_remaining_votes = sorted([int(p[4].replace(",", "")) for p in candidate_distribution])
remaining_seats = seats_to_split - auto_total_seats
parties_elegible_for_seats = all_remaining_votes[-remaining_seats:]

for p in candidate_distribution:
  if int(p[4].replace(",", "")) in parties_elegible_for_seats:
    p.append("1")
    p.append(f"{int(p[3])+1}")
  else:
    p.append("-")
    p.append(p[3])

print("\n\n\n")
print(f"RP auto assigned {auto_total_seats} seats")
print(f"Would need {int(votes_for_seat):,} votes for 1 seat")
print()
print(tabulate(candidate_distribution, headers=["Party", "Votes", "Pct", "Auto Seats", "Remaining Votes", "Remainder Seats", "Total RP Seats"]))

#####################

mr_winner_parties = defaultdict(int)
mr_check = 0

jobs = []

for state_id in range(1, 33):
  thread = threading.Thread(target=download_state_data, args=(state_id,))
  jobs.append(thread)

for j in jobs:
  j.start()

for j in jobs:
  j.join()
  print(".", end="", flush=True)

for state in state_districts:
  state = DottedDict(state)
  state_data = open_state_data(state.idEstado)

  for district in state_data.distritos.values():
    mr_check += 1
    winner = sorted(district.votosCandidatura.votos, key=lambda p: int(p.votos.replace(",", "")))[-1]
    winner_party_id = int(winner.partido)

    db_district = sorted(state.distritos, key=lambda d: 1 if d.idDistrito == district.distrito else 0)[-1]

    if winner_party_id in political_party_ids.keys():
      mr_winner_parties[political_party_ids[winner_party_id]] += 1
    elif winner_party_id == 20 and "vxm_party_id" in db_district:
      mr_winner_parties[political_party_ids[db_district.vxm_party_id]] += 1
    elif winner_party_id == 30 and "jhh_party_id" in db_district:
      mr_winner_parties[political_party_ids[db_district.jhh_party_id]] += 1   
    else:
      raise Exception("winner is in coalition but not in our db")

for party in political_parties:
  mr_winner_parties[party]

results = []
total_chamber_seats = 500
ct_party_limit = 300
chamber_seats = 0

for party, mr_seats in mr_winner_parties.items():
  rp_data = sorted(candidate_distribution, key=lambda p: 1 if p[0] == party else 0)[-1]

  rp_seats = int(rp_data[-1])
  total_seats = mr_seats + rp_seats
  chamber_seats += total_seats
  
  party_nv = float(rp_data[2].strip("%")) / 100
  party_ovrp_limit = party_nv + 0.08
  party_ovrp_limit_seats = party_ovrp_limit * 500
  party_eff_rep = total_seats / total_chamber_seats
  party_ovrp_by = math.ceil(total_seats - party_ovrp_limit_seats) if math.ceil(total_seats - party_ovrp_limit_seats) > 0 else 0
  party_ovrp = party_ovrp_by != 0
  over_ct_limit = total_seats > ct_party_limit

  results.append([party, mr_seats, rp_seats, total_seats, over_ct_limit, party_ovrp])

results.sort(key=lambda p: -p[3])

if chamber_seats != total_chamber_seats:
  raise Exception(f"seats unallocated! have {chamber_seats}/{total_chamber_seats}")

print("\n")
print(tabulate(results, headers=["Party", "MR Seats", "RP Seats", "Total Seats", "Over 300?", "Ovrp?"]))

coalitions = {
  "Juntos Haremos Historia": ["MORENA", "PVEM", "PT"],
  "Va x Mexico": ["PRI", "PAN", "PRD"],
  "MC": ["MC"],
}

coalition_results = []
total_coalition_chamber_seats = 0

for coalition_name, coalition_parties in coalitions.items():
  mr_coalition_seats = 0
  rp_coalition_seats = 0

  for party in coalition_parties:
    joint_data = sorted(results, key=lambda p: 1 if p[0] == party else 0)[-1]
    mr_coalition_seats += joint_data[1]
    rp_coalition_seats += joint_data[2]
  
  total_coalition_seats = mr_coalition_seats + rp_coalition_seats
  total_coalition_chamber_seats += total_coalition_seats

  coalition_pct = total_coalition_seats / total_chamber_seats
  simple_maj    = coalition_pct > 0.50
  qualifed_maj  = coalition_pct > 0.66

  coalition_results.append([coalition_name, mr_coalition_seats, rp_coalition_seats, total_coalition_seats, f"{coalition_pct:.2%}", simple_maj, qualifed_maj])

if total_coalition_chamber_seats != total_chamber_seats:
  raise Exception(f"seats unallocated! have {total_coalition_chamber_seats}/{total_chamber_seats}")

print("\n")
print(tabulate(coalition_results, headers=["Coalition", "MR Seats", "RP Seats", "Total Seats", "Percentage", "Simple Maj?", "Qualified Maj?"]))