import glob


class Utils:
    @staticmethod
    def read_queries_and_groups(path, groups_count):
        groups = {}
        for i in range(1, groups_count + 1):
            groups[i] = []
            with open(path + f"queries_{i}.txt", encoding="utf-8") as queries_file:
                groups[i] = [x.strip().lower() for x in queries_file.read().split(",")]
        return groups


