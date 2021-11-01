import sqlite3


class Sqlite:
    def __init__(self):
        self.connection = sqlite3.connect("database.db", timeout=30.0, check_same_thread=False)
        self.connection.text_factory = lambda b: b.decode(errors='ignore')
        self.cursor = self.connection.cursor()


    def add_raw_search_result(self, internal_id, group=None, query=None, header_json=None, document_html=None):
        self.cursor.execute('''select * from raw_search_results where internal_id = ? and "group" = ?''', (internal_id, group))
        if len(list(self.cursor.fetchall())) > 0:
            if header_json is not None:
                self.cursor.execute('''UPDATE raw_search_results set header_json = ? where internal_id = ?''',
                                    (header_json, internal_id))
            if document_html is not None:
                self.cursor.execute('''UPDATE raw_search_results set document_html = ? where internal_id = ?''',
                                    (document_html, internal_id))
        else:
            self.cursor.execute('''insert into raw_search_results values (?, ?, ?, ?, ?, ?, ?)''',
                                (None, internal_id, group, query, header_json, None, document_html))
        self.connection.commit()

    def get_raw_search_results(self):
        self.cursor.execute('''SELECT * from raw_search_results''')
        return self.cursor.fetchall()

    def get_unparsed_documents_html(self):
        self.cursor.execute('''SELECT * FROM raw_search_results WHERE document_html is NULL''')
        return self.cursor.fetchall()

    def save_standards_number(self, id_, prefix=None, number=None, year=None):
        self.cursor.execute('''INSERT INTO parsed_standards (id, prefix, number, year) VALUES (?, ?, ?, ?) ''',
                            (id_, prefix, number, year))
        self.connection.commit()

    def get_headers(self):
        self.cursor.execute('''SELECT id, header_json FROM raw_search_results''')
        return self.cursor.fetchall()

    def execute(self, sql, args):
        if len(args) > 0:
            self.cursor.execute(sql, args[0])
        else:
            self.cursor.execute(sql)

    def commit(self):
        self.connection.commit()

    def get(self):
        return self.cursor.fetchall()

