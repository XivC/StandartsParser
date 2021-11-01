import time
from pprint import pprint

import document as document
import requests
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class SiteParser:
    def __init__(self, controller):
        self.db = controller

    def parse_raw_search_headers_to_db(self, group, queries):
        i = 0
        while i < len(queries):
                query = queries[i]
                try:
                    response = requests.get(" https://docs.cntd.ru/api/search/intellectual/documents", params={"q": query},
                                            verify=False)
                    if response.status_code != 200:
                        print(response.text, response.status_code)
                    data = json.loads(response.text)
                    try:
                        total = int(data["documents"]["pagination"]["total"])
                        pages = int(data["documents"]["pagination"]["last_page"])
                    except:
                        total = 0
                        pages = 0
                        pprint(data)
                    if total == 0:
                        i += 1
                        continue

                    page = 1
                    while page <= pages:
                        try:
                            response = requests.get(" https://docs.cntd.ru/api/search/intellectual/documents", params={"q": query,
                                                                                                                       "page": page},
                                                    verify=False)
                            if response.status_code != 200:
                                print(response.text, response.status_code)

                            data = json.loads(response.text)
                            for result in data["documents"]["data"]:
                                internal_id = int(result["id"])
                                header_json = json.dumps(result)
                                self.db.execute('''INSERT OR IGNORE INTO raw_search_results (internal_id, "group", query, header_json) VALUES (?, ?, ?, ?)''', (internal_id, group, query, header_json,))
                                self.db.commit()
                            page += 1
                        except requests.exceptions.ConnectionError:
                            print("timeout error")
                            time.sleep(10)
                    i += 1
                except requests.exceptions.ConnectionError:
                    print("timeout error")
                    time.sleep(10)

    def fill_documents_html(self, internal_ids=None):
        parsed = []
        if internal_ids is None:
            return
            #internal_ids = [x[1] for x in self.db.get_unparsed_documents_html()]
        #print(internal_ids)
        for internal_id in internal_ids:
            try:
                response = requests.get(f"https://docs.cntd.ru/document/{internal_id}".format(
                    internal_id=str(internal_id)), verify=False)
                if response.status_code != 200:
                    print(response.text)
                    continue
                self.db.execute('''UPDATE raw_search_results set document_html=? where internal_id=?''',
                                (response.text, internal_id,))
                self.db.commit()



                print("id:", internal_id, "parsed", "\n")
            except requests.exceptions.ConnectionError:
                print("timeout error")
                time.sleep(10)



    def fill_api_headers(self):

        self.db.execute('''SELECT DISTINCT internal_id from raw_search_results where api_header is null''')
        internal_ids = [x[0] for x in self.db.get()]
        for internal_id in internal_ids:
            try:
                response = requests.get(f"https://docs.cntd.ru/api/document/{internal_id}".format(
                    internal_id=str(internal_id)), verify=False)
                if response.status_code != 200:
                    print(response.text)
                    continue
                data = json.loads(response.text)

                self.db.execute('''UPDATE raw_search_results SET api_header = ? where internal_id = ?''', (json.dumps(data), internal_id))
                self.db.commit()

            except requests.exceptions.ConnectionError:
                print("timeout error")
                time.sleep(10)





