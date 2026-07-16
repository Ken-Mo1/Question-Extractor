class SearchEngine:

    def __init__(self, dataframe):
        self.df = dataframe

    def keyword(self, word):

        return self.df[
            self.df["question"].str.contains(
                word,
                case=False,
                na=False
            )
        ]

    def chapter(self, chapter):
        return self.df[self.df["chapter"] == chapter]

    def marks(self, marks):
        return self.df[self.df["marks"] == marks]

    def year(self, year):
        return self.df[self.df["year"] == year]

    def subject(self, subject):
        return self.df[self.df["subject"] == subject]