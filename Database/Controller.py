from Database.Sqlite import Sqlite


class Controller:
    def __init__(self, db_type):
        self.dbType = db_type
        self.db = None
        if self.dbType == "sqlite":
            self.db = Sqlite()

    def add_raw_search_result(self, internal_id, group=None, query=None, header_json=None, document_html=None):
        if self.dbType == "sqlite":
            self.db.add_raw_search_result(internal_id, group=group, query=query, header_json=header_json,
                                          document_html=document_html)

    def get_raw_search_results(self):
        if self.dbType == "sqlite":
            return self.db.get_raw_search_results()

    def get_unparsed_documents_html(self):
        if self.dbType == "sqlite":
            return self.db.get_unparsed_documents_html()

    def save_standards_number(self, id_, prefix=None, number=None, year=None):
        if self.dbType == "sqlite":
            self.db.save_standards_number(id_, prefix=prefix, number=number, year=year)

    def get_headers(self):
        if self.dbType == "sqlite":
            return self.db.get_headers()

    def execute(self, sql, *args):
        if self.dbType == "sqlite":
            self.db.execute(sql, args)

    def commit(self):
        if self.dbType == "sqlite":
            self.db.commit()

    def get(self):
        if self.dbType == "sqlite":
            return self.db.get()
