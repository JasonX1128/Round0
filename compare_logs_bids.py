import json, pandas as pd, io
def get_series(fp):
    d = json.load(open(fp))
    df = pd.read_csv(io.StringIO(d['activitiesLog']), sep=';')
    return df[df['product']=='TOMATOES']['bid_price_1'].reset_index(drop=True), df[df['product']=='TOMATOES']['ask_price_1'].reset_index(drop=True)

b1, a1 = get_series('results/round0/23792.log')
b2, a2 = get_series('results/round0/23878.log')
b3, a3 = get_series('results/round0/23904.log')
print("b1==b2:", b1.equals(b2))
print("a1==a2:", a1.equals(a2))
