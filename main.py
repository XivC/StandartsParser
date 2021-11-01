from Parsers.SiteParser import SiteParser
from Database.Controller import Controller
from Parsers.RawParser import RawParser
from Parsers.RawParser import find_substring_intersect
from Utils.Utils import Utils
from Parsers.Parallel import ParallelController
from Output.TestOutput import TestOutput
from Parsers.RawParser import split_by_sentences
controller = Controller("sqlite")
parser = RawParser(controller)
parser_site = SiteParser(controller)

#parser.parse_queries2()
#print(Utils.read_queries_and_groups("queries/", 14))
 #for group in range(3, 15):
 #   parser_site.parse_raw_search_headers_to_db(group, open("queries_{}.txt".format(group), "r", encoding="utf-8").read().split(","))
 #   print("Group", group, "parsed")

#parser_site.fill_documents_html()
#parser_site.fill_api_headers()
#parser.parse_standards_from_names()
#parser.parse_queries(search_unfound=True)
#parser.parse_standard_classes()
#parser.parse_status()
#parser.parse_exploitation_type_general()
#parser.parse_special_conditions_light()
#parser.parse_standard_groups_by_segment()
#parser.parse_products_using_leds()
#parser.parsed_standards_class_and_segment()

#parser.parse_point_standard_type()
#parser.parse_special_rows()

#parallel = ParallelController("sqlite")
#parallel.fill_documents_html()
#parser_site.fill_api_headers()
#parser.parse_description()
#parser.parse_is_latin()
TestOutput.dump_db("out.xlsx", "Стандарты таблица 31.10.21 + столбец англ.xlsx")
#parser.prefix_correction()
