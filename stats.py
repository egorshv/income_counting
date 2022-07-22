from db import DbDispatcher
from datetime import datetime

data = DbDispatcher('data.db')


def get_stats(time, tag):
    tag_id = data.select_data({'name': tag}, 'tags', ['id'])[0][0]
    all_data_by_tag = data.select_data({'tag_id': tag_id}, 'records', ['date', 'sum'])
    d = {'день': 2, 'неделя': 2, 'месяц': 1, 'год': 0}
    k = d[time]
    n = 1
    now = str(datetime.now()).split('-')
    now[2] = now[2].split()[0]
    now = now[k]
    if time == 'неделя':
        n = 7
    result = []
    for item in all_data_by_tag:
        time_data = item[0].split('-')
        time_data[2] = time_data[2].split()[0]
        time_data = time_data[k]
        if int(now) - int(time_data) <= n:
            result.append(item)
    return result, sum([item[1] for item in result])



# print(get_stats('день', 'some name'))
