from collections import defaultdict


class QuestionBank:

    def __init__(self):
        pass

    def build(self, dataframe):

        bank = defaultdict(list)

        for _, row in dataframe.iterrows():

            chapter = row["chapter"]

            bank[chapter].append(row)

        return bank