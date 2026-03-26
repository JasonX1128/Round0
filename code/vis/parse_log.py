import json
with open('outputs/local_sim.log', 'r') as f:
    data = json.load(f)
print(type(data['activitiesLog']))
print("Length of activities", len(data['activitiesLog']))
if 'tradeHistory' in data:
    print(type(data['tradeHistory']), len(data['tradeHistory']))
print("First bit of tradeHistory:", str(data.get('tradeHistory', ''))[:200])
