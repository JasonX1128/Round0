import json, pandas as pd, io
def get_mid_series(fp):
    d = json.load(open(fp))
    df = pd.read_csv(io.StringIO(d['activitiesLog']), sep=';')
    return df[df['product']=='TOMATOES']['mid_price'].reset_index(drop=True)

s1 = get_mid_series('results/round0/23792.log')
s2 = get_mid_series('results/round0/23878.log')
s3 = get_mid_series('results/round0/23904.log')
print("1 vs 2:", s1.equals(s2))
print("2 vs 3:", s2.equals(s3))
