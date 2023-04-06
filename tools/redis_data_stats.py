import pandas
import json

def main():
    redis_backup_filepath = 'temp_data_files/redis_backup.json'
    # data_df = pandas.read_json(redis_backup_filepath, orient='index')
    # data_df = pandas.read_json(redis_backup_filepath)
    # print(data_df)

    records = []

    with open(redis_backup_filepath, 'r') as f:
        data = json.load(f)
        for key in data.keys():
            key_prefix = ':'.join(key.split(':')[0:2])
            records.append({
                'key_prefix': key_prefix,
                'count': 1
            })
            
    data_df = pandas.DataFrame(records)
    grouped_df = data_df.groupby('key_prefix').sum().reset_index()
    grouped_df = grouped_df.sort_values('count', ascending=False).reset_index()
    print(grouped_df)


if __name__ == '__main__':
    main()