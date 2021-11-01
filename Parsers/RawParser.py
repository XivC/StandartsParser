import json
import re

import bs4
from bs4 import BeautifulSoup as bs
from pprint import pprint
import pymorphy2
from Utils.Utils import Utils
from datetime import datetime


def get_strings_from_document_header(document):
    soup = bs(document, features="html.parser")
    strings = [x for x in soup.find_all('p', {"class": "headertext topleveltext centertext"},
                                        id=lambda x: re.match('P[0-9]{3,}', str(x)) is not None,
                                        align="center")]
    strs = []
    for s in strings:
        strs += [x if isinstance(x, bs4.NavigableString) else x.get_text() for x in list(s.children)]
    strs = [x.replace("<br>", "\n").replace("<br/>", "\n").replace("</br>", "\n") for x in strs]
    return strs


def split_by_sentences(string):
    split = []
    dot_flag = False
    sentence = ""
    for i in range(len(string)):
        char = string[i]
        if dot_flag:

            if char in " ":
                sentence += char
                continue
            dot_flag = False
            if (char.upper() in char) and (not char.isdigit()):
                split.append(sentence)
                sentence = char
                continue
            split.append(sentence)
            sentence = ""
        if char in ".?!":
            dot_flag = True
        else:
            sentence += char
    split.append(sentence)
    return split


def is_russian_sentence(sentence):
    alphabet = "абвгдеёжзиклмнопрстуфхцчшщъыьэюя"
    for char in sentence:
        if char.lower() in alphabet:
            return True
    return False


def is_sublist(lst, sublist):
    return len([x for x in sublist if x in lst]) == len(sublist)


def find_substring_intersect(string, substring):
    string_lst = string.lower().strip().split()
    substring_lst = substring.lower().strip().split()
    for testing_word in substring_lst:
        flag = False
        for word in string_lst:
            if testing_word in word:
                flag = True
                break
        if not flag:
            return False
    return True






class RawParser:
    def __init__(self, controller):
        self.db = controller
        self.standards_reg = r'(СТО|ОДМ|МУ|ГОСТ|ГОСТ Р|ГОСТ EN|Cispr|СИСПР|СТБ|СТ РК|ИСО|МЭК|ISO|IEC|ИСО|ТУ|СТ СЭВ|UNE-EN|ULC|CAN|Правила ЕЭК ООН|СанПиН|СНиП|ПНСТ|ОСН-АПК|DIN|UNI) ([0-9]{1,8}(?:(?:\.|-|_|:|,)(?:(?:(?:[0-9])|(?:[0-6][0-9]{1,2}))(?=(?:\.|-|:|,|_|\s|$))))*)((?:\.|-|_|:|,)(?:(?:20[0-3][0-3])|(?:19[7-9][0-9])|(?:[8-9][0-9])))?'
        self.standards_reg_without_year = r'(СТО|ОДМ|МУ|ГОСТ|ГОСТ Р|ГОСТ EN|Cispr|СИСПР|СТБ|СТ РК|ИСО|МЭК|ISO|IEC|ИСО|ТУ|СТ СЭВ|UNE-EN|ULC|CAN|Правила ЕЭК ООН|СанПиН|СНиП|ПНСТ|ОСН-АПК|DIN|UNI) ([0-9]{1,8}(?:(?:\.|-|_|:|,)(?:[0-9]{0,5})(?=(?:\.|-|:|,|_|\s|$)))*)'
        self.normalized_queries_cache = {}
        self.normalized_words_cache = {}
        self.morph = pymorphy2.MorphAnalyzer()

    def normalize_list(self, lst):

        for i in range(len(lst)):
            word = lst[i]
            word_norm = self.normalized_words_cache.get(word)
            if word_norm is None:
                word_norm = self.morph.parse(word)[0].normal_form
                self.normalized_words_cache[word] = word_norm
            lst[i] = word_norm
        return lst

    def find_substring_normalized(self, string, substring):

        string = self.normalize_list(string.split())
        substring = self.normalize_list(substring.split())
        return is_sublist(string, substring)

    def parse_standards_from_names(self):
        for id_, header in self.db.get_headers():
            try:
                header = json.loads(header, strict=False)
            except json.decoder.JSONDecodeError:
                continue
            for name in header["names"]:
                search = re.search(self.standards_reg, name)
                if search is not None:
                    groups = [x for x in list(search.groups()) if x is not None]
                    prefix = groups[0]
                    number = groups[1]
                    year = None
                    if len(groups) > 2:
                        year = groups[2]
                        year = year[1:] if not year[0].isdigit() else year
                        year = "19" + year if len(year) == 2 else year

                    self.db.save_standards_number(id_, prefix=prefix, number=number, year=year)
                    break

    # queries_groups - Ключи, по которым будет производится поиск
    # queries_found_in_description - объект, куда записываем новые найденные слова
    # document - документ, по которому производится поиск
    def find_queries_in_text(self, queries_groups, queries_found_in_description, document):
        try:
            soup = bs(document, features="html.parser")
        except TypeError:
            return {}
        strings = [x for x in soup.find_all('p',
                                            id=lambda x: re.match('P[0-9]{3,}', str(x)) is not None,
                                            align="justify")]
        strs = []
        for s in strings:
            buffer = []
            for child in s.children:
                try:
                    buffer.append(child.get_text())
                except AttributeError:
                    buffer.append(str(child))
            strs += buffer
        strings = strs
        strings = [x.replace("\xa0", " ").replace("<br>", "\n").replace("<br/>", "\n").replace("</br>", "\n") for x
                   in
                   strings]
        strings = [x for x in strings if len(x) > 3]
        queries_found_in_text = {}
        for string in strings:
            queries_found_in_text[string] = set()
            for group in queries_groups.keys():
                for query in queries_groups[group]:
                    if self.find_substring_normalized(string.lower(), query.lower()):
                        queries_found_in_text[string].add(query)
                        queries_found_in_description[group].add(query)
        return queries_found_in_text

    def parse_queries2(self):
        n = 0
        groups = Utils.read_queries_and_groups("queries/", 14)
        self.db.execute(
            '''SELECT parsed_standards.id, parsed_standards.description from parsed_standards''')
        id_desc_relation = self.db.get()
        for id_, description in id_desc_relation:
            n += 1
            if n < 14460:
                continue
            groups_temp = {}
            for group in groups:
                groups_temp[group] = [x for x in groups[group]]
            queries_found = {}
            for group in groups.keys():
                queries_found[group] = set()

            self.db.execute('''SELECT "group", query from raw_search_results
             where internal_id in ( SELECT internal_id from raw_search_results where id = ?)''', (id_,))
            for group, query in self.db.get():
                queries_found[group].add(query)

            for group in groups.keys():
                for query in groups[group]:
                    if self.find_substring_normalized(description.lower(), query.lower()):
                        queries_found[group].add(query)
            for group in groups.keys():
                if len(queries_found[group]) == 0:
                    groups_temp[group] = []
                else:
                    for query in queries_found[group]:
                        try:
                            groups_temp[group].remove(query)
                        except ValueError:
                            continue

            self.db.execute('''SELECT document_html from raw_search_results where id = ?''', (id_,))
            document = self.db.get()[0][0]

            queries_found_in_text = self.find_queries_in_text(groups_temp, queries_found, document)
            # ------Подготовка к записи и запись
            groups_found = set()
            for group in groups.keys():
                if len(queries_found[group]) > 0:
                    groups_found.add(group)
                else:
                    queries_found.pop(group)
            _ = [x for x in queries_found_in_text.keys()]
            for string in _:
                if len(queries_found_in_text[string]) == 0:
                    queries_found_in_text.pop(string)
            queries_found_in_text_string = ""
            queries_found_string = ""
            groups_found_string = ", ".join([str(x) for x in groups_found])
            for string in queries_found_in_text:
                queries_found_in_text_string += f"{queries_found_in_text[string]}\n{string}\n\n"
            for group in queries_found:
                for query in queries_found[group]:
                    queries_found_string += query + ", "
            queries_found_string = queries_found_string[::-1][2:][::-1]
            print(n)
            # print(queries_found_string, queries_found_in_text_string, groups_found_string)

            self.db.execute('''UPDATE parsed_standards set queries = ?, queries_groups = ?, queries_in_text = ? 
            where id = ?'''
                            , (queries_found_string,
                               groups_found_string,
                               queries_found_in_text_string,
                               id_
                               ))
            self.db.commit()

    def parsed_standards_class_and_segment(self):
        self.db.execute(
            '''SELECT parsed_standards.id, 
             parsed_standards.description from parsed_standards
              ''')
        n = 0
        for id_, description in self.db.get():
            n += 1
            print(n)
            description_shorted = ""
            shorting_flag = False
            for i in range(len(description) - 2):
                if description[i].isupper() and description[i+1].islower() and description[i+2].islower():
                    shorting_flag = True
                if shorting_flag:
                    description_shorted += description[i]
            description_shorted += description[-2] + description[-1]
            #print(description, "\n", "\n", description_shorted, "\n", "--------", "\n")
            description_split = split_by_sentences(description_shorted)
            standard_class = description_split[0]
            try:
                standard_segment = "".join(description_split[1:])
            except:
                standard_segment = None
            self.db.execute('''UPDATE parsed_standards SET 
            standard_class = ?, standard_groups_by_segment = ? where id = ?''',
                            (standard_class if len(standard_class.strip()) > 0 else None,
                             standard_segment if len(standard_segment.strip()) > 0 else None,
                             id_, ))
            self.db.commit()




    def parse_standard_classes(self):
        headers = ["межгосударственный стандарт",
                   "национальный стандарт ",
                   "государственный стандарт",
                   "всесоюзный стандарт",
                   "СТАНДАРТ ОРГАНИЗАЦИИ",
                   "ГОСУДАРСТВЕННЫЙ СТАНДАРТ СОЮЗА ССР",
                   "ОТРАСЛЕВОЙ ДОРОЖНЫЙ МЕТОДИЧЕСКИЙ ДОКУМЕНТ",
                   "САНИТАРНЫЕ ПРАВИЛА И НОРМЫ",
                   "ПОСТАНОВЛЕНИЕ",
                   "ИНФОРМАЦИОННЫЕ ДАННЫЕ",
                   "СВОД ПРАВИЛ"
                   ]
        headers = [x.upper() for x in headers] + [x.lower() for x in headers]
        self.db.execute(
            '''SELECT raw_search_results.id, raw_search_results.document_html,
             parsed_standards.description from raw_search_results,parsed_standards
              where raw_search_results.id = parsed_standards.id''')

        documents = self.db.get()
        for id_, document, description in documents:
            print(split_by_sentences(description))
            soup = bs(document, features="html.parser")

            strings = [x for x in soup.find_all('p', {"class": "headertext topleveltext centertext"},
                                                id=lambda x: re.match('P[0-9]{3,}', str(x)) is not None,
                                                   align="center")]
            strs = []
            for s in strings:
                strs += [str(x) for x in list(s.children)]

            strings = strs

            print(strings)

            strings = [x.replace("\xa0", " ") for x in strings]
            strings = [x.strip() for x in strings if
                       x.replace(" ", "").upper() == x.replace(" ", "") and len(x.replace(" ", "")) > 3]

            for i in range(len(strings)):
                for header in headers:
                    if header in strings[i]:
                        strings[i] = None
                        break
            strings = [x for x in strings if x is not None]
            print(strings)
            class_ = strings[0] if len(strings) > 0 else None
            self.db.execute('''UPDATE parsed_standards SET standard_class = ? WHERE id = ?''', (class_, id_,))
        self.db.commit()

    def parse_status(self):
        self.db.execute('''select id, api_header from raw_search_results where api_header is not null''')
        for id_, api_header in self.db.get():
            try:
                header = json.loads(api_header, strict=False)
            except json.decoder.JSONDecodeError:
                continue
            try:
                status = header["data"]["status"]["name"]
                # print(status)
                if "Действующий" in status:
                    status = 1
                else:
                    status = 0
            except TypeError:
                status = None
                pprint(header["data"])
            self.db.execute('UPDATE parsed_standards set status = ? where id = ?', (status, id_,))
            self.db.commit()

    def parse_exploitation_type_general(self):
        groups = [(1, ['улич', 'улиц', 'дорог', 'трасс', 'завод', 'наружнего примен', 'промышленн обстанов',
                       'промышленн зон', 'промышленности', 'в районах с промышленными', 'промышленного применения',
                       'промышленные применения', 'магнитного поля промышленной частоты',
                       'электрооборудование машин и механизмов', 'на промышленных предприятиях',
                       'в промышленных', 'промышленное', 'промышленные', 'промышленной', 'на промышленных',
                       'промышленных машин', 'промышленного назначения', 'промышленн эксплуатац',
                       'электрическое оборудование для измерения', 'управления и лабораторного применения',
                       'ржд', 'железн', 'дуговой сварки', 'лифт', 'конвейер', 'эскалатор', 'сельского', 'лесного',
                       'промышленных площадках', 'строительн', 'стройках', 'строительств', 'станки', 'станков', 'пресс',
                       'технические средства с потребляемым током не более 75 а',
                       'технические средства с потребляемым током более 16 а', 'поезд', 'подвижной состав', 'вагон',
                       'транспортное средство', 'трансформаторы силовые', 'силовых приводов', 'промышленность',
                       'взрыв', 'рудничное', 'угольные шахты', 'нефте-газов']
                   ), (2, ['коммерческого', ' коммерческих зонах', ' коммерческими', ' общественного', ' общественных',
                           ' ОБОРУДОВАНИЯ ИНФОРМАЦИОННЫХ ТЕХНОЛОГИЙ', ' легк  промыш']),
                  (3, ['общего назначения']),
                  (4, ['бытового или аналогичного'])]

        self.db.execute('''SELECT id, description from parsed_standards''')
        for id_, description in self.db.get():
            for group, keys in groups:
                for key in keys:
                    if find_substring_intersect(description, key):
                        self.db.execute(
                            '''UPDATE parsed_standards SET exploitation_type_general = ? WHERE id = ?''',
                            (group, id_))
                        break
        self.db.commit()

    def parse_special_conditions_light(self):
        groups = [
            (1, [r'взрыв', r'рудничное', r'угольные шахты', r'нефте-газов']),
            (2, [r'медецин']),
            (3, [r'железн', r'ржд']),
            (4, [r'жил помещен']),
            (5, [r'торговли', r'питания']),
            (6, [r'мебел']),
            (7, [r'Чистые помещ', r'чистые зоны']),
            (8, [r'судовое', r'суда', r'судна']),
            (8, [r'атомн']),
            (10, [r'вентиляци', r'вентиляторы промышлен']),
            (11, [r'отоплени', r'водоснабжени']),
            (12, [r'теплиц']),
            (13, [r'ЭЛЕКТРИЧЕСКИХ КОНТРОЛЬНО-ИЗМЕРИТЕЛЬНЫХ ПРИБОРОВ И ЛАБОРАТОРНОГО ОБОРУДОВАНИЯ']),
            (14, [r"автоматические электрические управляющие устройства"]),
            (15, [r'оборудование информационных технологий']),
            (16, [r"IP "]),
            (17, [r'К МЕХАНИЧЕСКИМ ВНЕШНИМ', r'IK ', r'Ударопрочно']),
            (
                18,
                [r'С ВЛИЯНИЕМ НА ЧЕЛОВЕКА ЭЛЕКТРОМАГНИТНЫХ ПОЛЕЙ', r'с воздействием на человека электромагнитных полей',
                 r'воздействия на человека электромагнитных полей',
                 r'электромагнитных полей бытовых приборов и аналогичных аппаратов с учетом их воздействия на человека'
                 ]),
            (19, [r'РАДИОСВЯЗИ', r'радиосвязь']),
            (20, [r'РАДИОВЕЩАТЕЛЬНЫЕ ПРИЕМНИКИ', r'ТЕЛЕВИЗОРЫ', r'ПРИЕМНИКИ ЗВУКОВОГО И ТЕЛЕВИЗИОННОГО ВЕЩАНИЯ']),
            (21, [r'АУДИО-, ВИДЕОАППАРАТУРА']),
            (22, [r'МАШИНЫ ЭЛЕКТРИЧЕСКИЕ ВРАЩАЮЩИЕСЯ']),
            (23, [r'ТРЕБОВАНИЯ К ЗАРЯДНЫМ УСТРОЙСТВАМ БАТАРЕЙ']),
            (24, [
                r'ВЫКЛЮЧАТЕЛИ АВТОМАТИЧЕСКИЕ ДЛЯ ЗАЩИТЫ ОТ СВЕРХТОКОВ ЭЛЕКТРОУСТАНОВОК БЫТОВОГО И АНАЛОГИЧНОГО НАЗНАЧЕНИЯ']),
            (25, [r'АППАРАТУРА РАСПРЕДЕЛЕНИЯ И УПРАВЛЕНИЯ НИЗКОВОЛЬТНАЯ']),
            (26, [r'ВЫКЛЮЧАТЕЛИ ДЛЯ БЫТОВЫХ И АНАЛОГИЧНЫХ СТАЦИОНАРНЫХ ЭЛЕКТРИЧЕСКИХ УСТАНОВОК']),
            (27, [r'СОЕДИНИТЕЛИ ЭЛЕКТРИЧЕСКИЕ ШТЕПСЕЛЬНЫЕ БЫТОВОГО И АНАЛОГИЧНОГО НАЗНАЧЕНИЯ']),

        ]
        self.db.execute(
            '''SELECT id, header_json, document_html from  raw_search_results where id in (SELECT id from parsed_standards) and document_html is not null''')
        for id_, header, document in self.db.get():
            try:
                header = json.loads(header, strict=False)
            except json.decoder.JSONDecodeError:
                continue
            found = False
            for group, keys in groups:
                if found:
                    break
                if group == 1:
                    for key in keys:

                        is_match = find_substring_intersect(document.lower(), key.lower())
                        if is_match:
                            self.db.execute(
                                '''UPDATE parsed_standards SET special_conditions_light = ? WHERE id = ?''',
                                (group, id_))
                            found = True
                            break

                for name in header["names"]:
                    if found:
                        break
                    for key in keys:

                        is_match = find_substring_intersect(name.lower(), key.lower())
                        if is_match:
                            self.db.execute(
                                '''UPDATE parsed_standards SET special_conditions_light = ? WHERE id = ?''',
                                (group, id_))
                            found = True
                            break
        self.db.commit()

    def parse_standard_groups_by_segment(self):
        def logic1():
            for i in range(len(strs)):
                if "частные требования" in strs[i].lower():
                    return True, " ".join(strs[i::])
            return False, None

        def logic2():
            for i in range(len(strs)):
                if "часть" in strs[i].lower() and strs[-1] != strs[i]:
                    print(" ".join(strs[i::]))
                    return True, " ".join(strs[i::])
            return False, None

        def logic3():
            for i in range(2, len(strs)):
                if strs[i][0] in strs[i][0].upper() and strs[i][1::] in strs[i][1::].lower():
                    return True, strs[i]
            return False, None

        def logic4():
            if len(strs) == 2:
                return True, strs[1]
            else:
                return False, None

        self.db.execute(
            '''SELECT id, description FROM parsed_standards where description is not null''')

        for id_, description in self.db.get():
            strs = split_by_sentences(description)
            res = None
            l1 = logic1()
            l2 = logic2()
            l3 = logic3()
            l4 = logic4()
            if l1[0]:
                res = l1[1]
            elif l2[0]:
                res = l2[1]
            elif l3[0]:
                res = l3[1]
            elif l4[0]:
                res = l4[1]

            self.db.execute('''UPDATE parsed_standards SET standard_groups_by_segment = ? where id = ?''', (res, id_))
        self.db.commit()

    def parse_products_using_leds(self):
        groups = [
            (1,
             ['свет', 'освещ', 'прожектор', 'фонарь', 'осветительный', 'ламп', 'oled', 'электрооборудование аквариумов',
              'облучател', 'рециркулят']),
            (2, [r'блок питан', 'источн питан']),
            (3, ['для уничтожения насекомых']),
            (4, ['лазер']),
            (5, ['зеркало', 'зеркала']),
            (6, ['модули полупроводниковые силовые']),
            (7, ['лифты']),
            (8, ['устройства дисплейные', 'информационным табло', 'медиаэкран',
                 'Средства отображения информации коллективного пользования', 'Табло коммуникационной поддержки']),
            (9, ['Шкафы, прилавки и витрины холодильные торговые', 'витрины', 'прилавки' 'торговое оборудование']),
            (10, ['для удаления кухонных испарений', 'вытяжки кухон']),
            (11, ['холодильники']),
            (12, ['рентген']),
            (13, ['ЗНАКИ ДОРОЖНЫЕ', 'Знаки переменной информации',
                  'Временные технические средства организации дорожного движения']),
            (14, ['Светофоры', 'семафоры']),
            (15, [r'охран видеокамер', 'охран видео-камер', 'охран видео камер']),
            (16, ['реклама']),
            (17, ['вагон', 'трамвай', 'троллейбус', 'автобус', 'поезд', 'Транспортные средства', 'Электротранспорт']),

        ]
        self.db.execute(
            '''SELECT id, header_json, document_html from  raw_search_results where id in (SELECT id from parsed_standards) and document_html is not null''')
        n = 0
        for id_, header, document in self.db.get():
            n += 1
            print(n)
            try:
                header = json.loads(header, strict=False)
            except json.decoder.JSONDecodeError:
                continue
            found = False
            for group, keys in groups:
                if found:
                    break
                if group <= 4:
                    for key in keys:

                        is_match = find_substring_intersect(document.lower(), key.lower())
                        if is_match:
                            self.db.execute(
                                '''UPDATE parsed_standards SET products_using_leds = ? WHERE id = ?''',
                                (group, id_))
                            found = True
                            break

                for name in header["names"]:
                    if found:
                        break
                    for key in keys:

                        is_match = find_substring_intersect(name.lower(), key.lower())
                        if is_match:
                            self.db.execute(
                                '''UPDATE parsed_standards SET products_using_leds = ? WHERE id = ?''',
                                (group, id_))
                            found = True
                            break
        self.db.commit()

    def parse_point_standard_type(self):
        groups = [
            (1, 'ЭМС', ['Совместимость технических средств электромагнитная', 'электромагнитное поле',
                        'электромагнитное излучение', 'электромагнитные помехи', 'радиопомехи', 'кондуктивным']),
            (2, 'безоп.', ['Безопасность', 'Электробезопасность', 'общие требования', 'общие условия']),
            (3, 'УХЛ',
             ['условия эксплуатации', 'требования эксплуатации', 'климатическое исполнение', 'климатическое применение',
              'климатические условия']),
            (4, 'взрыв', ['взрыв', 'рудничное', 'угольные шахты', 'нефте-газов']),
            (5, 'пож', ['пожар']),
            (6, 'EEI', ['энергоэффективный']),
            (7, 'санпин', ['охрана труда', 'безопасность труда', 'условия труда', 'санпин']),

        ]
        uncopy = [
            (1, 'Совместимость технических средств электромагнитная')
        ]

        self.db.execute(
            '''SELECT raw_search_results.id, raw_search_results.document_html,
             parsed_standards.description from raw_search_results,parsed_standards
              where raw_search_results.id = parsed_standards.id''')
        for id_, document, description in self.db.get():
            found_str = set()
            if document is None:
                print(id_, "Has not html document")
                document = ""
            for group, group_name, keys in groups:

                if group == 4:
                    for key in keys:
                        is_match = re.match(r"(^|\s)" + key.lower() + ".*", document.strip().lower(),
                                            flags=re.IGNORECASE) is not None
                        if not is_match:
                            is_match = self.find_substring_normalized(bs(document).get_text().lower(), key.lower())
                        if is_match:
                            found_str.add(group_name)
                            break
                for key in keys:
                    is_match = re.match(r"(^|\s)" + key.lower() + ".*", description.strip().lower(),
                                        flags=re.IGNORECASE) is not None
                    if not is_match:
                        is_match = self.find_substring_normalized(" ".join(split_by_sentences(description.lower())),
                                                                  key.lower())
                    if is_match:
                        found_str.add(group_name)
                        if len([x for x in uncopy if group == x[0] and key in x[1]]) > 0:
                            self.db.execute(
                                '''UPDATE parsed_standards SET point_standard_type_uncopy = ? WHERE id = ?''',
                                (1, id_))
                        break
            if len(found_str) == 0:
                if is_russian_sentence(description):
                    found_str = "безоп."
                else:
                    found_str = None
            else:
                found_str = ", ".join(found_str)
                # print(found_str)
            self.db.execute('''UPDATE parsed_standards SET point_standard_type = ? where id = ?''', (found_str, id_))
        self.db.commit()

    def parse_special_rows(self):
        groups = [
            (19, ['издел', 'товар', 'оборуд', 'продукц']),
            (20,
             ['переходн помех', 'переходн процесс', 'обрывы', 'молнии', 'замыкан', 'звенящ волн',
              'колебательн волн',
              'затухающ волн', 'времен отключ питан', 'помехоустойчивост',
              'устойчивость к выбросу', 'устойчивость к провалам напряжения',
              'кратковременным прерываниям и изменениям напряжения',
              'устойчивость к воздействию микросекундных импульсных помех большой энергии',
              'УСТОЙЧИВОСТЬ К НАНОСЕКУНДНЫМ ИМПУЛЬСНЫМ ПОМЕХАМ', 'выброс напряжения',
              'УСТОЙЧИВОСТЬ К ИСКАЖЕНИЯМ СИНУСОИДАЛЬНОСТИ НАПРЯЖЕНИЯ',
              'устойчивость к импульсному магнитному полю',
              'помехи от линий электропередачи и электрических подстанций',
              'УСТОЙЧИВОСТЬ К ЭЛЕКТРОСТАТИЧЕСКИМ РАЗРЯДАМ', 'функциональная безопасность',
              'УСТОЙЧИВОСТЬ К ИЗМЕНЕНИЯМ ЧАСТОТЫ ПИТАЮЩЕГО НАПРЯЖЕНИЯ',
              'индустриальные радиопомехи двигателя',
              'индустриальных радиопомех электрогенератора',
              'ТЕХНОЛОГИЧЕСКИХ ПРОЦЕССОВ', 'от перенапряжений',
              'до 1000 В переменного тока', 'устойчивость к наведенным помехам',
              'Защита от отклонений напряжения и электромагнитных помех',
              'молнии', 'обрывы', 'КЗ', 'замыкание', 'прерывание напряжения', 'провалы напряжения',
              'импульсному магнит полю',
              'импульсные помехи',
              'КОНДУКТИВНЫМ ПОМЕХАМ В ПОЛОСЕ ЧАСТОТ ОТ 0 ДО 150 кГц. ДЛЯ ТС С ДЛИНОЮ ПОДКЛЮЧАЕМОГО ПРОВОДА БОЛЕЕ 20 МЕТРОВ',
              'Защита от резких отклонений напряжения и электромагнитных возмущений']),
            (22, ['силовые', 'силовое', 'силовых', 'более 16А', 'более 75А', 'менее 75А']),
            (23, ['не более 16А']),
            (24, ['кондуктивным']),
            (25, ['электростатический']),
            (26, ['радиопомехи']),

        ]
        self.db.execute(
            '''SELECT id, description from  parsed_standards clear_name where description is not null ''')
        for id_, description in self.db.get():
            found = False
            for group, keys in groups:
                if found:
                    break
                for key in keys:

                    is_match = find_substring_intersect(description.lower(), key.lower())
                    if is_match:
                        self.db.execute(
                            '''UPDATE parsed_standards SET special_row_{number} = ? WHERE id = ?'''.format(
                                number=group),
                            (1, id_))
                        found = True
                        break
        self.db.commit()

    def parse_description(self):
        self.db.execute(
            '''SELECT id, api_header from raw_search_results where id in (SELECT id from parsed_Standards) and api_header is not null''')
        for id_, header in self.db.get():
            data = json.loads(header)["data"]
            self.db.execute('''UPDATE parsed_standards set description = ? where id = ?''', (data["clean_name"], id_))
            self.db.commit()

    def prefix_correction(self):
        self.db.execute("SELECT DISTINCT prefix FROM parsed_standards")
        prefix = [x[0] for x in self.db.get()]
        russian_prefixes = [x for x in prefix if
                            len([y for y in x[0] if y.lower() in "абвгдеёжзиклмнопрстувхцчшщъыьэюя"]) > 0]
        english_prefixes = [x for x in prefix if x not in russian_prefixes]
        print(russian_prefixes)
        print("123")
        print(english_prefixes)
        self.db.execute("SELECT id, description, prefix from parsed_standards")
        n = 0
        for id_, description, prefix in self.db.get():
            if prefix in english_prefixes:
                for rus_prefix in russian_prefixes:
                    if rus_prefix in description:
                        n += 1
                        self.db.execute('''UPDATE parsed_standards set prefix = ? where id = ?''', (rus_prefix, id_,))
                        self.db.commit()
        print(n, "prefixes updated")

    def parse_is_latin(self):
        self.db.execute('''SELECT id, description FROM parsed_standards''')

        for id_, description in self.db.get():
            is_latin = int(not is_russian_sentence(description))
            print(is_latin)
            self.db.execute('''UPDATE parsed_standards SET is_latin = ? WHERE id = ?''', (is_latin, id_,))
            self.db.commit()

