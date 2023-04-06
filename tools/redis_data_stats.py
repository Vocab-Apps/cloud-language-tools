import sys
import os
import inspect
import pandas
import json
import cloudlanguagetools.constants

pandas.set_option('display.max_rows', 500)

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 

import redisdb

def main():
    redis_backup_filepath = 'temp_data_files/redis_backup.json'
    # data_df = pandas.read_json(redis_backup_filepath, orient='index')
    # data_df = pandas.read_json(redis_backup_filepath)
    # print(data_df)

    records = []

    with open(redis_backup_filepath, 'r') as f:
        data = json.load(f)
        for key in data.keys():
            key_components = key.split(':')
            if key_components[1] in ['api_key', 'trial_user', 'getcheddar_user', 'patreon_user']:
                key_prefix = ':'.join(key_components[0:2])
            elif key_components[1] == 'usage' and key_components[3] not in ['lifetime', 'recurring']:
                key_prefix = ':'.join(key_components[0:5])
            else:
                key_prefix = ':'.join(key_components[0:3])
            date_int = 0
            # if key_components[1] == redisdb.KEY_TYPE_USAGE:
            #     if key_components[2] in [cloudlanguagetools.constants.UsageScope.User.key_str, cloudlanguagetools.constants.UsageScope.Global.key_str]:
            #         date_str = key_components[4]
            #         try:
            #             date_int = int(date_str)
            #         except:
            #             print(f'exception when trying to parse: {key}')
            #         # print(f'date_str: {date_str}')
            records.append({
                'key_prefix': key_prefix,
                'date_int': date_int,
                'count': 1
            })
            
    data_df = pandas.DataFrame(records)
    grouped_df = data_df.groupby('key_prefix').agg({'count': 'sum', 'date_int': 'min'}).reset_index()
    grouped_df = grouped_df.sort_values('count', ascending=False).reset_index()
    print(grouped_df)


if __name__ == '__main__':
    main()