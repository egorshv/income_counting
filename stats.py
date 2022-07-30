from db import DbDispatcher
from datetime import datetime
import matplotlib.pyplot as plt

data = DbDispatcher('data.db')


def get_stat(time, tag):
    tag_id = data.select_data({'name': tag}, 'tags', ['id'])[0][0]
    all_data_by_tag = data.select_data({'tag_id': tag_id}, 'records', ['date', 'sum', 'description'])
    d = {'день': 1, 'неделя': 7, 'месяц': 31, 'год': 365}
    n = d[time]
    now = datetime.now()
    result = []
    for item in all_data_by_tag:
        time_data = item[0].split('.')[0]
        time_data = datetime.strptime(time_data, '%Y-%m-%d %H:%M:%S')
        diff = now - time_data
        if diff.days < n:
            result.append(item)
    return result, sum([item[1] for item in result])


def get_plot(filename, time, income):
    labels = data.select_data({}, 'tags', ['id', 'name', 'income'])
    _labels = list(filter(lambda x: x[2] == income, labels))
    lbs = []
    for lb in _labels:
        records = data.select_data({'tag_id': lb[0]}, 'records')
        if len(records) > 0:
           lbs.append(lb)
    names = [item[1] for item in lbs]
    _data = []
    for label in names:
        s = get_stat(time, label)
        _data.append(s[1])
    plt.pie(_data, labels=names)
    plt.savefig(filename)


# get_plot('plot1.png', 'день', 0)
# print(get_stats('день', 'some name'))
