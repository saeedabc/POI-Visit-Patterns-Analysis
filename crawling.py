import os.path

import pandas as pd
import urllib.request
import json
from pathlib import Path
from collections import OrderedDict
from pprint import pprint


base_path = 'data'


def crawl_census_profile_data_for_cbgs_of_interest():
    sg_df = pd.read_csv(os.path.join(base_path, 'SafeGraph', 'weekly-patterns.csv'))

    census_dir = os.path.join(base_path, 'CensusProfile')
    Path(census_dir).mkdir(parents=True, exist_ok=True)

    visited_cbgs = set(fn.split('.')[0] for fn in os.listdir(census_dir))

    for i, row in enumerate(sg_df['visitor_home_cbgs']):
        for cbg in eval(row).keys():
            try:
                da = cbg.split(':')[1]
            except (IndexError, ) as e:  # CBG is in US
                print(f"\tError: #{i}: cbg={cbg} | {e}")
                continue

            dguid = f'2016S0512{da}'

            if dguid not in visited_cbgs:
                url = f"https://www12.statcan.gc.ca/rest/census-recensement/CPR2016.json?lang=E&dguid={dguid}&topic=0&notes=0&stat=0"
                try:
                    dic = json.loads(urllib.request.urlopen(url).read())
                except json.decoder.JSONDecodeError as e:  # API returned no data
                    print(f"\tError: #{i}: cbg={cbg} | {e}")
                    continue

                cbg_df = pd.DataFrame(data=dic['DATA'], columns=dic['COLUMNS'])
                tbw_path = os.path.join(census_dir, f'{dguid}.csv')
                cbg_df.to_csv(tbw_path)

                visited_cbgs.add(dguid)
                print(f"#row({i+1}/{len(sg_df)}), poi_id={sg_df.iloc[i]['safegraph_place_id']}: cbg={cbg} (#{len(visited_cbgs)})")


def combine_cbgs_census_data_into_a_single_dataframe():
    def get_prop(df, topic_theme, hier_ids):
        df = df[df['TOPIC_THEME'] == topic_theme]
        if type(hier_ids) is str:
            hier_id = hier_ids
            # print(hier_id, df[df['HIER_ID'] == hier_id]['T_DATA_DONNEE'], df[df['HIER_ID'] == hier_id]['T_DATA_DONNEE'].values)
            return df[df['HIER_ID'] == hier_id]['T_DATA_DONNEE'].values[0]
        else:  # type(hier_ids) is list
            # print(type(df[df['HIER_ID'] == hier_ids[0]]['T_DATA_DONNEE']), df[df['HIER_ID'] == hier_ids[0]]['T_DATA_DONNEE'])
            return sum(df[df['HIER_ID'] == hier_id]['T_DATA_DONNEE'].values[0] for hier_id in hier_ids)

    def extract_props_of_interest(df):
        d = OrderedDict()

        d['geo_uid'] = df['GEO_UID'][0]
        d['geo_id'] = df['GEO_ID'][0]

        d['population'] = get_prop(df, 'Population', '1.1.1')  # 'Population, 2016'
        d['land_area'] = get_prop(df, 'Population', '1.1.7')  # 'Land area in square kilometres'
        d['pop_density'] = get_prop(df, 'Population', '1.1.6')  # 'Population density per square kilometre'
        d['pop_0_14'] = get_prop(df, 'Population', '1.2.1.1')  # '  0 to 14 years'
        d['pop_15_64'] = get_prop(df, 'Population', '1.2.1.1')  # '  15 to 64 years'
        d['pop_65'] = get_prop(df, 'Population', '1.2.1.1')  # '  65 years and over'
        d['pop_avg_age'] = get_prop(df, 'Population', '1.2.3')  # 'Average age of the population'
        d['pop_med_age'] = get_prop(df, 'Population', '1.2.4')  # 'Median age of the population'
        d['pop_married'] = get_prop(df, 'Families, households and marital status', '2.2.1.1')  # '  Married or living common law'
        d['pop_not_married'] = get_prop(df, 'Families, households and marital status', '2.2.1.2')  # '  Not married and not living common law'

        d['income_0_30'] = get_prop(df, 'Income', ['4.1.5.3.1', '4.1.5.3.2', '4.1.5.3.3'])
        d['income_30_70'] = get_prop(df, 'Income', ['4.1.5.3.4', '4.1.5.3.5', '4.1.5.3.6', '4.1.5.3.7'])
        d['income_70_100'] = get_prop(df, 'Income', ['4.1.5.3.8', '4.1.5.3.9', '4.1.5.3.10'])
        d['income_100'] = get_prop(df, 'Income', '4.1.5.3.11')
        d['income_emp_avg'] = get_prop(df, 'Income', '4.1.3.1.2')  # Average employment income in 2015 for full-year full-time workers ($)
        d['income_emp_med'] = get_prop(df, 'Income', '4.1.3.1.1')  # Median employment income in 2015 for full-year full-time workers ($)

        d['orig_north_american'] = get_prop(df, 'Ethnic origin', ['8.1.1.1', '8.1.1.2'])
        d['orig_european'] = get_prop(df, 'Ethnic origin', '8.1.1.3')
        d['orig_caribbean'] = get_prop(df, 'Ethnic origin', '8.1.1.4')
        d['orig_latin'] = get_prop(df, 'Ethnic origin', '8.1.1.5')
        d['orig_african'] = get_prop(df, 'Ethnic origin', '8.1.1.6')
        d['orig_asian'] = get_prop(df, 'Ethnic origin', '8.1.1.7')
        d['orig_oceania'] = get_prop(df, 'Ethnic origin', '8.1.1.8')

        d['edu_no_degree'] = get_prop(df, 'Education', '10.1.1.1')
        d['edu_diploma'] = get_prop(df, 'Education', '10.1.1.2')
        d['edu_post_secondary'] = get_prop(df, 'Education', '10.1.1.3')

        d['employment_rate'] = get_prop(df, 'Labour', '11.1.3')
        d['unemployment_rate'] = get_prop(df, 'Labour', '11.1.4')

        return d

    cp_dir = os.path.join(base_path, 'CensusProfile')
    cbgs_uids = os.listdir(cp_dir)
    cbgs_data = []
    for fname in cbgs_uids:
        df = pd.read_csv(os.path.join(cp_dir, fname))
        dic = extract_props_of_interest(df)
        cbgs_data.append(dic)

        print(f'#{len(cbgs_data)}/{len(cbgs_uids)}: cbg(geo_uid={fname}) data extracted')

    cbgs_df = pd.DataFrame(cbgs_data)
    cbgs_df.to_csv(os.path.join(cp_dir, 'cbgs-census.csv'))


if __name__ == '__main__':
    # crawl_census_profile_data_for_cbgs_of_interest()
    combine_cbgs_census_data_into_a_single_dataframe()