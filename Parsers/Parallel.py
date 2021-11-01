from Parsers.SiteParser import SiteParser
from Database.Controller import Controller
import threading

class ParallelController:
    def __init__(self, dbtype):
        self.dbtype = dbtype

    def fill_documents_html(self):
        db = Controller(self.dbtype)
        threads = []
        db.execute('''SELECT DISTINCT "group" from raw_search_results''')
        groups = [x[0] for x in db.get()]
        for group in groups:
            db.execute('''SELECT DISTINCT internal_id from raw_search_results where "group" = ? and document_html is null''', (group, ))
            internal_ids = [x[0] for x in db.get()]
            db_ = Controller(self.dbtype)
            parser = SiteParser(db_)
            thread = threading.Thread(target=parser.fill_documents_html, kwargs={
                "internal_ids": internal_ids,
            })
            threads.append(thread)
            thread.start()
            print("Thread for group", group, "started", "Len:", len(internal_ids))



