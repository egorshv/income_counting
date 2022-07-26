import sqlite3


class DbDispatcher:
    def __init__(self, filename):
        self.filename = filename
        self.con = sqlite3.connect(filename)
        self.cur = self.con.cursor()

    def write_data(self, d: dict, table: str):
        # d: key - столбец, value - значение
        lst2 = []
        for i in d.values():
            lst2.append(f'\'{i}\'')
        s1 = ', '.join(d.keys())
        s2 = ', '.join(lst2)
        assert len(d.keys()) == len(d.values())
        q = f"""INSERT INTO {table} ({s1}) VALUES ({s2})"""
        self.cur.execute(q)
        self.con.commit()

    def update_data(self, d: dict, params: dict, table: str):
        lst = []
        for k, v in d.items():
            lst.append(f"{k} = '{v}'")
        s = ', '.join(lst)
        arr = list(map(lambda x: f"{x[0]} = '{x[1]}'", params.items()))
        s2 = ' AND '.join(arr)
        q = f"""UPDATE {table} SET {s} WHERE {s2}"""
        self.cur.execute(q)
        self.con.commit()

    def read_all_data(self, table: str):
        q = f"""SELECT * FROM {table}"""
        return self.cur.execute(q).fetchall()

    def select_data(self, d: dict, table: str, columns=None):
        # d - параметры поиска
        # table - таблица, в которой надо искать
        # columns - столбцы, которые надо вывести
        lst = []
        for item in d.items():
            try:
                lst.append(f'{item[0]}={int(item[1])}')
            except ValueError:
                lst.append(f"{item[0]}='{item[1]}'")
        s = ' AND '.join(lst)
        if columns:
            col = ', '.join(columns)
        else:
            col = '*'
        if s:
            q = f"""SELECT {col} FROM {table} WHERE {s}"""
        else:
            q = f"""SELECT {col} FROM {table}"""
        return self.cur.execute(q).fetchall()

    def get_max_id(self, table):
        q = f"""SELECT MAX(id) FROM {table}"""
        return self.cur.execute(q).fetchone()

    def delete_data(self, table):
        q = f"""DELETE from {table}"""
        self.cur.execute(q)
        self.con.commit()

    def close_connection(self):
        self.con.close()
