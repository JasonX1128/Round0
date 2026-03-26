import json, pandas as pd, io
def get_mid_series_log(fp):
    d = json.load(open(fp))
    df = pd.read_csv(io.StringIO(d['activitiesLog']), sep=';')
    return df[df['product']=='TOMATOES']['mid_price'].reset_index(drop=True)

s1 = get_mid_series_log('results/round0/23792.log')

df_tut = pd.read_csv('TUTORIAL_ROUND_1/prices_round_0_day_-1.csv', sep=';')
s_tut = df_tut[df_tut['product']=='TOMATOES']['mid_price'].reset_index(drop=True)

print("Log vs Tut:", s1.equals(s_tut))
