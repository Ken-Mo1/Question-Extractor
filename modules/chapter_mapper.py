import re


class ChapterMapper:

    def __init__(self):

        # -------------------------------------------------
        # SCIENCE
        # -------------------------------------------------

        self.science = {

            # Life Processes
            "photosynthesis": "Life Processes",
            "respiration": "Life Processes",
            "nutrition": "Life Processes",
            "digest": "Life Processes",
            "digestion": "Life Processes",
            "stomach": "Life Processes",
            "intestine": "Life Processes",
            "enzyme": "Life Processes",
            "blood": "Life Processes",
            "heart": "Life Processes",
            "artery": "Life Processes",
            "vein": "Life Processes",
            "capillary": "Life Processes",
            "circulation": "Life Processes",
            "haemoglobin": "Life Processes",
            "hemoglobin": "Life Processes",
            "oxygen": "Life Processes",
            "alveoli": "Life Processes",
            "lungs": "Life Processes",
            "kidney": "Life Processes",
            "nephron": "Life Processes",
            "excretion": "Life Processes",
            "xylem": "Life Processes",
            "phloem": "Life Processes",
            "transpiration": "Life Processes",

            # Control and Coordination
            "neuron": "Control and Coordination",
            "brain": "Control and Coordination",
            "spinal cord": "Control and Coordination",
            "reflex": "Control and Coordination",
            "hormone": "Control and Coordination",
            "pituitary": "Control and Coordination",
            "thyroid": "Control and Coordination",
            "adrenal": "Control and Coordination",
            "coordination": "Control and Coordination",
            "stimulus": "Control and Coordination",
            "response": "Control and Coordination",

            # Reproduction
            "reproduction": "How do Organisms Reproduce",
            "zygote": "How do Organisms Reproduce",
            "fertilization": "How do Organisms Reproduce",
            "placenta": "How do Organisms Reproduce",
            "embryo": "How do Organisms Reproduce",
            "menstruation": "How do Organisms Reproduce",
            "pollination": "How do Organisms Reproduce",
            "ovule": "How do Organisms Reproduce",
            "pollen": "How do Organisms Reproduce",
            "seed": "How do Organisms Reproduce",

            # Heredity
            "gene": "Heredity",
            "genetics": "Heredity",
            "inheritance": "Heredity",
            "chromosome": "Heredity",
            "dna": "Heredity",
            "trait": "Heredity",
            "mendel": "Heredity",
            "variation": "Heredity",

            # Electricity
            "electric current": "Electricity",
            "current": "Electricity",
            "resistance": "Electricity",
            "resistor": "Electricity",
            "ohm": "Electricity",
            "voltage": "Electricity",
            "potential difference": "Electricity",
            "ammeter": "Electricity",
            "voltmeter": "Electricity",
            "series circuit": "Electricity",
            "parallel circuit": "Electricity",
            "electric power": "Electricity",
            "joule": "Electricity",

            # Magnetic Effects
            "magnet": "Magnetic Effects of Electric Current",
            "magnetic field": "Magnetic Effects of Electric Current",
            "electromagnet": "Magnetic Effects of Electric Current",
            "motor": "Magnetic Effects of Electric Current",
            "generator": "Magnetic Effects of Electric Current",
            "fleming": "Magnetic Effects of Electric Current",
            "right hand rule": "Magnetic Effects of Electric Current",
            "left hand rule": "Magnetic Effects of Electric Current",
            "solenoid": "Magnetic Effects of Electric Current",
            "compass": "Magnetic Effects of Electric Current",

            # Light
            "mirror": "Light Reflection and Refraction",
            "reflection": "Light Reflection and Refraction",
            "refraction": "Light Reflection and Refraction",
            "concave mirror": "Light Reflection and Refraction",
            "convex mirror": "Light Reflection and Refraction",
            "concave lens": "Light Reflection and Refraction",
            "convex lens": "Light Reflection and Refraction",
            "focal length": "Light Reflection and Refraction",
            "image distance": "Light Reflection and Refraction",
            "ray diagram": "Light Reflection and Refraction",

            # Human Eye
            "eye": "Human Eye",
            "retina": "Human Eye",
            "cornea": "Human Eye",
            "iris": "Human Eye",
            "ciliary": "Human Eye",
            "power of accommodation": "Human Eye",
            "myopia": "Human Eye",
            "hypermetropia": "Human Eye",
            "presbyopia": "Human Eye",
            "cataract": "Human Eye",

            # Carbon
            "carbon": "Carbon and its Compounds",
            "hydrocarbon": "Carbon and its Compounds",
            "ethanol": "Carbon and its Compounds",
            "ethanoic": "Carbon and its Compounds",
            "soap": "Carbon and its Compounds",
            "detergent": "Carbon and its Compounds",
            "ester": "Carbon and its Compounds",
            "homologous": "Carbon and its Compounds",

            # Acids
            "acid": "Acids Bases and Salts",
            "base": "Acids Bases and Salts",
            "salt": "Acids Bases and Salts",
            "ph": "Acids Bases and Salts",
            "indicator": "Acids Bases and Salts",
            "neutralisation": "Acids Bases and Salts",
            "neutralization": "Acids Bases and Salts",
            "litmus": "Acids Bases and Salts",

            # Environment
            "ecosystem": "Our Environment",
            "food chain": "Our Environment",
            "food web": "Our Environment",
            "biodegradable": "Our Environment",
            "non biodegradable": "Our Environment",
            "ozone": "Our Environment",
            "pollution": "Our Environment",

            # Chemical Reactions
            "oxidation": "Chemical Reactions and Equations",
            "reduction": "Chemical Reactions and Equations",
            "combination reaction": "Chemical Reactions and Equations",
            "decomposition": "Chemical Reactions and Equations",
            "displacement": "Chemical Reactions and Equations",
            "balanced equation": "Chemical Reactions and Equations",
        }

        # Remaining subject dictionaries
        self.maths = {}
        self.sst = {}
        self.english = {}
        self.hindi = {}
        self.computer = {}
                # -------------------------------------------------
        # MATHEMATICS
        # -------------------------------------------------

        self.maths = {

            # Real Numbers
            "euclid": "Real Numbers",
            "hcf": "Real Numbers",
            "lcm": "Real Numbers",
            "fundamental theorem of arithmetic": "Real Numbers",
            "prime factorisation": "Real Numbers",
            "prime factorization": "Real Numbers",

            # Polynomials
            "polynomial": "Polynomials",
            "zeroes of polynomial": "Polynomials",
            "zeros of polynomial": "Polynomials",
            "quadratic polynomial": "Polynomials",
            "cubic polynomial": "Polynomials",
            "remainder theorem": "Polynomials",
            "factor theorem": "Polynomials",

            # Pair of Linear Equations
            "linear equation": "Pair of Linear Equations in Two Variables",
            "pair of linear equations": "Pair of Linear Equations in Two Variables",
            "substitution method": "Pair of Linear Equations in Two Variables",
            "elimination method": "Pair of Linear Equations in Two Variables",
            "cross multiplication": "Pair of Linear Equations in Two Variables",

            # Quadratic Equations
            "quadratic equation": "Quadratic Equations",
            "quadratic formula": "Quadratic Equations",
            "discriminant": "Quadratic Equations",
            "nature of roots": "Quadratic Equations",
            "completing the square": "Quadratic Equations",

            # Arithmetic Progressions
            "arithmetic progression": "Arithmetic Progressions",
            "ap": "Arithmetic Progressions",
            "common difference": "Arithmetic Progressions",
            "nth term": "Arithmetic Progressions",
            "sum of first": "Arithmetic Progressions",

            # Triangles
            "pythagoras": "Triangles",
            "similar triangles": "Triangles",
            "basic proportionality theorem": "Triangles",
            "bpt": "Triangles",

            # Coordinate Geometry
            "distance formula": "Coordinate Geometry",
            "section formula": "Coordinate Geometry",
            "coordinates": "Coordinate Geometry",
            "mid point": "Coordinate Geometry",
            "midpoint": "Coordinate Geometry",

            # Trigonometry
            "sin": "Introduction to Trigonometry",
            "cos": "Introduction to Trigonometry",
            "tan": "Introduction to Trigonometry",
            "cosec": "Introduction to Trigonometry",
            "sec": "Introduction to Trigonometry",
            "cot": "Introduction to Trigonometry",
            "trigonometry": "Introduction to Trigonometry",
            "trigonometric identity": "Introduction to Trigonometry",

            # Heights and Distances
            "angle of elevation": "Some Applications of Trigonometry",
            "angle of depression": "Some Applications of Trigonometry",
            "height and distance": "Some Applications of Trigonometry",

            # Circles
            "tangent": "Circles",
            "radius": "Circles",
            "circle": "Circles",

            # Constructions
            "construct": "Constructions",
            "construction": "Constructions",
            "bisector": "Constructions",

            # Areas Related to Circles
            "arc": "Areas Related to Circles",
            "sector": "Areas Related to Circles",
            "segment": "Areas Related to Circles",

            # Surface Areas and Volumes
            "cone": "Surface Areas and Volumes",
            "cylinder": "Surface Areas and Volumes",
            "sphere": "Surface Areas and Volumes",
            "hemisphere": "Surface Areas and Volumes",
            "frustum": "Surface Areas and Volumes",
            "volume": "Surface Areas and Volumes",
            "surface area": "Surface Areas and Volumes",

            # Statistics
            "mean": "Statistics",
            "median": "Statistics",
            "mode": "Statistics",
            "frequency": "Statistics",
            "cumulative frequency": "Statistics",
            "histogram": "Statistics",
            "ogive": "Statistics",

            # Probability
            "probability": "Probability",
            "random experiment": "Probability",
            "sample space": "Probability",
            "event": "Probability",
            "outcome": "Probability"
        }
                # -------------------------------------------------
        # SOCIAL SCIENCE
        # -------------------------------------------------

        self.sst = {

            # HISTORY
            "nationalism": "Nationalism in India",
            "civil disobedience": "Nationalism in India",
            "non cooperation": "Nationalism in India",
            "dandi march": "Nationalism in India",
            "gandhi": "Nationalism in India",
            "gandhiji": "Nationalism in India",
            "salt march": "Nationalism in India",
            "satyagraha": "Nationalism in India",
            "quit india": "Nationalism in India",
            "congress": "Nationalism in India",

            "print culture": "Print Culture and the Modern World",
            "printing press": "Print Culture and the Modern World",
            "martin luther": "Print Culture and the Modern World",
            "gutenberg": "Print Culture and the Modern World",

            "industrial revolution": "The Making of a Global World",
            "globalisation": "The Making of a Global World",
            "globalization": "The Making of a Global World",
            "world economy": "The Making of a Global World",

            "europe": "The Rise of Nationalism in Europe",
            "unification": "The Rise of Nationalism in Europe",
            "italy": "The Rise of Nationalism in Europe",
            "germany": "The Rise of Nationalism in Europe",
            "bismarck": "The Rise of Nationalism in Europe",
            "mazzini": "The Rise of Nationalism in Europe",

            # GEOGRAPHY
            "resource": "Resources and Development",
            "renewable": "Resources and Development",
            "non renewable": "Resources and Development",
            "soil": "Resources and Development",
            "land use": "Resources and Development",

            "forest": "Forest and Wildlife Resources",
            "wildlife": "Forest and Wildlife Resources",
            "biosphere": "Forest and Wildlife Resources",
            "national park": "Forest and Wildlife Resources",

            "water resource": "Water Resources",
            "rainwater harvesting": "Water Resources",
            "dam": "Water Resources",
            "multipurpose project": "Water Resources",

            "agriculture": "Agriculture",
            "cropping": "Agriculture",
            "kharif": "Agriculture",
            "rabi": "Agriculture",
            "cash crop": "Agriculture",

            "mineral": "Minerals and Energy Resources",
            "coal": "Minerals and Energy Resources",
            "petroleum": "Minerals and Energy Resources",
            "natural gas": "Minerals and Energy Resources",
            "mica": "Minerals and Energy Resources",

            "manufacturing": "Manufacturing Industries",
            "industry": "Manufacturing Industries",
            "iron and steel": "Manufacturing Industries",
            "cotton textile": "Manufacturing Industries",

            "lifeline": "Lifelines of National Economy",
            "transport": "Lifelines of National Economy",
            "roadways": "Lifelines of National Economy",
            "railways": "Lifelines of National Economy",
            "waterways": "Lifelines of National Economy",

            # POLITICAL SCIENCE
            "power sharing": "Power Sharing",
            "belgium": "Power Sharing",
            "sri lanka": "Power Sharing",

            "federalism": "Federalism",
            "state list": "Federalism",
            "union list": "Federalism",
            "concurrent list": "Federalism",

            "democracy": "Gender Religion and Caste",
            "gender": "Gender Religion and Caste",
            "caste": "Gender Religion and Caste",
            "communalism": "Gender Religion and Caste",

            "political party": "Political Parties",
            "bjp": "Political Parties",
            "congress party": "Political Parties",
            "regional party": "Political Parties",

            "election": "Outcomes of Democracy",
            "democratic": "Outcomes of Democracy",

            "consumer rights": "Consumer Rights",
            "consumer protection": "Consumer Rights",
            "copra": "Consumer Rights",

            # ECONOMICS
            "development": "Development",
            "per capita income": "Development",
            "human development": "Development",
            "hdi": "Development",

            "sector": "Sectors of Indian Economy",
            "primary sector": "Sectors of Indian Economy",
            "secondary sector": "Sectors of Indian Economy",
            "tertiary sector": "Sectors of Indian Economy",

            "money": "Money and Credit",
            "credit": "Money and Credit",
            "bank": "Money and Credit",
            "loan": "Money and Credit",
            "self help group": "Money and Credit",

            "globalisation": "Globalisation and the Indian Economy",
            "multinational": "Globalisation and the Indian Economy",
            "mnc": "Globalisation and the Indian Economy",
            "liberalisation": "Globalisation and the Indian Economy",

            "consumer movement": "Consumer Rights"
        }
                # -------------------------------------------------
        # ENGLISH
        # -------------------------------------------------

        self.english = {

            "letter to god": "A Letter to God",
            "nelson mandela": "Nelson Mandela",
            "two stories": "Two Stories about Flying",
            "anne frank": "From the Diary of Anne Frank",
            "hundred dresses": "The Hundred Dresses",
            "glimpses of india": "Glimpses of India",
            "mijbil": "Mijbil the Otter",
            "madam rides the bus": "Madam Rides the Bus",
            "sermon at benares": "The Sermon at Benares",
            "proposal": "The Proposal",

            "dust of snow": "Dust of Snow",
            "fire and ice": "Fire and Ice",
            "tiger in the zoo": "A Tiger in the Zoo",
            "how to tell wild animals": "How to Tell Wild Animals",
            "ball poem": "The Ball Poem",
            "amanda": "Amanda",
            "animals": "Animals",
            "trees": "The Trees",
            "fog": "Fog",
            "tale of custard": "The Tale of Custard the Dragon",

            "triumph of surgery": "A Triumph of Surgery",
            "thief story": "The Thief's Story",
            "midnight visitor": "The Midnight Visitor",
            "question of trust": "A Question of Trust",
            "footprints": "Footprints Without Feet",
            "making of scientist": "The Making of a Scientist",
            "necklace": "The Necklace",
            "bholi": "Bholi",
            "book saved": "The Book That Saved the Earth"
        }

        # -------------------------------------------------
        # HINDI
        # -------------------------------------------------

        self.hindi = {

            "बड़े भाई साहब": "बड़े भाई साहब",
            "डायरी": "डायरी का एक पन्ना",
            "तताँरा": "तताँरा-वामीरो कथा",
            "सपनों": "सपनों के-से दिन",
            "टोपी": "टोपी शुक्ला",
            "साखी": "साखी",
            "मीरा": "मीरा के पद",
            "मनुष्यता": "मनुष्यता",
            "आत्मकथ्य": "आत्मकथ्य",
            "राम": "राम-लक्ष्मण-परशुराम संवाद"
        }

        # -------------------------------------------------
        # COMPUTER / AI
        # -------------------------------------------------

        self.computer = {

            "python": "Python Programming",
            "list": "Python Programming",
            "tuple": "Python Programming",
            "dictionary": "Python Programming",
            "function": "Python Programming",

            "artificial intelligence": "Artificial Intelligence",
            "machine learning": "Artificial Intelligence",
            "ai": "Artificial Intelligence",
            "neural network": "Artificial Intelligence",

            "database": "Database",
            "sql": "Database",
            "sqlite": "Database",

            "cyber": "Cyber Safety",
            "phishing": "Cyber Safety",
            "malware": "Cyber Safety",
            "virus": "Cyber Safety",
            "password": "Cyber Safety"
        }

    # -------------------------------------------------
    # Prediction
    # -------------------------------------------------

        # -------------------------------------------------
    # Prediction
    # -------------------------------------------------

    def predict(self, question, subject):

        q = question.lower()

        subject = str(subject).lower()

        if "science" in subject:
            mapping = self.science

        elif "math" in subject:
            mapping = self.maths

        elif "social" in subject:
            mapping = self.sst

        elif "english" in subject:
            mapping = self.english

        elif "hindi" in subject:
            mapping = self.hindi

        elif (
            "computer" in subject
            or "artificial intelligence" in subject
            or subject == "ai"
            or "information technology" in subject
        ):
            mapping = self.computer

        else:
            return "Unknown"

        for keyword in sorted(mapping.keys(), key=len, reverse=True):

            if keyword in q:
                return mapping[keyword]

        return "Unknown"
