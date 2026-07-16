class Analytics:

    def __init__(self, df):
        self.df = df

    def summary(self):

        return {

            "Questions": len(self.df),

            "Subjects": self.df["subject"].fillna("").nunique(),

            "Chapters": self.df["chapter"].fillna("").nunique(),

            "Types": self.df["type"].fillna("").nunique()

        }